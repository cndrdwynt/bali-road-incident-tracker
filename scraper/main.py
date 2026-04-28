import time
import random
import json
import os
import pymongo
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 1. CONFIGURATION & DATABASE ---
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongodb_bali:27017")
REMOTE_URL = os.getenv("SELENIUM_REMOTE_URL", "http://selenium-vnc:4444/wd/hub")

# Sambungan ke Database
client = pymongo.MongoClient(MONGO_URL)
db = client["bali_traffic"]
collection = db["raw_posts"]

def init_driver():
    options = Options()
    
    # Headless dimatikan agar bisa ditonton Live Streaming di VNC
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument("window-size=1280,800")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    # Hubungkan ke kontainer selenium-vnc
    driver = webdriver.Remote(
        command_executor=REMOTE_URL,
        options=options
    )
    return driver

def scrape_denpasar_viral():
    driver = init_driver()
    total_added = 0
    seen_texts = set()
    
    keywords = [
        "kecelakaan", "laka", "tabrakan", "beruntun", 
        "macet", "kemacetan", "padat merayap", "tersendat",
        "kebakaran", "api", "damkar", "hangus"
    ]
    
    print(f"🚀 [VNC MODE] Menghubungkan ke Browser... Silakan buka http://localhost:7900")
    
    try:
        # Step 1: Login via Cookies
        driver.get("https://www.facebook.com")
        time.sleep(5)
        
        if os.path.exists("cookies.json"):
            with open("cookies.json", "r") as f:
                cookies = json.load(f)
                for cookie in cookies:
                    if 'sameSite' in cookie: del cookie['sameSite']
                    driver.add_cookie(cookie)
        
        # Step 2: Menuju Sasaran
        driver.get("https://www.facebook.com/denpasarviral/posts")
        print("🔍 Menunggu halaman termuat...")
        
        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='main']")))

        # Step 3: Infinite Scroll (Tonton aksinya di port 7900!)
        for scroll_count in range(500):
            # Scroll halus seperti manusia
            scroll_distance = random.randint(800, 1300)
            driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
            
            time.sleep(random.uniform(4, 6))
            
            # Scrape data
            posts = driver.find_elements(By.XPATH, "//div[@dir='auto']")
            
            for post in posts:
                try:
                    raw_text = post.text
                    if raw_text and len(raw_text) > 40:
                        text_lower = raw_text.lower()
                        
                        if any(k in text_lower for k in keywords):
                            clean_text = " ".join(raw_text.split())
                            
                            if clean_text not in seen_texts:
                                seen_texts.add(clean_text)
                                
                                # Simpan ke Mongo (Anti-Duplikat)
                                res = collection.update_one(
                                    {"text": clean_text},
                                    {"$setOnInsert": {
                                        "text": clean_text,
                                        "status": "pending_ai",
                                        "scraped_at": time.ctime(),
                                        "source": "Denpasar Viral"
                                    }},
                                    upsert=True
                                )
                                
                                if res.upserted_id:
                                    total_added += 1
                                    print(f"📥 [{total_added}] Data Baru Masuk: {clean_text[:60]}...")
                except: continue
            
            if scroll_count % 5 == 0:
                print(f"🔄 Live Scroll: {scroll_count}/500 | Total Data Terkumpul: {total_added}")

    except Exception as e:
        print(f"❌ Error Sistem: {e}")
    finally:
        print("🏁 Scraper Selesai.")
        driver.quit()

if __name__ == "__main__":
    scrape_denpasar_viral()