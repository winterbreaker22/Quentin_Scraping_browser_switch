import asyncio
import os
import pandas as pd
import time
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from dateutil.relativedelta import relativedelta

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

async def run_search_thread(playwright):
    csv_file = 'scraped_data.csv'
    
    browser = await playwright.chromium.launch(headless=False, args=['--start-maximized'])
    page = await browser.new_page(no_viewport=True) 

    await page.goto(search_url)
    time.sleep(5)

    await page.click('article#main-content >> text="Advanced Search"')  # Replace with the correct selector, if needed
    await page.keyboard.press("End")
    time.sleep(2)

    today = datetime.today()
    one_month_ago = today - relativedelta(months=1)

    await page.fill('#recordedDateRange', str(one_month_ago.strftime(f'%m/%d/%Y')))
    await page.fill('div.form-field-inline-datepicker > div:last-of-type input', str(today.strftime(f'%m/%d/%Y')))
    time.sleep(2)

    for doc_type in doc_types:
        await page.fill('input#docTypes-input', doc_type['name'])
        await page.click(f'div.tokenized-nested-select__dropdown label[for="docTypes-item-{str(doc_type['count'])}"]')
    
    await page.click('button[type="submit"]')
    time.sleep(10)

    rows = page.locator('table tbody tr')  
    row_count = await rows.count()

    # Check if the CSV file exists; if not, we'll create and add headers
    file_exists = os.path.isfile(csv_file)

    for i in range(row_count):
        property_address = await rows.nth(i).locator('td.col-14 span').text_content()
        print (property_address)
        
        # Extract text from each cell in the row
        # row_data = [await cell.inner_text() for cell in cells]

        # # Convert row data to a DataFrame and append it to the CSV file
        # row_df = pd.DataFrame([row_data])

        # # Append to CSV, without headers if the file already exists
        # row_df.to_csv(csv_file, mode='a', header=not file_exists, index=False)
        # file_exists = True  # After first row, set file_exists to True to skip headers in future rows

    print("Data has been updated in scraped_data.csv")

    # Close the browser
    await browser.close()

async def run_db_thread(playwright):
    browser = await playwright.chromium.launch(headless=False, args=['--start-maximized'])
    page = await browser.new_page(no_viewport=True) 

    await page.goto(db_url)
    time.sleep(5)

async def main():
    async with async_playwright() as playwright:
        task_search = asyncio.create_task(run_search_thread(playwright))
        task_db = asyncio.create_task(run_db_thread(playwright))
        await asyncio.gather(task_search, task_db)

if __name__ == "__main__":
    asyncio.run(main())
