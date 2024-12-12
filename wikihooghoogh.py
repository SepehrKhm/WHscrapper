import os
import asyncio
import aiohttp
import pandas as pd
from bs4 import BeautifulSoup
from itertools import cycle

input_file = 'urls_wikihoghoogh(1).csv'
output_file = 'laws_wikihoghoogh.csv'
proxy_file = 'IRproxy.csv'

def load_proxies(proxy_file):
    proxy_df = pd.read_csv(proxy_file)
    proxies = proxy_df['proxy'].tolist()  
    return cycle(proxies)  

async def fetch(url, session, proxy, retries=3, timeout=10):
    while retries > 0:
        try:
            async with session.get(url, proxy=f"http://{proxy}", timeout=timeout) as response:
                if response.status == 429:
                    raise aiohttp.ClientError("Too many requests (429)")
                return await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"Error with proxy {proxy}: {e}. Retrying...")
            retries -= 1
    raise aiohttp.ClientError(f"Failed to fetch {url} after retries.")

def process_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    content = soup.find(class_='mw-parser-output')
    if content:
        first_paragraph = content.find('p')
        return first_paragraph.text.strip() if first_paragraph else ""
    return ""

async def extract_text(url, session, proxy):
    html = await fetch(url, session, proxy)
    return await asyncio.to_thread(process_html, html)

async def extract_category(url, session, proxy):
    html = await fetch(url, session, proxy)
    soup = BeautifulSoup(html, 'html.parser')
    heading = soup.find('h1', id='firstHeading', class_='firstHeading mw-first-heading')
    return heading.text.strip() if heading else "Unknown Category"

async def process_url(url, session, proxy):
    law_text = await extract_text(url, session, proxy)
    category = await extract_category(url, session, proxy)
    return category, law_text, url

async def write_law():
    if not os.path.exists(input_file):
        print(f"Input file '{input_file}' does not exist.")
        return

    urls_df = pd.read_csv(input_file)
    urls = urls_df['Page URLs'].tolist()
    proxies = load_proxies(proxy_file)

    last_scraped_url = None
    if os.path.exists(output_file):
        existing_data = pd.read_csv(output_file)
        last_scraped_url = existing_data.iloc[-1]['URL']
        print(f"Resuming from last scraped URL: {last_scraped_url}")

    start_scraping = not last_scraped_url
    results = []
    current_proxy = next(proxies)

    async with aiohttp.ClientSession() as session:
        for url in urls:
            if not start_scraping and url == last_scraped_url:
                start_scraping = True
                continue

            try:
                result = await process_url(url, session, current_proxy)
                results.append(result)
            except aiohttp.ClientError:
                current_proxy = next(proxies)
                print(f"Switching proxy: {current_proxy}")
                continue

        new_data = pd.DataFrame(results, columns=['Category', 'Text', 'URL'])
        if os.path.exists(output_file):
            existing_data = pd.read_csv(output_file)
            combined_data = pd.concat([existing_data, new_data], ignore_index=True).drop_duplicates()
        else:
            combined_data = new_data
        combined_data.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Saved {len(results)} entries to '{output_file}'.")

asyncio.run(write_law())
