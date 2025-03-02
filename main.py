import sys
import requests
from bs4 import BeautifulSoup
import json
import re
import os
from dotenv import load_dotenv
import concurrent.futures
import threading
from concurrent.futures import ThreadPoolExecutor

print_lock = threading.Lock()
bulk_data_lock = threading.Lock()
# Bellekte ID sayacı
global_id_counter = 30001
id_lock = threading.Lock()  # ID güncelleme için kilit

# Yazma işlemi sırasında kilit kullanmak için
write_lock = threading.Lock()

load_dotenv()
def fetch_links_from_page(base_url, page_number, headers, productLinks, lock):
    """Belirli bir sayfadan linkleri getirir ve paylaşılan productLinks setine ekler."""
    url = f'{base_url}&sf={page_number}'
    link_url = os.getenv("LINK_URL")
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()  # HTTP hatalarını yakala
        soup = BeautifulSoup(r.content, 'html.parser')
        productList = soup.find_all('div', class_='col-md-3 col-6 pro-shadow')
        with lock:
            for item in productList:
                link = item.find('a', href=True)
                if link:
                    href = link['href']
                    if href.startswith('/'):
                        href = href[1:]  # Başındaki '/' karakterini kaldır
                    full_link = link_url.rstrip('/') + '/' + href.lstrip('/')
                    productLinks.add(full_link)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page {page_number}: {e}")


def getProductLinks(base_url, output_file):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
    }
    productLinks = set()  # Set kullanarak aynı linklerin tekrar eklenmesini önlüyoruz
    lock = threading.Lock()  # productLinks setini korumak için kilit

    # Multithreading ile sayfaları paralel olarak işle
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_links_from_page, base_url, x, headers, productLinks, lock) for x in
                   range(1, 2)]

        # Tüm işlerin tamamlanmasını bekleyin
        for future in futures:
            future.result()

    # Linkleri JSON formatında bir dosyaya yazın
    with open(output_file, 'w') as file:
        json.dump(list(productLinks), file, indent=4)

    print(f'Number of product links: {len(productLinks)}')


# Benzersiz ID oluşturmak için sayaç dosyasını kullan
# Bellekte ID oluşturma işlevi
def get_next_id():
    global global_id_counter
    with id_lock:
        next_id = global_id_counter
        global_id_counter += 1
    return next_id

# Program sonlandığında ID'yi dosyaya kaydetme işlevi
def save_id_to_file(counter_file='ProductsData/id_counter.txt'):
    with open(counter_file, 'w') as file:
        file.write(str(global_id_counter))


def scrapeDetailsFromLink(link):
    tire_data = {}

    try:
        with print_lock:
            print(f"Processing link: {link}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
        }

        r = requests.get(link, headers=headers, timeout=35)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html.parser')

        productName_element = soup.find('h1', class_='prod-title')
        if productName_element:
            productName = productName_element.text.strip()
        else:
            raise ValueError(f"Product name not found for link: {link}")

        # Üst sınıftan başlayarak marka adını çekme
        productBrand_element = soup.find('div', class_='row my-3 my-md-0 mx-0')
        if productBrand_element:
            brand_anchor = productBrand_element.find('a')
            if brand_anchor:
                productBrand = brand_anchor.text.strip()
            else:
                productBrand = "Marka bulunamadı"
        else:
            productBrand = "Marka bulunamadı"



        productPrice = None
        divs = soup.find_all('div')
        for div in divs:
            if 'font-weight: bolder;' in div.get('style', '') and 'font-size: 1.7rem;' in div.get('style', ''):
                productPrice = div.text.strip()
                break

        if productPrice:
            productPrice = re.sub(r'[^\d,]', '', productPrice).replace(',', '.')

        tire_data = {
            'name': productName,
            'brand': productBrand,
            'price': productPrice,
            'stock status': 'outofstock',
            'tecs': {}
        }

        images = soup.select('div.carousel-item.active img')
        tire_data['images'] = [{'src': img.get('data-src')} for img in images if img.get('data-src')]

        rows = soup.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) > 1:
                attribute_name = cells[0].text.strip()
                attribute_value = cells[1].text.strip()
                tire_data['tecs'][attribute_name] = attribute_value

        tire_data['description'] = tire_data['name'] + ' ' + tire_data['tecs'].get('Mevsim', '') + ' lastiği'

        # Kategori ve Mevsim bilgilerini işleme
        categories = [{'id': 104, 'name': 'Lastik'}]  # İlk kategori 104 ve 'Lastik' adıyla eklenir
        if tire_data['tecs'].get('Kategori') == 'Oto Lastik':
            categories.append({'id': 105, 'name': 'Otomobil Lastikleri'})
        elif tire_data['tecs'].get('Kategori') == 'SUV 4x4 Lastikleri':
            categories.append({'id': 106, 'name': 'Suv Lastikleri'})
        elif tire_data['tecs'].get('Kategori') == 'Elektrikli Otomobil Lastikleri':
            categories.append({'id': 107, 'name': 'Elektrikli Araç Lastikleri'})
        elif tire_data['tecs'].get('Kategori') == 'Hafif Ticari Lastikleri':
            categories.append({'id': 108, 'name': 'Hafif Ticari Araç Lastikleri'})

        if 'Mevsim' in tire_data['tecs']:
            season = None
            if tire_data['tecs']['Mevsim'] == 'Yaz':
                season = {'id': 113, 'name': 'Yaz Lastiği'}
            elif tire_data['tecs']['Mevsim'] == 'Kış':
                season = {'id': 114, 'name': 'Kış Lastiği'}
            elif tire_data['tecs']['Mevsim'] == '4-Mevsim':
                season = {'id': 115, 'name': '4 Mevsim Lastiği'}

            if season:
                categories.append(season)

        # Dot Text ve üretim tarihi kontrolü
        dot_text_element = soup.find('span', id='spProductionDate')
        if dot_text_element:
            dotText = dot_text_element.text.strip()
            dot = dotText.replace('Üretim Tarihi : ', '').strip()
        else:
            dot = '2024'

        brand_attribute = create_brandAndDot_Attribute('Marka', productBrand)
        dot_attribute = create_brandAndDot_Attribute('Üretim Yılı', dot)

        # Resimleri formatlama
        images_formatted = [{'src': img.get('data-src')} for img in images if img.get('data-src')]

        # Ürün attributeleri product_data'ya dahil edilecek
        attributes = []
        for name, option in tire_data['tecs'].items():
            attribute = {
                'name': name,
                'options': [option]
            }
            attribute = create_attribute(name, option)
            attributes.append(attribute)

        attributes.append(brand_attribute)
        attributes.append(dot_attribute)

        # Benzersiz bir id oluştur
        product_id = get_next_id()

        product_data = {
            "id": product_id,
            "name": tire_data['name'] + ' ' + tire_data['tecs'].get('Mevsim', '') + ' Lastiği ' + dot + ' Üretim',
            "categories": categories,
            "images": images_formatted,
            "attributes": attributes,  # Attributeleri burada ekledik
        }

        return product_data

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"404 Not Found error for link: {link}")
        else:
            print(f"HTTP error occurred for link: {link}\nError: {str(e)}")
        with open("ProductsData/failed_links.txt", "a") as file:
            file.write(link + "\n")
        return None


    except requests.exceptions.RequestException as e:
        print(f"An error occurred while processing the link: {link}\nError: {str(e)}")
        # Hatalı linki bir dosyaya kaydedin
        with open("ProductsData/failed_links.txt", "a") as file:
            file.write(link + "\n")
        return None


def save_data_to_json(bulk_data, file_path=os.getenv("SAVE_FILE")):
    # Dosya mevcut değilse, klasörü ve dosyayı oluştur
    if not os.path.exists(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))

    # Mevcut veriyi oku veya boş liste başlat
    try:
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            with open(file_path, 'r', encoding='utf-8') as file:
                existing_data = json.load(file)
        else:
            existing_data = []
    except json.JSONDecodeError:
        print("Error: JSON file is corrupted. Program will terminate without modifying the file.")
        sys.exit(1)

    # Yeni veriyi ekle
    existing_data.extend(bulk_data)

    # JSON dosyasına yaz
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(existing_data, file, ensure_ascii=False, indent=4)

    print(f"Number of products in file: {len(existing_data)}")


def create_attribute(name, option):
    # name alanlarına göre id ekleyelim
    if name == "Kategori":
        return {'id': 1, 'name': name, 'options': [option]}
    elif name == "Mevsim":
        return {'id': 8, 'name': name, 'options': [option]}
    elif name == "Yakıt Ekonomisi":
        return {'id': 27, 'name': name, 'options': [option]}
    elif name == "Fren Mesafesi":
        return {'id': 28, 'name': name, 'options': [option]}
    elif name == "Gürültü Seviyesi":
        return {'id': 29, 'name': name, 'options': [option]}
    elif name == "Taban Genişliği":
        return {'id': 9, 'name': name, 'options': [option]}
    elif name == "Yanak Kesiti":
        return {'id': 10, 'name': name, 'options': [option]}
    elif name == "Jant Çapı":
        return {'id': 11, 'name': name, 'options': [option]}
    elif name == "Yük Endeksi":
        return {'id': 12, 'name': name, 'options': [option]}
    elif name == "Hız Endeksi":
        return {'id': 13, 'name': name, 'options': [option]}
    elif name == "Ürün Tipi":
        return {'id': 15, 'name': name, 'options': [option]}
    elif name == "Ebat":
        return {'id': 16, 'name': name, 'options': [option]}
    elif name == "Desen":
        return {'id': 17, 'name': name, 'options': [option]}
    elif name == "Yük/Hız Endeksi":
        return {'id': 18, 'name': name, 'options': [option]}
    elif name == "Yük/HızEndeksi":
        return {'id': 18, 'name': "Yük/Hız Endeksi", 'options': [option]}
    elif name == "M + S":
        return {'id': 21, 'name': name, 'options': [option]}
    elif name == "OEM Araç":
        return {'id': 25, 'name': name, 'options': [option]}
    elif name == "XL Ekstra Yük":
        return {'id': 14, 'name': name, 'options': [option]}
    elif name == "3PMSF":
        return {'id': 22, 'name': name, 'options': [option]}
    elif name == "Kat Sayısı":
        return {'id': 34, 'name': name, 'options': [option]}
    elif name == "OEM Kod":
        return {'id': 35, 'name': name, 'options': [option]}
    elif name == "Ses Yalıtımı":
        return {'id': 36, 'name': name, 'options': [option]}
    elif name == "Run Flat / Patlasada Gidebilen":
        return {'id': 37, 'name': "Run Flat / Patlasa da Gidebilen", 'options': [option]}
    elif name == "Patlak Yalıtımı":
        return {'id': 38, 'name': name, 'options': [option]}
    elif name == "Pozisyon":
        return {'id': 39, 'name': name, 'options': [option]}
    elif name == "Tube-Type":
        return {'id': 40, 'name': "İç Lastik (Şambrel) Tipi", 'options': [option]}
    elif name == "Jant Tipi":
        return {'id': 41, 'name': name, 'options': [option]}
    elif name == "Jant Koruma":
        return {'id': 42, 'name': name, 'options': [option]}
def create_brandAndDot_Attribute(name, option):
    if name == "Marka":
        return {
            'id': 6,
            'name': name,
            'options': [option]
        }
    elif name == "Üretim Yılı":
        return {
            'id': 5,
            'name': name,
            'options': [option]
        }



def main():
    # base_url = os.getenv("BASE_URL")
    # output_file = os.getenv("OUTPUT_FILE")
    # getProductLinks(base_url, output_file)

    global global_id_counter
    # ID dosyasını sadece başlangıçta bir kez oku
    counter_file = 'ProductsData/id_counter.txt'
    if os.path.exists(counter_file):
        with open(counter_file, 'r') as file:
            try:
                global_id_counter = int(file.read().strip())
            except ValueError:
                print("Warning: ID counter file is corrupted. Starting from 30001.")
                global_id_counter = 30001

    output_file = os.getenv("OUTPUT_FILE")  # .env'den dosya ismini al
    if not os.path.exists(output_file):
        raise FileNotFoundError(f"HATA: {output_file} dosyası bulunamadı!")

    with open(output_file, 'r') as file:
        product_links = json.load(file)

    # product_links'i 50'lik gruplara ayır
    batch_size = 50
    for i in range(0, len(product_links), batch_size):
        links_batch = product_links[i:i + batch_size]
        bulk_data = []

        # Her 50'lik bağlantı grubu için iş parçacıklarıyla işlemi başlat
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(scrapeDetailsFromLink, links_batch))

        # İşlem sonuçlarını bulk_data'ya ekle
        for result in results:
            if result:
                bulk_data.append(result)

        # Her batch tamamlandığında dosyaya kaydet
        if bulk_data:
            save_data_to_json(bulk_data)
            bulk_data = []  # Sıfırla

    # Program tamamlandığında ID'yi dosyaya kaydet
    save_id_to_file(counter_file)

    print("LINK_URL:", os.getenv("LINK_URL"))
    print("BASE_URL:", os.getenv("BASE_URL"))
    print("OUTPUT_FILE:", os.getenv("OUTPUT_FILE"))
    print("SAVE_FILE:", os.getenv("SAVE_FILE"))


if __name__ == "__main__":
    main()
