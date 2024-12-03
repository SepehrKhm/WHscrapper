import os
import time
import requests as req
from bs4 import BeautifulSoup
import pandas as pd

file = "urls_wikihoghoogh(1).csv"

def contains_exclusion_text(url):
    response = req.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    exclusion_table = soup.find('table', class_='box-منسوخ plainlinks metadata ambox ambox-notice')
    
    if exclusion_table:
        return True
    return False

def extract_urls(url, url_type):
    time.sleep(10)  # Pause for 10 seconds between requests
    response = req.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    if url_type == "subcategory":
        category_groups = soup.find_all('div', class_='mw-category-group')
        hrefs = []

        for group in category_groups:
            links = group.find_all('a')
            for link in links:
                hrefs.append(link.get('href'))

        base_url = 'https://wikihoghoogh.net'
        full_urls = [base_url + href for href in hrefs]
        return full_urls

    elif url_type == "page":
        urls = []
        is_next_page = False

        mw_pages_div = soup.find('div', id='mw-pages')
        if not mw_pages_div:
            return urls

        a_tags = mw_pages_div.find_all('a')

        for a in a_tags:
            if a.get_text(strip=True) == "صفحهٔ بعدی":
                next_page = 'https://wikihoghoogh.net' + str(a.get('href'))
                is_next_page = True
                break

        for a in a_tags:
            if a.get_text(strip=True) != "صفحهٔ بعدی" and a.get_text(strip=True) != "صفحهٔ قبلی":
                urls.append('https://wikihoghoogh.net' + str(a.get('href')))

        while is_next_page:
            time.sleep(10)  # Pause for 10 seconds between requests
            response = req.get(next_page)
            soup = BeautifulSoup(response.content, 'html.parser')

            mw_pages_div = soup.find('div', id='mw-pages')
            if not mw_pages_div:
                break

            a_tags = mw_pages_div.find_all('a')

            for a in a_tags:
                if a.get_text(strip=True) != "صفحهٔ بعدی" and a.get_text(strip=True) != "صفحهٔ قبلی":
                    urls.append('https://wikihoghoogh.net' + str(a.get('href')))

            for a in a_tags:
                if a.get_text(strip=True) == "صفحهٔ بعدی":
                    next_page = 'https://wikihoghoogh.net' + str(a.get('href'))
                    is_next_page = True
                    break
                else:
                    is_next_page = False

        return urls

def get_last_scraped_url():
    if os.path.exists(file):
        df = pd.read_csv(file)
        if not df.empty:
            return df.iloc[-1, 0] 
    return None

def write_law(url, url_type):
    law_urls = []

    last_scraped_url = get_last_scraped_url()
    print(f"Last scraped URL: {last_scraped_url}")

    subcategory_urls = extract_urls(url, url_type)
    start_scraping = not last_scraped_url  

    for subcategory_url in subcategory_urls:
        page_urls = extract_urls(subcategory_url, "page")
        for page_url in page_urls:
            if not start_scraping:
                if page_url == last_scraped_url:
                    start_scraping = True  
                continue

            if not contains_exclusion_text(page_url):
                time.sleep(10)  # Pause for 10 seconds before processing each page
                law_urls.append(page_url)

    if law_urls:
        if os.path.exists(file):
            existing_df = pd.read_csv(file)
            new_df = pd.DataFrame(law_urls, columns=["Page URLs"])
            combined_df = pd.concat([existing_df, new_df], ignore_index=True).drop_duplicates()
            combined_df.to_csv(file, index=False, encoding='utf-8')
        else:
            pd.DataFrame(law_urls, columns=["Page URLs"]).to_csv(file, index=False, encoding='utf-8')
        print(f"Saved {len(law_urls)} new URLs to {file}.")
    else:
        print("No new URLs found.")

write_law("", "subcategory")
