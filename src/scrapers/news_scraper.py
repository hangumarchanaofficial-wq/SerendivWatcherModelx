import time
import yaml
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .base_scraper import BaseScraper

class NewsScraper(BaseScraper):
    def __init__(self, db_manager, config_path="config/scraper_config.yaml"):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        super().__init__(db_manager, config)
    
    def scrape_daily_mirror_business(self, browser):
        """Scrape Daily Mirror business section"""
        page = browser.new_page()
        url = self.config['sources']['daily_mirror']['business_url']
        
        self.safe_goto(page, url, timeout=self.config['scraping']['timeout'])
        time.sleep(self.config['scraping']['wait_time'])
        
        soup = BeautifulSoup(page.content(), "html.parser")
        page.close()
        
        selectors = self.config['sources']['daily_mirror']['selectors']['business']
        links = self.extract_links(soup, selectors, url)
        
        # Filter out the listing page itself
        links = [l for l in links if l.rstrip("/") != url.rstrip("/")]
        
        for link in links:
            self._scrape_article(browser, link, "DailyMirror", "business")
    
    def scrape_the_morning(self, browser):
        """Scrape The Morning news"""
        page = browser.new_page()
        url = self.config['sources']['the_morning']['news_url']
        
        self.safe_goto(page, url, timeout=self.config['scraping']['timeout'])
        time.sleep(self.config['scraping']['wait_time'])
        
        soup = BeautifulSoup(page.content(), "html.parser")
        page.close()
        
        selector = self.config['sources']['the_morning']['selectors']['articles']
        links = self.extract_links(soup, selector, url)
        
        for link in links:
            self._scrape_article(browser, link, "TheMorning", "news")
    
    def scrape_ft_lk(self, browser):
        """Scrape FT.lk"""
        page = browser.new_page()
        url = self.config['sources']['ft_lk']['base_url'] + "/"
        
        self.safe_goto(page, url, timeout=self.config['scraping']['timeout'])
        time.sleep(self.config['scraping']['wait_time'])
        
        soup = BeautifulSoup(page.content(), "html.parser")
        page.close()
        
        selectors = self.config['sources']['ft_lk']['selectors']['articles']
        links = self.extract_links(soup, selectors, url)
        
        # Filter specific patterns
        business_list = self.config['sources']['ft_lk']['business_list']
        filtered_links = []
        for link in links:
            if link.rstrip("/") == business_list.rstrip("/"):
                continue
            if "/business/" in link and "34-" not in link:
                continue
            if "/front-page/" in link and "44-" not in link:
                continue
            filtered_links.append(link)
        
        for link in filtered_links:
            self._scrape_article(browser, link, "FT.lk", "business/front-page")
    
    def scrape_economic_times(self, browser):
        """Scrape Economic Times"""
        urls = [
            self.config['sources']['economic_times']['base_url'],
            self.config['sources']['economic_times']['economy_url']
        ]
        
        for url in urls:
            page = browser.new_page()
            self.safe_goto(page, url, timeout=self.config['scraping']['timeout'])
            time.sleep(self.config['scraping']['wait_time'])
            
            soup = BeautifulSoup(page.content(), "html.parser")
            page.close()
            
            selector = self.config['sources']['economic_times']['selectors']['articles']
            links = self.extract_links(soup, selector, url)
            
            for link in links:
                self._scrape_article(browser, link, "EconomicTimes.lk", "economy")
    
    def scrape_sunday_times(self, browser):
        """Scrape Sunday Times Business"""
        page = browser.new_page()
        url = self.config['sources']['sunday_times']['business_url']
        
        print(f"\n[DEBUG] Loading Sunday Times: {url}")
        self.safe_goto(page, url, timeout=self.config['scraping']['timeout'])
        time.sleep(self.config['scraping']['wait_time'])
        
        soup = BeautifulSoup(page.content(), "html.parser")
        page.close()
        
        selector = self.config['sources']['sunday_times']['selectors']['articles']
        print(f"[DEBUG] Using selector: {selector}")
        
        links = self.extract_links(soup, selector, url)
        
        print(f"[DEBUG] Found {len(links)} Sunday Times articles")
        if len(links) == 0:
            print("[DEBUG] No links found! Trying alternative selectors...")
            # Try alternative selectors
            alt_links = []
            for a in soup.find_all('a', href=True):
                href = a.get('href')
                if href and '/business-times/' in href and '/251130/' in href:
                    alt_links.append(href)
            print(f"[DEBUG] Alternative search found {len(alt_links)} links")
            links = list(set(alt_links))[:10]  # Take first 10 unique
        
        for link in links:
            print(f"[DEBUG] Scraping: {link}")
            self._scrape_article(browser, link, "SundayTimes", "business-times")
    
    def scrape_lmd(self, browser):
        """Scrape LMD"""
        page = browser.new_page()
        url = self.config['sources']['lmd']['base_url']
        
        self.safe_goto(page, url, timeout=self.config['scraping']['timeout'])
        time.sleep(self.config['scraping']['wait_time'])
        
        soup = BeautifulSoup(page.content(), "html.parser")
        page.close()
        
        selector = self.config['sources']['lmd']['selectors']['articles']
        links = self.extract_links(soup, selector, url)
        
        for link in links:
            self._scrape_article(browser, link, "LMD", "home")
    
    def _scrape_article(self, browser, url, source, section):
        """Scrape individual article"""
        page = browser.new_page()
        self.safe_goto(page, url, timeout=60000)
        
        soup = BeautifulSoup(page.content(), "html.parser")
        page.close()
        
        title, full_text = self.extract_article_content(soup)
        full_text = self.limit_words(full_text, self.config['scraping']['max_words'])
        
        # Debug for Sunday Times
        if "sundaytimes" in url:
            print(f"[DEBUG ST] Title: '{title[:50] if title else 'EMPTY'}'")
            print(f"[DEBUG ST] Text length: {len(full_text)} chars")
            if not title:
                print("[DEBUG ST] No title found! Trying alternative extraction...")
                # Try alternative title extraction for Sunday Times
                title_tag = soup.find("h1") or soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else "Untitled"
                print(f"[DEBUG ST] Alternative title: '{title[:50]}'")
        
        if self.db.save_article(source, section, title, url, full_text):
            print(f"[{source}] {title[:50]}...")
        else:
            print(f"[{source}] FAILED to save: {url}")

    def run_all(self):
        """Run all scrapers"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.config['scraping']['headless'])
            
            try:
                print("Starting scraping process...")
                self.scrape_sunday_times(browser)
                self.scrape_daily_mirror_business(browser)
                self.scrape_the_morning(browser)
                self.scrape_ft_lk(browser)
                self.scrape_economic_times(browser)
                self.scrape_lmd(browser)
                print("Scraping completed!")
            except Exception as e:
                print(f"Error during scraping: {e}")
            finally:
                browser.close()
