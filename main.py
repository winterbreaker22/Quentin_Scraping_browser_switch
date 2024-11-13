import asyncio
import os
import pandas as pd
import time
from playwright.async_api import async_playwright

search_url = 'https://bexar.tx.publicsearch.us/'
db_url = 'https://bexar.trueautomation.com/clientdb/?cid=110'

doc_types = [29, 37, 47, 49, 50, 51, 55, 56, 60, 61, 77, 116]

async def run(playwright):
    csv_file = 'scraped_data.csv'
    
    browser = await playwright.chromium.launch(headless=False, args=['--start-maximized'])
    page = await browser.new_page(no_viewport=True) 

    await page.goto(search_url)
    time.sleep(5)

    await page.click('article#main-content >> text="Advanced Search"')  # Replace with the correct selector, if needed
    await page.keyboard.press("End")
    time.sleep(2)

    await page.click('input#docTypes-input')
    await page.click('div.tokenized-nested-select__dropdown #docTypes-item-0')
    await page.click('div.tokenized-nested-select__dropdown label[for="docTypes-item-1"]')
    await page.click('input#docTypes-input')
    await page.click('div.tokenized-nested-select__dropdown #docTypes-item-6')
    await page.click(f'div.tokenized-nested-select__dropdown label[for="docTypes-item-9"]')

    for doc_type in doc_types:
        await page.click('input#docTypes-input')
        element_selector = f'div.tokenized-nested-select__dropdown label[for="docTypes-item-{str(doc_type)}"]'
        element = page.locator(element_selector)
        await element.scroll_into_view_if_needed()
        await element.click()

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
