# 🚀 Concurrent Data Scraper Bot

**Concurrent_Data_Scraper_Bot** is a **multi-threaded web scraper** designed for high-speed data extraction.  
It uses **BeautifulSoup**, `requests`, and `ThreadPoolExecutor` for efficient concurrent scraping, saving data in **JSON format**.

## 📌 Features
- ✅ **Multi-threaded scraping** for high-speed data collection  
- ✅ **Extracts product data** (brand, price, specs, images)  
- ✅ **Saves output in JSON format**  
- ✅ **Handles failed requests & retries automatically**  
- ✅ **Uses `.env` file** to manage environment variables  

## 🛠️ Installation & Setup

### 🔹 1. Clone the Repository
```sh
git clone https://github.com/keremTheDev/Concurrent_Data_Scraper_Bot.git
cd Concurrent_Data_Scraper_Bot
```
### 🔹 2. Install Required Dependencies

```sh
pip install -r requirements.txt
```
### 🔹 3. Create & Configure .env File
```sh
LINK_URL=
BASE_URL=
OUTPUT_FILE=
SAVE_FILE=
```
### 🔹 4. Run the Scraper
```sh
python main.py
```

## 🛠️ How It Works

- 1️⃣ The scraper first collects all product links from multiple pages.
- 2️⃣ Each product page is processed concurrently using ThreadPoolExecutor.
- 3️⃣ Extracted data includes:

- Name, Brand, Price, Stock Status
- Technical specifications (attributes)
- Images and Production Year
- 4️⃣ All scraped data is saved in JSON format (ProductsData/LBAllData3.json).

## ⚙️ Technologies Used

- Python 3.8+
- BeautifulSoup (for HTML parsing)
- requests (for HTTP requests)
- ThreadPoolExecutor (for concurrent scraping)
- dotenv (for managing environment variables)
- JSON serialization (for structured data storage)