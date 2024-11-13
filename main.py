import asyncio
import os
import pandas as pd
from playwright.async_api import async_playwright

async def run(playwright):
    # Define the path to the CSV file
    csv_file = 'scraped_data.csv'
    
    # Launch the browser
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()

    # Go to the target URL
    url = "https://example.com"  # Replace with the target URL
    await page.goto(url)

    # Example: Click a button to load the table, if necessary
    await page.click('button#load-table')  # Replace with the correct selector, if needed

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

# Run the script
if __name__ == "__main__":
    asyncio.run(main())
