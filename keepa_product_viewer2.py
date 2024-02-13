from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from google_img_source_search import ReverseImageSearcher
import psycopg2
from supabase import create_client, Client
from decimal import Decimal
from json import JSONEncoder
import os
import asyncio
import pandas as pd
import numpy as np
import time
from urllib.parse import urlparse
import tempfile
import imaplib
import email
import re
import glob
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
import unicodedata
import decimal
from pyvirtualdisplay import Display
import chromedriver_autoinstaller


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
                distinct a.sys_run_date,
                a.product_id,
                a.product_title,
                a.product_url_href product_url,
                a.product_image_1_src product_image,
                a.product_price,
                a.product_variants->>'size' product_size,
                a.product_variants->>'color' product_color,
                a.product_variants->>'pack' product_pack,
                a.product_variants->>'attr' product_attr,
                a.product_brand
                from seller_product_data a 
                left join product_seller_amazon_mapping b on a.product_id=b.product_id and a.sys_run_date=b.sys_run_date
                where a.sys_run_date in (select max(sys_run_date) from seller_product_data)
                and b.product_id is null 
                and lower(a.product_brand) not in (select lower(brand) from "IP_Brand") 
                and a.product_id not in (select distinct product_id from mapping_finals);
    """
    cursor.execute(query)
    # Fetch all the rows as a list
    deal_products = cursor.fetchall()
    return deal_products


async def run_parallel(limit, function_name, begin, end,refresh_rate):
    semaphore = asyncio.Semaphore(value=limit)

    while True:
        deal_products = get_deal_products()  # Fetch the latest products
        if not deal_products:
            print("No more products to process. Exiting.")
            break

        for j in range(begin,end):
            # Wrap the function call in a task, managing concurrency with the semaphore
            task = asyncio.create_task(
                wrapper(semaphore, function_name, deal_products[j], j)
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


async def wrapper(semaphore, function_name, *args, **kwargs):
    async with semaphore:
        # Call the synchronous get_data function in a separate thread
        result = await asyncio.to_thread(function_name, *args, **kwargs)
        return result


def search_row(row, counter, est_sales_min_threshold=10):
    print("counter: ", counter)
    print(row)

    # for row in deal_products:
    try:
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
        ) = row
        data_df = {}
        image_url_search = []
        asin_list = []
        asin_string = ""
        image_url = product_image
        rev_img_searcher = ReverseImageSearcher()
        res = rev_img_searcher.search(image_url)
        for search_item in res:
            if "amazon.com/" in str(search_item.page_url):
                raw_asin = urlparse(search_item.page_url).path.split("/")[-1]
                # Check if ASIN consists only of numbers
                if raw_asin.isdigit() or re.fullmatch(r"(s(,s)*)?", raw_asin.lower()):
                    continue  # Skip the rest of the loop for this iteration
                data_df["asin"] = raw_asin
                asin_list.append(data_df["asin"])
                data_df["sys_run_date"] = sys_run_date.strftime("%Y-%m-%d")
                data_df["product_id"] = product_id
                data_df["product_title"] = product_title
                data_df["product_url"] = product_url
                data_df["product_image"] = product_image
                data_df["product_price"] = product_price
                data_df["product_size"] = product_size
                data_df["product_color"] = product_color
                data_df["product_pack"] = product_pack
                data_df["product_attr"] = product_attr
                data_df["product_brand"] = product_brand
        if asin_list:
            asin_string = ", ".join(asin_list)
            driver = webdriver.Chrome(options=chrome_options)
            # Open Keepa
            driver.get("https://keepa.com/#!")

            wait = WebDriverWait(driver, 20)
            # Login process
            try:
                login_button = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//*[@id="panelUserRegisterLogin"]')
                    )
                )
                login_button.click()

                username_field = wait.until(
                    EC.visibility_of_element_located((By.ID, "username"))
                )
                username_field.send_keys(username)

                password_field = driver.find_element(By.ID, "password")
                password_field.send_keys(password)
                password_field.send_keys(Keys.RETURN)
                time.sleep(2)
                # This is a hypothetical CSS selector targeting the close button inside a specific parent
                # Adjust the selector based on the actual structure of your HTML
                close_button_selector = "#shareChartOverlay-close .fa-times-circle"

                try:
                    # Wait for the popup close button to be clickable
                    WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, close_button_selector)
                        )
                    )

                    # Find the close button using the CSS selector and click it
                    close_button = driver.find_element(
                        By.CSS_SELECTOR, close_button_selector
                    )
                    close_button.click()
                except TimeoutException:
                    print(
                        "The close button was not found or the popup did not appear within the timeout period."
                    )

                try:
                    otp = get_otp_from_email(
                        server, email_address, email_password, subject_filter
                    )
                    otp_field = driver.find_element(By.ID, "otp")
                    otp_field.send_keys(otp)
                    otp_field.send_keys(Keys.RETURN)
                    time.sleep(5)
                except NoSuchElementException:
                    print("OTP field not found. Check the HTML or the timing.")
                except Exception as e:
                    print(f"An unexpected error occurred: {e}")
            except:
                raise Exception("Error during login Keepa")

            # Navigate to the product_viewer
            try:
                data_button = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//*[@id="topMenu"]/li[4]/a/span')
                    )
                )
                data_button.click()
                time.sleep(2)
                productviewer_button = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//*[@id="subPanel"]/ul[3]/li[2]/a')
                    )
                )
                productviewer_button.click()

                ListAsin_field = wait.until(
                    EC.visibility_of_element_located((By.ID, "importInputAsin"))
                )
                ListAsin_field.send_keys(asin_string)

                Loadlist_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="importSubmit"]'))
                )
                Loadlist_button.click()
                time.sleep(2)
                # Logic to handle the presence of a specific popup
                try:
                    # Wait for a certain amount of time for the popup to appear
                    WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "popup3"))
                    )
                    raise Exception("Popup detected, skipping to next retailer")
                except TimeoutException:
                    try:
                        # Try to find the close button of the popup
                        close_button = driver.find_element(
                            By.ID, "shareChartOverlay-close4"
                        )
                        # If found, click it to close the popup
                        close_button.click()
                        print("Popup was found and closed.")
                    except NoSuchElementException:
                        # If the close button is not found, the popup is not displayed
                        print("Popup not found; continuing with the script.")
                    export_button = wait.until(
                        EC.element_to_be_clickable(
                            (
                                By.XPATH,
                                '//*[@id="grid-tools-viewer"]/div[1]/span[3]/span',
                            )
                        )
                    )
                    export_button.click()
                    time.sleep(2)
                    final_download_button = wait.until(
                        EC.element_to_be_clickable(
                            (By.XPATH, '//*[@id="exportSubmit"]')
                        )
                    )
                    final_download_button.click()
                    time.sleep(2)
                    driver.quit()

                def get_newest_file(directory):
                    files = glob.glob(os.path.join(directory, "*"))
                    if not files:  # Check if the files list is empty
                        return None
                    newest_file = max(files, key=os.path.getmtime)
                    return newest_file

                file_path = download_dir

                newest_file_path = get_newest_file(file_path)
                # # Get the current UTC time
                # current_utc_time = datetime.utcnow()

                # # Calculate the time difference for GMT+7
                # gmt7_offset = timedelta(hours=7)

                # # Get the current date and time in GMT+7
                # current_time_gmt7 = current_utc_time + gmt7_offset
                if newest_file_path:
                    data = pd.read_csv(newest_file_path)
                    data["sys_run_date"] = sys_run_date.strftime("%Y-%m-%d")
                    # Proceed with the database insertion
                else:
                    print("No files found in the specified directory.")

                def format_header(header):
                    # Convert to lowercase
                    header = header.lower()
                    # Replace spaces with underscores
                    header = header.replace(" ", "_")
                    # Remove Vietnamese characters by decomposing and keeping only ASCII
                    header = (
                        unicodedata.normalize("NFKD", header)
                        .encode("ASCII", "ignore")
                        .decode("ASCII")
                    )
                    return header

                # Extract the header row
                headers = [
                    "Locale",
                    "Image_URLs",
                    "Title",
                    "Sales_Rank_Current",
                    "Sales_Rank_90_Days_Avg",
                    "Sales_Rank_90_Days_Drop_Percent",
                    "Sales_Rank_Drops_Last_90_Days",
                    "Sales_Rank_Reference",
                    "Sales_Rank_Subcategory_Sales_Ranks",
                    "Bought_Past_Month",
                    "Reviews_Rating",
                    "Reviews_Review_Count",
                    "Reviews_Review_Count_90_Days_Drop_Percent",
                    "Ratings_Format_Specific",
                    "Review_Count_Format_Specific",
                    "Last_Price_Change",
                    "Buy_Box_Current_Price",
                    "Buy_Box_90_Days_Avg_Price",
                    "Buy_Box_90_Days_Drop_Percent",
                    "Buy_Box_Stock",
                    "Buy_Box_90_Days_OOS_Percent",
                    "Buy_Box_Seller",
                    "Buy_Box_Is_FBA",
                    "Buy_Box_Unqualified",
                    "Amazon_Current_Price",
                    "Amazon_90_Days_Avg_Price",
                    "Amazon_90_Days_Drop_Percent",
                    "Amazon_90_Days_OOS_Percent",
                    "New_Current_Price",
                    "New_90_Days_Avg_Price",
                    "New_90_Days_Drop_Percent",
                    "New_90_Days_OOS_Percent",
                    "New_3rd_Party_FBA_Current_Price",
                    "New_3rd_Party_FBA_90_Days_Avg_Price",
                    "New_3rd_Party_FBA_90_Days_Drop_Percent",
                    "FBA_PickAndPack_Fee",
                    "Referral_Fee_Percent",
                    "Referral_Fee_Current_Price",
                    "New_3rd_Party_FBM_Current_Price",
                    "New_3rd_Party_FBM_90_Days_Avg_Price",
                    "New_3rd_Party_FBM_90_Days_Drop_Percent",
                    "New_Prime_Exclusive_Current_Price",
                    "New_Prime_Exclusive_90_Days_Avg_Price",
                    "New_Prime_Exclusive_90_Days_Drop_Percent",
                    "Lightning_Deals_Current_Price",
                    "Lightning_Deals_Upcoming_Deal_Price",
                    "Used_Current_Price",
                    "Used_90_Days_Avg_Price",
                    "Used_90_Days_Drop_Percent",
                    "Used_90_Days_OOS_Percent",
                    "Used_Like_New_Current_Price",
                    "Used_Like_New_90_Days_Avg_Price",
                    "Used_Like_New_90_Days_Drop_Percent",
                    "Used_Very_Good_Current_Price",
                    "Used_Very_Good_90_Days_Avg_Price",
                    "Used_Very_Good_90_Days_Drop_Percent",
                    "Used_Good_Current_Price",
                    "Used_Good_90_Days_Avg_Price",
                    "Used_Good_90_Days_Drop_Percent",
                    "Used_Acceptable_Current_Price",
                    "Used_Acceptable_90_Days_Avg_Price",
                    "Used_Acceptable_90_Days_Drop_Percent",
                    "Warehouse_Deals_Current_Price",
                    "Warehouse_Deals_90_Days_Avg_Price",
                    "Warehouse_Deals_90_Days_Drop_Percent",
                    "List_Price_Current",
                    "List_Price_90_Days_Avg",
                    "List_Price_90_Days_Drop_Percent",
                    "Rental_Current_Price",
                    "Rental_90_Days_Avg_Price",
                    "Rental_90_Days_Drop_Percent",
                    "New_Offer_Count_Current",
                    "New_Offer_Count_90_Days_Avg",
                    "Count_of_Retrieved_Live_Offers_New_FBA",
                    "Count_of_Retrieved_Live_Offers_New_FBM",
                    "Used_Offer_Count_Current",
                    "Used_Offer_Count_90_Days_Avg",
                    "Tracking_Since",
                    "Listed_Since",
                    "Categories_Root",
                    "Categories_Sub",
                    "Categories_Tree",
                    "Categories_Launchpad",
                    "ASIN",
                    "Product_Codes_EAN",
                    "Product_Codes_UPC",
                    "Product_Codes_PartNumber",
                    "Parent_ASIN",
                    "Variation_ASINs",
                    "Freq_Bought_Together",
                    "Type",
                    "Manufacturer",
                    "Brand",
                    "Product_Group",
                    "Model",
                    "Variation_Attributes",
                    "Color",
                    "Size",
                    "Edition",
                    "Format",
                    "Author",
                    "Contributors",
                    "Binding",
                    "Number_of_Items",
                    "Number_of_Pages",
                    "Publication_Date",
                    "Release_Date",
                    "Languages",
                    "Package_Dimension_cm3",
                    "Package_Weight_g",
                    "Package_Quantity",
                    "Item_Dimension_cm3",
                    "Item_Weight_g",
                    "Hazardous_Materials",
                    "Adult_Product",
                    "Trade_In_Eligible",
                    "Prime_Eligible",
                    "Subscribe_and_Save",
                    "One_Time_Coupon_Absolute",
                    "One_Time_Coupon_Percentage",
                    "Subscribe_and_Save_Coupon_Percentage",
                    "sys_run_date",
                ]

                # Helper function to remove $ and convert to float
                def clean_currency(value):
                    try:
                        if pd.isna(value) or value == "-":
                            return 0
                        if isinstance(value, str):
                            return float(
                                value.replace("$", "").replace(",", "").strip()
                            )
                        return float(value)
                    except:
                        return 0.00

                # Helper function to remove % and convert to percentage
                def clean_percentage(value):
                    try:
                        if pd.isna(value) or value == "-":
                            return 0
                        if isinstance(value, str):
                            return float(value.replace("%", "").strip()) / 100
                        return float(value)
                    except:
                        return 0.00

                headers = [format_header(h) for h in headers]
                # data=data.to_dict(orient='records')
                # Convert column headers
                data.columns = headers

                # List of columns to apply the cleaning functions
                currency_columns = [
                    "Buy_Box_Current_Price",
                    "Buy_Box_90_Days_Avg_Price",
                    "Amazon_Current_Price",
                    "Amazon_90_Days_Avg_Price",
                    "New_Current_Price",
                    "New_90_Days_Avg_Price",
                    "New_3rd_Party_FBA_Current_Price",
                    "New_3rd_Party_FBA_90_Days_Avg_Price",
                    "FBA_PickAndPack_Fee",
                    "Referral_Fee_Current_Price",
                    "New_3rd_Party_FBM_Current_Price",
                    "New_3rd_Party_FBM_90_Days_Avg_Price",
                    "New_Prime_Exclusive_Current_Price",
                    "New_Prime_Exclusive_90_Days_Avg_Price",
                    "Lightning_Deals_Current_Price",
                    "Used_Current_Price",
                    "Used_90_Days_Avg_Price",
                    "Used_Like_New_Current_Price",
                    "Used_Like_New_90_Days_Avg_Price",
                    "Used_Very_Good_Current_Price",
                    "Used_Very_Good_90_Days_Avg_Price",
                    "Used_Good_Current_Price",
                    "Used_Good_90_Days_Avg_Price",
                    "Used_Acceptable_Current_Price",
                    "Used_Acceptable_90_Days_Avg_Price",
                    "Warehouse_Deals_Current_Price",
                    "Warehouse_Deals_90_Days_Avg_Price",
                    "List_Price_Current",
                    "List_Price_90_Days_Avg",
                    "Rental_Current_Price",
                    "Rental_90_Days_Avg_Price",
                    "One_Time_Coupon_Absolute",
                ]

                percentage_columns = [
                    "Sales_Rank_90_Days_Drop_Percent",
                    "Buy_Box_90_Days_Drop_Percent",
                    "Buy_Box_90_Days_OOS_Percent",
                    "Reviews_Review_Count_90_Days_Drop_Percent",
                    "Amazon_90_Days_Drop_Percent",
                    "Amazon_90_Days_OOS_Percent",
                    "New_90_Days_Drop_Percent",
                    "New_90_Days_OOS_Percent",
                    "New_3rd_Party_FBA_90_Days_Drop_Percent",
                    "New_3rd_Party_FBM_90_Days_Drop_Percent",
                    "New_Prime_Exclusive_90_Days_Drop_Percent",
                    "Used_90_Days_Drop_Percent",
                    "Used_Like_New_90_Days_Drop_Percent",
                    "Used_Very_Good_90_Days_Drop_Percent",
                    "Used_90_Days_OOS_Percent",
                    "Used_Good_90_Days_Drop_Percent",
                    "Used_Acceptable_90_Days_Drop_Percent",
                    "Warehouse_Deals_90_Days_Drop_Percent",
                    "List_Price_90_Days_Drop_Percent",
                    "Rental_90_Days_Drop_Percent",
                    "Reviews_Review_Count_90_Days_Drop_Percent",
                    "Referral_Fee_Percent",
                    "One_Time_Coupon_Percentage",
                    "Subscribe_and_Save_Coupon_Percentage",
                ]

                integer_columns = [
                    "Sales_Rank_Current",
                    "Sales_Rank_90_Days_Avg",
                    "Sales_Rank_Drops_Last_90_Days",
                    "Bought_Past_Month",
                    "Reviews_Review_Count",
                    "Ratings_Format_Specific",
                    "Review_Count_Format_Specific",
                    "Buy_Box_Stock",
                    "New_Offer_Count_Current",
                    "New_Offer_Count_90_Days_Avg",
                    "Count_of_Retrieved_Live_Offers_New_FBA",
                    "Count_of_Retrieved_Live_Offers_New_FBM",
                    "Used_Offer_Count_Current",
                    "Used_Offer_Count_90_Days_Avg",
                    "Number_of_Items",
                    "Number_of_Pages",
                    "Package_Dimension_cm3",
                    "Package_Weight_g",
                    "Package_Quantity",
                    "Item_Dimension_cm3",
                    "Item_Weight_g",
                ]

                string_columns = [
                    "Product_Codes_EAN",
                    "Product_Codes_UPC",
                ]

                # Apply cleaning functions to the specified columns
                for col in currency_columns:
                    data[format_header(col)] = data[format_header(col)].apply(
                        clean_currency
                    )

                for col in percentage_columns:
                    data[format_header(col)] = data[format_header(col)].apply(
                        clean_percentage
                    )

                for col in integer_columns:
                    data[format_header(col)] = (
                        data[format_header(col)].astype(float).fillna(0).astype(int)
                    )
                # for col in string_columns:
                #     data[format_header(col)] = (
                #         data[format_header(col)].apply(lambda x: "{:.0f}".format(x))
                #     )

                for index, row in data.iterrows():
                    try:
                        # Convert row to dictionary and handle NaN values
                        row_dict = row.replace({np.nan: None}).to_dict()

                        # Generate MD5 hash as the primary key
                        asin = row_dict.get("asin")
                        sys_run_date = row_dict.get("sys_run_date")
                        if asin and sys_run_date:
                            md5_hash = str(asin) + str(sys_run_date)
                            row_dict["pk_column_name"] = md5_hash
                            data_df["asin"] = asin
                            data_df["amazon_title"] = row_dict.get("title")
                            data_df["amazon_url"] = "https://www.amazon.com/dp/" + asin
                            data_df["amazon_image"] = row_dict.get("image_urls")
                            data_df["amazon_category"] = row_dict.get("categories_root")
                            data_df["brand"] = row_dict.get("brand")
                            data_df["amazon_size"] = row_dict.get("size")
                            data_df["amazon_color"] = row_dict.get("color")
                            data_df["amazon_pack"] = row_dict.get("number_of_items")
                            data_df["buy_box_current_price"] = row_dict.get(
                                "buy_box_current_price"
                            )
                            data_df["buy_box_90_days_avg_price"] = row_dict.get(
                                "buy_box_90_days_avg_price"
                            )
                            for key, value in data_df.items():
                                if isinstance(value, decimal.Decimal):
                                    data_df[key] = float(value)
                            try:
                                # Insert the row into the database
                                response2 = (
                                    supabase.table("product_seller_amazon_mapping")
                                    .insert(data_df)
                                    .execute()
                                )
                                if (
                                    hasattr(response2, "error")
                                    and response2.error is not None
                                ):
                                    print(f"Error inserting row: {response2.error}")

                                print(
                                    f"Row inserted at index product_seller_amazon_mapping"
                                )
                                response = (
                                    supabase.table("product_keepa")
                                    .insert(row_dict)
                                    .execute()
                                )
                                if (
                                    hasattr(response, "error")
                                    and response.error is not None
                                ):
                                    raise Exception(
                                        f"Error inserting row: {response.error}"
                                    )
                                print(f"Row inserted at index {index}")
                            except:
                                response = (
                                    supabase.table("product_keepa")
                                    .insert(row_dict)
                                    .execute()
                                )
                                if (
                                    hasattr(response, "error")
                                    and response.error is not None
                                ):
                                    print(f"Error inserting row: {response.error}")
                                print(f"Row inserted at index {index}")

                    except Exception as e:
                        print(f"Error with row at index {index}: {e}")
                        continue
            except Exception as e:
                print(e)
                driver.quit()
                # continue
    except Exception as e:
        print(f"Error Image: {image_url}: {e} ")
        # continue


def get_otp_from_email(server, email_address, email_password, subject_filter):
    mail = imaplib.IMAP4_SSL(server)
    mail.login(email_address, email_password)
    mail.select("inbox")

    status, data = mail.search(None, '(SUBJECT "{}")'.format(subject_filter))
    mail_ids = data[0].split()

    latest_email_id = mail_ids[-1]
    status, data = mail.fetch(latest_email_id, "(RFC822)")

    raw_email = data[0][1].decode("utf-8")
    email_message = email.message_from_bytes(data[0][1])

    otp_pattern = re.compile(r"\b\d{6}\b")

    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            if "text/plain" in content_type or "text/html" in content_type:
                email_content = part.get_payload(decode=True).decode()
                match = otp_pattern.search(email_content)
                if match:
                    return match.group(0)
    else:
        email_content = email_message.get_payload(decode=True).decode()
        match = otp_pattern.search(email_content)
        if match:
            return match.group(0)

    return None


SUPABASE_URL = "https://sxoqzllwkjfluhskqlfl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN4b3F6bGx3a2pmbHVoc2txbGZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MDIyODE1MTcsImV4cCI6MjAxNzg1NzUxN30.FInynnvuqN8JeonrHa9pTXuQXMp9tE4LO0g5gj0adYE"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Replace these with your Keepa username and password
username = "utytra1"
password = "SgN2N.yvY@iR2kg"

# Gmail App Password
server = "imap.gmail.com"
email_address = "uty.tra@thebargainvillage.com"
email_password = "kwuh xdki tstu vyct"
subject_filter = "Keepa.com Account Security Alert and One-Time Login Code"

# display = Display(visible=0, size=(800, 800))
# display.start()

# chromedriver_autoinstaller.install()  # Check if the current version of chromedriver exists

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
    ]
    chrome_options.add_experimental_option("prefs", prefs)
    for option in options:
        chrome_options.add_argument(option)


deal_products = get_deal_products()
print("running")
print("len deal products: ", len(deal_products))

limit = 1
# begin = 2
# end = 4
begin = 0
end = len(deal_products)

# Adjust the call to run_parallel to include refresh_rate
data = asyncio.run(
    run_parallel(
        limit,  # Adjust as needed
        function_name=search_row,
        begin=begin,
        end=end,
        refresh_rate=2,  # Set your desired refresh rate
    )
)
print("done")
