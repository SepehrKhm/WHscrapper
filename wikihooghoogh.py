import os
import asyncio
import aiohttp  # type: ignore
import pandas as pd
from bs4 import BeautifulSoup
import re

input_file = 'urls_wikihoghoogh(1).csv'
output_file = 'laws_wikihoghoogh(1).csv'

async def get_last_scraped_url():
    if os.path.exists(output_file):
        df = pd.read_csv(output_file)
        if not df.empty:
            return df.iloc[-1, 3]
    return None

async def fetch(url, session):
    async with session.get(url) as response:
        return await response.text()

def clean_text(text):
    unwanted_sections = [
        "از ویکی حقوق", "پرش به ناوبری", "پرش به جستجو",
        "مشاهده اصل قبلی", "مشاهده اصل بعدی", "فهرست",
        "اصول قانون اساسیشوراهامواد قرمز",
        "۲ پیشینه تفسیری دکترین رویه‌های حکومتی",
        "۲ توضیح واژگان نکات توضیحی تفسیری دکترین مطالعات فقهی .۱ مستندات فقهی",
        "۲ توضیح واژگان نکات توضیحی تفسیری دکترین نکات توضیحی مذاکرات تصویب کتب مرتبط ۸",
        "۲ پیشینه تفسیری دکترین رویه‌های قضایی"
    ]

    for section in unwanted_sections:
        text = text.replace(section, '')

    text = re.sub(r'https?://\S+', '', text)  
    text = re.sub(r'رده‌ها:.*', '', text)  
    text = ' '.join(text.split())  
    return text.strip('"')  

async def extract_text(url, session):
    html = await fetch(url, session)
    soup = BeautifulSoup(html, 'html.parser')
    content = soup.find(id='bodyContent', class_='vector-body')

    if content:
        text = content.text.strip()
        text = clean_text(text)  
        return f'"{text}"'

    return ""

async def extract_category(url, session):
    html = await fetch(url, session)
    soup = BeautifulSoup(html, 'html.parser')
    heading = soup.find('h1', id='firstHeading', class_='firstHeading mw-first-heading')
    return heading.text.strip() if heading else "Unknown Category"

async def process_url(url, session):
    law_text = await extract_text(url, session)
    category = await extract_category(url, session)
    
    match = re.match(r'(ماده\s*\d+|اصل\s*\d+)(.*)', category)
    if match:
        law_number = match.group(1).strip()
        law_category_rest = match.group(2).strip()
    else:
        law_number = "Unknown Number"
        law_category_rest = category
    
    return law_number, law_text, law_category_rest, url

async def write_law():
    if not os.path.exists(input_file):
        print(f"Input file '{input_file}' does not exist.")
        return

    urls_df = pd.read_csv(input_file)
    urls = urls_df['Page URLs'].tolist()

    last_scraped_url = await get_last_scraped_url()
    print(f"Last scraped URL: {last_scraped_url}")
    start_scraping = not last_scraped_url

    law_numbers = []
    law_texts = []
    law_categories_rest = []
    law_urls = []

    async with aiohttp.ClientSession() as session:
        tasks = []
        url_count = 0  
        for url in urls:
            if not start_scraping:
                if url == last_scraped_url:
                    start_scraping = True
                continue

            task = process_url(url, session)
            tasks.append(task)
            url_count += 1  

            if url_count % 200 == 0:  
                results = await asyncio.gather(*tasks)
                for law_number, law_text, law_category_rest, law_url in results:
                    law_numbers.append(law_number)
                    law_texts.append(law_text)
                    law_categories_rest.append(law_category_rest)
                    law_urls.append(law_url)
                
                tasks = []  
                print("Processed 200 URLs, taking a 5-minute break...")
                await asyncio.sleep(300)  

        results = await asyncio.gather(*tasks)
        for law_number, law_text, law_category_rest, law_url in results:
            law_numbers.append(law_number)
            law_texts.append(law_text)
            law_categories_rest.append(law_category_rest)
            law_urls.append(law_url)

    if law_urls:
        new_data = pd.DataFrame({
            'Law Number': law_numbers,
            'Law Text': law_texts,
            'Category': law_categories_rest,
            'Law URL': law_urls
        })

        if os.path.exists(output_file):
            existing_data = pd.read_csv(output_file)
            combined_data = pd.concat([existing_data, new_data], ignore_index=True).drop_duplicates()
        else:
            combined_data = new_data

        combined_data.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Saved {len(law_urls)} new entries to '{output_file}'.")
    else:
        print("No new entries found to save.")

asyncio.run(write_law())
