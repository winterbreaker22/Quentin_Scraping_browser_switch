import asyncio
import os
import re
import csv
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from dateutil.relativedelta import relativedelta
import pygetwindow as gw
import psutil

search_url = 'https://bexar.tx.publicsearch.us/'
db_url = 'https://bexar.trueautomation.com/clientdb/?cid=110'

doc_types = [
    { 'name': 'FEDERAL TAX LIEN', 'count': 1 },
    { 'name': 'AFFIDAVIT', 'count': 1 },
    { 'name': 'CHILD SUPPORT LN', 'count': 1 },
    { 'name': 'DECREE', 'count': 1 },
    { 'name': 'FORECLOSURE', 'count': 1 },
    { 'name': 'HOSPITAL LIEN', 'count': 1 },
    { 'name': 'JUDGMENT', 'count': 3 },
    { 'name': 'LANDLORD LIEN', 'count': 1 },
    { 'name': 'LIEN', 'count': 7 },
    { 'name': 'LIS PENDENS', 'count': 1 },
    { 'name': 'MECHANICS LIEN', 'count': 1 },
    { 'name': 'MEMORANDUM', 'count': 1 },
    { 'name': 'PROBATE', 'count': 1 },
    { 'name': 'WILL & TESTAMENT', 'count': 1 },
]

property_address_for_search = ''
detail_search = False
pid = 0

async def run_search_thread(playwright):
    global detail_search
    global property_address_for_search
    global pid
    
    browser = await playwright.chromium.launch(headless=False, args=['--start-maximized'])
    page = await browser.new_page(no_viewport=True) 
    await page.goto(search_url)
    await asyncio.sleep(5)
    pid = os.getpid()
    print (pid)

    while True:
        if not detail_search:
            await page.bring_to_front()

            await page.click('article#main-content >> text="Advanced Search"')  # Replace with the correct selector, if needed
            await page.keyboard.press("End")
            await asyncio.sleep(2)

            today = datetime.today()
            one_month_ago = today - relativedelta(months=1)

            await page.fill('#recordedDateRange', str(one_month_ago.strftime(f'%m/%d/%Y')))
            await page.fill('div.form-field-inline-datepicker > div:last-of-type input', str(today.strftime(f'%m/%d/%Y')))
            await asyncio.sleep(2)

            for doc_type in doc_types:
                await page.fill('input#docTypes-input', doc_type['name'])
                await page.click(f'div.tokenized-nested-select__dropdown label[for="docTypes-item-{str(doc_type['count'])}"]')
            
            await page.click('button[type="submit"]')
            await asyncio.sleep(10)

            rows = page.locator('table tbody tr')  
            row_count = await rows.count()

            for i in range(row_count):
                address = await rows.nth(i).locator('td.col-14 span').text_content()
                if address == 'N/A':
                    detail_search = False
                    continue 
                pieces = re.split(r'[,\s]+', address)
                if len(pieces) < 3:
                    detail_search = False
                    continue 
                property_address_for_search = ' '.join(pieces[:3])
                detail_search = True
        await asyncio.sleep(1)

    await browser.close()

async def run_db_thread(playwright):
    global detail_search
    global property_address_for_search
    
    csv_file = 'info.csv'
    headers = ["First Name", "Last Name", "Mailing Address", "Mailing City", "Mailing State", "Mailing Zip",
               "Property Address", "Property City", "Property State", "Property Zip"]

    file_exists = os.path.exists(csv_file)
    with open(csv_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(headers)
            
    browser = await playwright.chromium.launch(headless=False, args=['--start-maximized'])
    page = await browser.new_page(no_viewport=True) 
    await page.goto(db_url)
    await asyncio.sleep(5)

    while True:
        if detail_search:
            await page.bring_to_front()

            await page.fill('#propertySearchOptions_searchText', property_address_for_search)
            await page.click('#propertySearchOptions_search')
            await asyncio.sleep(5)

            rows = page.locator('#propertySearchResults_resultsTable tbody tr')  
            row_count = await rows.count()
            if row_count > 3:
                for i in range(row_count - 2):
                    await rows.nth(i + 1).locator('td:nth-last-of-type(2) a').click()   
                    await asyncio.sleep(3)

                    owner = page.locator('table tbody tr') 

                    # Name
                    full_name = await rows.nth(16).locator('td:nth-of-type(2)').text_content()
                    parts = full_name.split()
                    if len(parts) == 3:
                        first_name, middle_name, last_name = parts
                    elif len(parts) == 2:
                        first_name, last_name = parts
                        middle_name = ''

                    # Mailing address
                    mailing_address_full = await rows.nth(17).locator('td:nth-of-type(2)').text_content()
                    parts = mailing_address_full.split("<br>")
                    mailing_address = parts[0]
                    mailing_city = parts[-1].split(' ')[0]
                    mailing_state = parts[-1].split(' ')[1]
                    mailing_zip = parts[-1].split(' ')[-1]

                    # Property address
                    property_address_full = await rows.nth(12).locator('td:nth-of-type(2)').text_content()
                    parts = property_address_full.split("<br>")
                    property_address = parts[0]
                    property_city = parts[-1].split(' ')[0]
                    property_state = parts[-1].split(' ')[1]
                    property_zip = parts[-1].split(' ')[-1]

                    one_row = [first_name, last_name, mailing_address, mailing_city, mailing_state, mailing_zip, 
                               property_address, property_city, property_state, property_zip]
                    writer.writerow(one_row)

                await page.click('#header_PropertySearch')
                detail_search = False
        await asyncio.sleep(1)

    await browser.close()

async def run_switch_thread(playwright):
    global detail_search
    global pid

    await asyncio.sleep(20)
    print (pid)

    windows = gw.getAllWindows()
    print (windows)


async def main():
    async with async_playwright() as playwright:
        task_search = asyncio.create_task(run_search_thread(playwright))
        task_db = asyncio.create_task(run_db_thread(playwright))
        task_switch = asyncio.create_task(run_switch_thread(playwright))
        await asyncio.gather(task_db, task_search, task_switch)

if __name__ == "__main__":
    asyncio.run(main())
