from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
import psycopg2
from supabase import create_client, Client
from decimal import Decimal
from json import JSONEncoder
import asyncio
import time
from urllib.parse import urlparse
import tempfile
import decimal
from pyvirtualdisplay import Display
import chromedriver_autoinstaller
import re


class DecimalEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


def get_deal_products():
    conn = psycopg2.connect(
        dbname="postgres",  # Usually, this is 'postgres'
        user="postgres",  # Usually, this is 'postgres'
        password="5giE*5Y5Uexi3P2",
        host="db.sxoqzllwkjfluhskqlfl.supabase.co",
    )
    # Create a cursor
    cursor = conn.cursor()

    # Execute the SQL query to retrieve relevant data from the "productfinder_keepa_raw" table
    query = """
            SELECT 
            a.sys_run_date,
            a.product_id,
            a.product_title,
            a.product_url,
            a.product_image,
            a.product_price,
            a.product_size,
            a.product_color,
            a.product_pack,
            a.product_attr,
            a.product_brand,
            a.amazon_title,
            a.amazon_url,
            a.amazon_image,
            a.amazon_category,
            a.brand,
            a.amazon_size,
            a.amazon_color,
            a.asin,
            a.amazon_pack,
            a.buy_box_current_price,
            a.buy_box_90_days_avg_price,
            a.image_matching, 
                ROUND(
                    a.product_price / COALESCE(a.product_pack, 1) * (
                        CASE WHEN a.amazon_pack > 0 THEN a.amazon_pack ELSE 1 END
                    ),
                    2
                ) AS total_cost_price

            FROM 
                product_seller_amazon_mapping a
            LEFT JOIN 
                product_keepa b ON a.sys_run_date = b.sys_run_date AND a.asin = b.asin
            LEFT JOIN 
                seller_product_data c ON a.sys_run_date = c.sys_run_date AND a.product_id = c.product_id
            left join product_data_mapping_finals d on a.sys_run_date=d.sys_run_date and a.asin=d.asin and a.product_id = d.product_id
            WHERE 
                a.image_matching IS NULL
                AND a.product_brand = a.brand
                AND COALESCE(b.sales_rank_drops_last_90_days, 0) >= 10
                AND COALESCE(b.Reviews_Review_Count, 0) >= 3
                AND COALESCE(b.buy_box_90_days_avg_price, 0) >= 20
                AND COALESCE(b.Buy_Box_Is_FBA, 'no') = 'no'
                AND COALESCE(b.Count_of_Retrieved_Live_Offers_New_FBA, 0) = 0
                AND c.product_availabilitystatus NOT IN ('OUT_OF_STOCK')
                AND d.product_id is null
            ORDER BY a.sys_run_date;
    """
    cursor.execute(query)
    # Fetch all the rows as a list
    deal_products = cursor.fetchall()
    return deal_products


async def run_parallel(limit, function_name, refresh_rate):
    semaphore = asyncio.Semaphore(value=limit)

    while True:
        deal_products = get_deal_products()  # Fetch the latest products
        if not deal_products:
            print("No more products to process. Exiting.")
            break

        for j, deal_product in enumerate(deal_products):
            # Wrap the function call in a task, managing concurrency with the semaphore
            task = asyncio.create_task(
                wrapper(semaphore, function_name, deal_product, j)
            )

            # Wait for the task to complete before continuing
            await task

            if refresh_rate > 0:
                await asyncio.sleep(refresh_rate)

            # Refresh `deal_products` by fetching new data
            # This is critical if your `get_deal_products` function has side effects
            # or if the database changes frequently
            deal_products = get_deal_products()

            if not deal_products:
                print("No more products to process after refresh. Exiting.")
                break

        # If needed, add any conditions to break out of the while loop here


async def wrapper(semaphore, function_name, *args, **kwargs):
    async with semaphore:
        result = await asyncio.to_thread(function_name, *args, **kwargs)
        return result


def search_row(row, counter, est_sales_min_threshold=10):
    print("counter: ", counter)
    print(row)
    (
        sys_run_date,
        product_id,
        product_title,
        product_url,
        product_image,
        product_price,
        product_size,
        product_color,
        product_pack,
        product_attr,
        product_brand,
        amazon_title,
        amazon_url,
        amazon_image,
        amazon_category,
        brand,
        amazon_size,
        amazon_color,
        asin,
        amazon_pack,
        buy_box_current_price,
        buy_box_90_days_avg_price,
        image_matching,
        total_cost_price,
    ) = row
    data_df = {}
    data_df = {
        "sys_run_date": sys_run_date,
        "product_id": product_id,
        "product_title": product_title,
        "product_url": product_url,
        "product_image": product_image,
        "product_price": product_price,
        "product_size": product_size,
        "product_color": product_color,
        "product_pack": product_pack,
        "product_attr": product_attr,
        "product_brand": product_brand,
        "amazon_title": amazon_title,
        "amazon_url": amazon_url,
        "amazon_image": amazon_image,
        "amazon_category": amazon_category,
        "brand": brand,
        "amazon_size": amazon_size,
        "amazon_color": amazon_color,
        "asin": asin,
        "amazon_pack": amazon_pack,
        "buy_box_current_price": buy_box_current_price,
        "buy_box_90_days_avg_price": buy_box_90_days_avg_price,
        "image_matching": image_matching,
        "total_cost_price": total_cost_price,
    }
    for key, value in data_df.items():
        if isinstance(value, decimal.Decimal):
            data_df[key] = float(value)
    driver = webdriver.Chrome(options=chrome_options)
    # Open SellerAmp
    driver.get("https://sas.selleramp.com/site/login")
    wait = WebDriverWait(driver, 20)
    # Login process
    try:
        username_field = wait.until(
            EC.visibility_of_element_located((By.ID, "loginform-email"))
        )
        username_field.send_keys(username_selleramp)

        password_field = driver.find_element(By.ID, "loginform-password")
        password_field.send_keys(password_selleramp)
        password_field.send_keys(Keys.RETURN)
        time.sleep(8)
    except:
        raise Exception("Error during login SellerAmp")

    try:
        asin_field = wait.until(
            EC.visibility_of_element_located((By.ID, "saslookup-search_term"))
        )
        asin_field.send_keys(asin)
        search_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//*[@id="sas-calc-form"]/div/div/div/div/div/div[2]/button',
                )
            )
        )
        search_button.click()
        time.sleep(20)

        # Execute JavaScript to clear the input field
        driver.execute_script("document.getElementById('qi_cost').value = ''")
        costprice_input = wait.until(
            EC.visibility_of_element_located((By.ID, "qi_cost"))
        )
        # costprice_input.clear()
        costprice_input.send_keys(data_df["total_cost_price"])
        time.sleep(2)

        bsr_element = wait.until(EC.visibility_of_element_located((By.ID, "qi-bsr")))
        bsr_text = bsr_element.text
        bsr_value = bsr_text.split()[0]

        estsale_element = wait.until(
            EC.visibility_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "#qi-estimated-sales > span.estimated_sales_per_mo",
                )
            )
        )
        estsale_text = estsale_element.text
        estsale_value = float(extract_number(estsale_text))

        profit_element = wait.until(
            EC.visibility_of_element_located((By.ID, "qi-profit"))
        )
        profit_text = profit_element.text
        profit_value = float(extract_number(profit_text))

        roi_element = wait.until(
            EC.visibility_of_element_located((By.ID, "saslookup-roi"))
        )
        roi_text = roi_element.text
        roi_value = float(extract_number(roi_text))

        fee_element = wait.until(
            EC.visibility_of_element_located((By.ID, "saslookup-total_fee"))
        )
        fee_text = fee_element.text
        fee_value = float(extract_number(fee_text))
        # Convert row to dictionary
        data_df = {
            "sys_run_date": sys_run_date.strftime("%Y-%m-%d"),
            "product_id": product_id,
            "product_title": product_title,
            "product_url": product_url,
            "product_image": product_image,
            "product_price": product_price,
            "product_size": product_size,
            "product_color": product_color,
            "product_pack": product_pack,
            "product_attr": product_attr,
            "product_brand": product_brand,
            "amazon_title": amazon_title,
            "amazon_url": amazon_url,
            "amazon_image": amazon_image,
            "amazon_category": amazon_category,
            "brand": brand,
            "amazon_size": amazon_size,
            "amazon_color": amazon_color,
            "asin": asin,
            "amazon_pack": amazon_pack,
            "buy_box_current_price": buy_box_current_price,
            "buy_box_90_days_avg_price": buy_box_90_days_avg_price,
            "image_matching": image_matching,
            "total_cost_price": total_cost_price,
            "bsr_percent": bsr_value,
            "est_sale": estsale_value,
            "profit": profit_value,
            "roi": roi_value,
            "total_fee": fee_value,
        }
        for key, value in data_df.items():
            if isinstance(value, decimal.Decimal):
                data_df[key] = float(value)
        try:
            response2 = (
                supabase.table("product_data_mapping_finals").insert(data_df).execute()
            )
            if hasattr(response2, "error") and response2.error is not None:
                print(f"Error inserting row: {response2.error}")

            print(f"Row inserted at:{data_df}")
        except Exception as e:
            print(f"Error with row at index {asin}: {e}")
    except Exception as e:
        print(e)
        driver.quit()


def extract_number(text):
    # Regular expression to find numbers, including those with commas as thousand separators and periods as decimal points
    # This regex also accounts for optional leading characters (e.g., ">") and trailing text or symbols (e.g., "$" or "below")
    match = re.search(
        r"([<>]?)(\d{1,3}(?:,\d{3})*(?:\.\d+)?)(\s*[$€£]?)", text.replace(",", "")
    )
    if match:
        # Extract the numeric part and convert commas to dots if necessary for decimal
        number_str = match.group(2).replace(",", "")
        number = float(number_str)
        # Check for a leading '<' or '>' to adjust the number slightly to reflect it's an approximation
        if match.group(1) == ">":
            number += 0.01  # Assuming the number is slightly greater
        elif match.group(1) == "<":
            number -= 0.01  # Assuming the number is slightly less
        return number
    else:
        # If no number is found, return None or raise an error based on your needs
        return None


SUPABASE_URL = "https://sxoqzllwkjfluhskqlfl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN4b3F6bGx3a2pmbHVoc2txbGZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MDIyODE1MTcsImV4cCI6MjAxNzg1NzUxN30.FInynnvuqN8JeonrHa9pTXuQXMp9tE4LO0g5gj0adYE"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Replace these with your Keepa username and password
username_selleramp = "greatwallpurchasingdept@gmail.com"
password_selleramp = "H@h@h@365!"

display = Display(visible=0, size=(800, 800))
display.start()

chromedriver_autoinstaller.install()  # Check if the current version of chromedriver exists

# Create a temporary directory for downloads
with tempfile.TemporaryDirectory() as download_dir:
    # and if it doesn't exist, download it automatically,
    # then add chromedriver to path
    chrome_options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    options = [
        # Define window size here
        "--window-size=1200,1200",
        "--ignore-certificate-errors",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
    ]
    chrome_options.add_experimental_option("prefs", prefs)
    for option in options:
        chrome_options.add_argument(option)


deal_products = get_deal_products()
print("running")
print("len deal products: ", len(deal_products))

limit = 5
# begin = 2
# end = 4
begin = 0
end = len(deal_products)

# Adjust the call to run_parallel to include refresh_rate
data = asyncio.run(
    run_parallel(
        limit,  # Adjust as needed
        function_name=search_row,
        refresh_rate=2,  # Set your desired refresh rate
    )
)
print("done")
