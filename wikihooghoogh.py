import os
import asyncio
import aiohttp
import pandas as pd
from bs4 import BeautifulSoup
from itertools import cycle
import re

input_file = 'urls_wikihoghoogh(1).csv'
output_file = 'laws_wikihoghoogh.csv'
proxy_file = 'IRproxy.csv'

def load_proxies(proxy_file):
    proxy_df = pd.read_csv(proxy_file, header=None, names=['proxy'])
    proxies = proxy_df['proxy'].tolist()
    return cycle(proxies)

async def fetch(url, session, proxy, retries=3, timeout=10):
    while retries > 0:
        try:
            async with session.get(url, proxy=f"http://{proxy}", timeout=timeout) as response:
                if response.status == 429:
                    raise aiohttp.ClientError("Too many requests (429)")
                return await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            retries -= 1
    raise aiohttp.ClientError(f"Failed to fetch {url} after retries.")

def process_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    content = soup.find(class_='mw-parser-output')
    if content:
        paragraphs = []
        for tag in content.children:
            if tag.name == 'ul':
                break
            if tag.name == 'p':
                paragraphs.append(tag.text.strip())
        return ' '.join(paragraphs)
    return ""

async def extract_text(url, session, proxy):
    html = await fetch(url, session, proxy)
    return await asyncio.to_thread(process_html, html)

async def extract_category_and_title(url, session, proxy):
    html = await fetch(url, session, proxy)
    soup = BeautifulSoup(html, 'html.parser')
    heading = soup.find('h1', id='firstHeading', class_='firstHeading mw-first-heading')
    if heading:
        category_text = heading.text.strip()
        title_match = re.match(r'(اصل \d+|ماده \d+)', category_text)
        title = title_match.group(0) if title_match else "Unknown Title"
        category = category_text[len(title):].strip() if title_match else category_text
        return title, category
    return "Unknown Title", "Unknown Category"

async def process_url(url, session, proxy):
    law_text = await extract_text(url, session, proxy)
    title, category = await extract_category_and_title(url, session, proxy)
    return title, law_text, category, url

async def write_law():
    if not os.path.exists(input_file):
        return

    urls_df = pd.read_csv(input_file)
    urls = urls_df['Page URLs'].tolist()
    proxies = load_proxies(proxy_file)

    last_scraped_url = None
    if os.path.exists(output_file):
        existing_data = pd.read_csv(output_file)
        last_scraped_url = existing_data.iloc[-1]['URL']
    else:
        existing_data = pd.DataFrame(columns=['Title', 'Text', 'Category', 'URL'])

    start_scraping = not last_scraped_url
    results = []
    current_proxy = next(proxies)

    async with aiohttp.ClientSession() as session:
        for url in urls:
            if not start_scraping and url == last_scraped_url:
                start_scraping = True
                continue

            if existing_data['URL'].str.contains(url, regex=False).any():
                continue

            try:
                result = await process_url(url, session, current_proxy)
                results.append(result)
            except aiohttp.ClientError:
                current_proxy = next(proxies)
                continue

        new_data = pd.DataFrame(results, columns=['Title', 'Text', 'Category', 'URL'])
        combined_data = pd.concat([existing_data, new_data], ignore_index=True).drop_duplicates()
        combined_data.to_csv(output_file, index=False, encoding='utf-8-sig')

asyncio.run(write_law())
