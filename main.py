import asyncio
import os
import re
import csv
import playwright
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from dateutil.relativedelta import relativedelta
import pygetwindow as gw
import pyautogui
import psutil
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

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
PID = 0
HWND_SEARCH = 0
HWND_DB = 0
scraping_finished = False
current_doc_type = ''

def get_windows_with_pid_and_hwnd(pid, target_hwnd):
    windows = gw.getWindowsWithTitle('')
    windows_with_pid_and_hwnd = []
    
    for window in windows:
        try:
            process_id = None
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['pid'] == pid:
                    process_id = proc.info['pid']
                    break
            
            # Check if the window belongs to the specified process and matches the target hwnd
            if process_id == pid and window._hWnd == target_hwnd:
                windows_with_pid_and_hwnd.append(window)
        
        except Exception as e:
            print(f"Error retrieving window information: {e}")
    
    return windows_with_pid_and_hwnd

def get_pid_from_window_handle(window_handle):
    pid = wintypes.DWORD() 
    user32.GetWindowThreadProcessId(window_handle, ctypes.byref(pid))
    return pid.value

async def run_search_thread(playwright):
    global detail_search
    global property_address_for_search
    global PID
    global HWND_SEARCH
    global scraping_finished
    global current_doc_type

    await asyncio.sleep(10)
    browser = await playwright.chromium.launch(
        headless=False, 
        args=[
            "--start-maximized",
            "--remote-debugging-port=9222",
        ],
    )
    page = await browser.new_page(no_viewport=True) 
    await page.goto(search_url)
    await asyncio.sleep(5)

    HWND_SEARCH = ctypes.windll.user32.GetForegroundWindow()
    PID = get_pid_from_window_handle(HWND_SEARCH)

    await page.click('article#main-content >> text="Advanced Search"')  # Replace with the correct selector, if needed
    await page.keyboard.press("End")
    await asyncio.sleep(2)

    today = datetime.today()
    one_month_ago = today - relativedelta(months=1)

    await page.fill('#recordedDateRange', str(one_month_ago.strftime(f'%m/%d/%Y')))
    await page.fill('div.form-field-inline-datepicker > div:last-of-type input', str(today.strftime(f'%m/%d/%Y')))
    await asyncio.sleep(2)
    pyautogui.click(x=100, y=100)
    await asyncio.sleep(2)

    for doc_type in doc_types:
        await page.fill('input#docTypes-input', doc_type['name'])
        await page.click(f'div.tokenized-nested-select__dropdown label[for="docTypes-item-{str(doc_type['count'])}"]')
    
    await page.click('button[type="submit"]')
    await asyncio.sleep(10)

    result_element = page.locator('p[data-testid="resultsSummary"] > span:first-of-type')
    result = await result_element.text_content()
    total = result.split()[2].replace(',', '')

    total_page_number = int(total) / 50 + 1
    last_page_row_number = int(total) % 50

    search_row_number = 0
    search_page_number = 1
    while True:
        if not detail_search:
            rows = page.locator('table tbody tr')  
            current_doc_type = await rows.nth(search_row_number).locator('td.col-5 span').text_content()
            address_element = rows.nth(search_row_number).locator('td.col-14 span')
            await address_element.scroll_into_view_if_needed()
            property_address_for_search = await address_element.text_content()
            search_row_number = search_row_number + 1

            last_row_index = last_page_row_number if search_page_number == total_page_number else 50
            if search_row_number == last_row_index:
                search_row_number = 0
                await asyncio.sleep(2)
                await page.click('nav.Pagination > div > button:last-of-type')
                await asyncio.sleep(5)
                if search_page_number != total_page_number:
                    search_page_number = search_page_number + 1
                else:
                    scraping_finished = True
                    break
            if property_address_for_search == 'N/A':
                continue 
            
            detail_search = True
        await asyncio.sleep(1)

    await browser.close()

async def run_db_thread(playwright):
    global detail_search
    global property_address_for_search
    global PID
    global HWND_DB
    global scraping_finished
    global current_doc_type
    
    browser = await playwright.chromium.launch(
        headless=False, 
        args=[
            "--start-maximized",
            "--remote-debugging-port=9223",
        ],
    )
    page = await browser.new_page(no_viewport=True) 
    await page.goto(db_url)

    HWND_DB = ctypes.windll.user32.GetForegroundWindow()
    PID = get_pid_from_window_handle(HWND_DB)

    await asyncio.sleep(5)
    
    csv_file = 'info.csv'
    headers = ["First Name", "Last Name", "Mailing Address", "Mailing City", "Mailing State", "Mailing Zip",
               "Property Address", "Property City", "Property State", "Property Zip", "Doc Type", "Exemption"]

    file_exists = os.path.exists(csv_file)
    if file_exists:
        with open(csv_file, 'w') as file:
            pass
    with open(csv_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
    
    while True:
        if detail_search:
            await page.wait_for_selector("#propertySearchOptions_advanced", state='visible', timeout=5000) 
            await page.click('#propertySearchOptions_advanced')
            await asyncio.sleep(2)
            address_parts = property_address_for_search.split(',')
            first_part = address_parts[0].strip()
            words = first_part.split(' ')
            street_number = words[0] 
            street_name = ' '.join(words[1:])
            await page.fill('#propertySearchOptions_streetNumber', street_number)
            await page.fill('#propertySearchOptions_streetName', street_name)
            await page.click('#propertySearchOptions_searchAdv')
            await asyncio.sleep(5)

            rows = page.locator('#propertySearchResults_resultsTable tbody tr')  
            row_count = await rows.count()
            if row_count > 2:
                for i in range(row_count - 2):
                    view_details = rows.nth(i + 1).locator('td:nth-last-of-type(2) a')
                    if not view_details:
                        continue
                    await view_details.wait_for(state="visible")
                    await view_details.click()   
                    await asyncio.sleep(2)

                    owner = page.locator('table tbody tr') 
                    full_name = await owner.nth(15).locator('td:nth-of-type(2)').text_content()
                    print ("full name: ", full_name)
                    parts = full_name.split()
                    first_name = middle_name = last_name = ''
                    if len(parts) > 3:
                        first_name, middle_name, last_name = parts[:3]
                    elif len(parts) == 3:
                        first_name, middle_name, last_name = parts
                    elif len(parts) == 2:
                        first_name, last_name = parts
                        middle_name = ''
                    if first_name == '&':
                        first_name = ''
                    if last_name == '&':
                        last_name = ''
                        
                    mailing_address_full = await owner.nth(16).locator('td:nth-of-type(2)').text_content()
                    parts = mailing_address_full.split('  ')
                    mailing_address = parts[0] if len(parts) > 0 else ''
                    sub_parts = parts[-1].strip(',') if len(parts) > 0 else ''
                    city_state_zip = sub_parts.rsplit(' ', 2)
                    mailing_city = city_state_zip[0].rstrip(',') if len(city_state_zip) > 0 else ''
                    mailing_state = city_state_zip[1] if len(city_state_zip) > 1 else ''
                    mailing_zip = city_state_zip[2] if len(city_state_zip) > 2 else ''

                    # Property address
                    property_address_full = await owner.nth(11).locator('td:nth-of-type(2)').text_content()
                    parts = property_address_full.split('  ')
                    property_address = parts[0] if len(parts) > 0 else ''
                    sub_parts = parts[-1].strip(',') if len(parts) > 0 else ''
                    city_state_zip = sub_parts.rsplit(' ', 2)
                    property_city = city_state_zip[0].rstrip(',') if len(city_state_zip) > 0 else ''
                    property_state = city_state_zip[1] if len(city_state_zip) > 1 else ''
                    property_zip = city_state_zip[2] if len(city_state_zip) > 2 else ''
                    doc_type = current_doc_type
                    exemption = await owner.nth(17).locator('td:last-of-type').text_content()

                    one_row = [first_name, last_name, mailing_address, mailing_city, mailing_state, mailing_zip, 
                               property_address, property_city, property_state, property_zip, doc_type, exemption]

                    with open(csv_file, mode='a', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerow(one_row)
                    await page.go_back()
                    await asyncio.sleep(2)

            await page.wait_for_selector("#header_PropertySearch", state='visible', timeout=5000) 
            await page.click('#header_PropertySearch')
            detail_search = False
        
        if scraping_finished:
            break
        await asyncio.sleep(1)

    await browser.close()

async def run_switch_thread(playwright):
    global detail_search
    global PID
    global HWND_DB
    global HWND_SEARCH
    global scraping_finished

    await asyncio.sleep(30)
    print ("db: ", HWND_DB)
    print ("search: ", HWND_SEARCH)

    while True:
        if detail_search:
            ctypes.windll.user32.SetForegroundWindow(HWND_DB)
        else:
            ctypes.windll.user32.SetForegroundWindow(HWND_SEARCH)
        if scraping_finished:
            break
        await asyncio.sleep(1)

async def main():
    async with async_playwright() as playwright:
        task_search = asyncio.create_task(run_search_thread(playwright))
        task_db = asyncio.create_task(run_db_thread(playwright))
        task_switch = asyncio.create_task(run_switch_thread(playwright))
        await asyncio.gather(task_db, task_search, task_switch)

if __name__ == "__main__":
    asyncio.run(main())
