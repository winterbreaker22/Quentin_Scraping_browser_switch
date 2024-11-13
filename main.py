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

async def run(playwright):
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
    today_str = today.strftime('%m/%d/%y')
    one_month_ago_str = one_month_ago.strftime('%m/%d/%y')
    await page.fill('#recordedDateRange', one_month_ago_str)
    time.sleep(2)
    await page.fill('input[aria-label="end date"]', today_str)
    time.sleep(2)

    for doc_type in doc_types:
        await page.fill('input#docTypes-input', doc_type['name'])
        await page.click(f'div.tokenized-nested-select__dropdown label[for="docTypes-item-{str(doc_type['count'])}"]')

    time.sleep(10)










    # Wait for table to load
    await page.wait_for_selector('table#data-table')  # Replace with the table's selector

    # Extract data from each row of the table
    rows = await page.query_selector_all('table#data-table tr')  # Replace with the actual table row selector

    # Check if the CSV file exists; if not, we'll create and add headers
    file_exists = os.path.isfile(csv_file)

    for row in rows[1:]:  # Skipping the header row if the table has headers
        cells = await row.query_selector_all('td')
        
        # Extract text from each cell in the row
        row_data = [await cell.inner_text() for cell in cells]

        # Convert row data to a DataFrame and append it to the CSV file
        row_df = pd.DataFrame([row_data])

        # Append to CSV, without headers if the file already exists
        row_df.to_csv(csv_file, mode='a', header=not file_exists, index=False)
        file_exists = True  # After first row, set file_exists to True to skip headers in future rows

    print("Data has been updated in scraped_data.csv")

    # Close the browser
    await browser.close()

async def main():
    async with async_playwright() as playwright:
        await run(playwright)

if __name__ == "__main__":
    asyncio.run(main())
