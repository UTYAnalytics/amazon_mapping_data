# Remember to close the browser
import tempfile
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import pandas as pd
import psycopg2
import glob
from supabase import create_client, Client
import re
import unicodedata
from selenium.common.exceptions import TimeoutException
import imaplib
import email
import re
import chromedriver_autoinstaller
from selenium.common.exceptions import NoSuchElementException
from datetime import datetime, timedelta
import numpy as np
from pyvirtualdisplay import Display
from urllib.parse import urlparse
import requests
import json
from skimage import io
import numpy as np
import cv2 as cv


display = Display(visible=0, size=(800, 600))
display.start()

chromedriver_autoinstaller.install()

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


# Your connection string
connection_string = "postgres://postgres.sxoqzllwkjfluhskqlfl:5giE*5Y5Uexi3P2@aws-0-us-west-1.pooler.supabase.com:6543/postgres"

# Parse the connection string
result = urlparse(connection_string)
user = result.username
passdata = result.password
database = result.path[1:]  # remove the leading '/'
hostname = result.hostname
port = result.port

conn = psycopg2.connect(
    dbname=database, user=user, password=passdata, host=hostname, port=port
)
# Create a cursor
cursor = conn.cursor()

# Execute the SQL query to retrieve distinct brand from the "best_seller_keepa" table
query = """
select distinct a.product_brand from seller_product_data a
left join (select distinct sys_run_date, brand from product_keepa) b on lower(a.product_brand)=lower(b.brand) and a.sys_run_date=b.sys_run_date
where a.sys_run_date IN (
        SELECT 
            MAX(sys_run_date) from seller_product_data
    )
AND a.product_brand is not null
and lower(a.product_brand) not in (select lower(brand) from "IP_Brand")
AND b.sys_run_date is null;
"""

cursor.execute(query)


# Fetch all the rows as a list
result = cursor.fetchall()

# Extract retailer_ids from the result
brand_list = [row[0] for row in result]

# Split the brand_list into subsets of 10 brands each
subset_size = 10
brand_subsets = [
    brand_list[i : i + subset_size] for i in range(0, len(brand_list), subset_size)
]


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


def get_asin_list(brands_list):
    # Existing parameters
    brand_list_lower = [brand.lower() for brand in brands_list]
    key = "4vveri0fi2h7tr6trfuphq19j5ilqj23hlu0cqviofk9r35i8me73pq4iq3ulquo"
    domain = 1
    selection = {
        "deltaPercent90_SALES_gte": 50,
        "current_COUNT_REVIEWS_gte": 3,
        "current_BUY_BOX_SHIPPING_gte": 3000,
        "current_AMAZON_gte": -1,
        "current_AMAZON_lte": -1,
        "current_COUNT_NEW_gte": 3,
        "offerCountFBA_gte": 0,
        "packageWeight_gte": 0,
        "packageWeight_lte": 2500,
        "buyBoxIsFBA": False,
        "buyBoxUsedIsFBA": False,
        "brand": brand_list_lower,
        "itemWeight_gte": 0,
        "itemWeight_lte": 2500,
        "productType": ["0"],
        "sort": [["current_SALES", "asc"]],
        "lastOffersUpdate_gte": 6882569,
        "lastRatingUpdate_gte": 6757289,
        "perPage": 10000,
        "page": 0,
    }

    # Construct new URL
    api_url = f"https://api.keepa.com/query?key={key}&domain={domain}&selection={json.dumps(selection)}"

    # Make a GET request to the API URL
    response = requests.get(api_url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        # Extract "asinList" from the response
        asin_list = data.get("asinList", [])
        if asin_list:
            # Convert the list of ASINs to a comma-separated string
            asin_string = ", ".join(asin_list)
            return asin_string
        else:
            raise Exception("ASIN list is empty")
    else:
        print(f"Error: Failed to fetch data. Status code: {response.status_code}")
        print(response.text)  # Print the error response for debugging
        return None


def get_selleramp(asin):
    username_selleramp = "greatwallpurchasingdept@gmail.com"
    password_selleramp = "H@h@h@365!"
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
                (By.XPATH, '//*[@id="sas-calc-form"]/div/div/div/div/div/div[2]/button')
            )
        )
        search_button.click()
        time.sleep(20)
    except Exception as e:
        print(e)
        driver.quit()


for brand in brand_subsets:

    # (
    #         sys_run_date,
    #         product_brand,
    #     ) = brand
    # Initialize the Chrome driver with the options
    driver = webdriver.Chrome(options=chrome_options)

    # Open Keepa
    driver.get("https://keepa.com/#!")

    wait = WebDriverWait(driver, 20)
    # Login process
    try:
        login_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="panelUserRegisterLogin"]'))
        )
        login_button.click()

        username_field = wait.until(
            EC.visibility_of_element_located((By.ID, "username"))
        )
        username_field.send_keys(username)

        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys(password)
        password_field.send_keys(Keys.RETURN)
        time.sleep(8)
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
            EC.element_to_be_clickable((By.XPATH, '//*[@id="topMenu"]/li[4]/a/span'))
        )
        data_button.click()
        time.sleep(2)
        productviewer_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="subPanel"]/ul[3]/li[2]/a'))
        )
        productviewer_button.click()

        ListAsin_field = wait.until(
            EC.visibility_of_element_located((By.ID, "importInputAsin"))
        )
        ListAsin_field.send_keys(get_asin_list(brand))

        Loadlist_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="importSubmit"]'))
        )
        Loadlist_button.click()
        time.sleep(5)
        # Logic to handle the presence of a specific popup
        try:
            # Wait for a certain amount of time for the popup to appear
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "popup3"))
            )
            raise Exception("Popup detected, skipping to next retailer")
        except TimeoutException:
            export_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="grid-tools-viewer"]/div[1]/span[3]/span')
                )
            )
            export_button.click()
            time.sleep(5)
            final_download_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="exportSubmit"]'))
            )
            final_download_button.click()
            time.sleep(5)
            driver.quit()

        def get_newest_file(directory):
            files = glob.glob(os.path.join(directory, "*"))
            if not files:  # Check if the files list is empty
                return None
            newest_file = max(files, key=os.path.getmtime)
            return newest_file

        file_path = download_dir

        newest_file_path = get_newest_file(file_path)
        # Get the current UTC time
        current_utc_time = datetime.utcnow()

        # Calculate the time difference for GMT+7
        gmt7_offset = timedelta(hours=7)

        # Get the current date and time in GMT+7
        current_time_gmt7 = current_utc_time + gmt7_offset
        if newest_file_path:
            data = pd.read_csv(newest_file_path)
            data["sys_run_date"] = current_time_gmt7.strftime("%Y-%m-%d %H:%M:%S")
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
                    return float(value.replace("$", "").replace(",", "").strip())
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
            data[format_header(col)] = data[format_header(col)].apply(clean_currency)

        for col in percentage_columns:
            data[format_header(col)] = data[format_header(col)].apply(clean_percentage)

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
                sys_run_date = datetime.strptime(
                    row_dict.get("sys_run_date"), "%Y-%m-%d %H:%M:%S"
                ).date()
                if asin and sys_run_date:
                    md5_hash = str(asin) + str(sys_run_date)
                    row_dict["pk_column_name"] = md5_hash
                    # Insert the row into the database
                    response = (
                        supabase.table("product_keepa").insert(row_dict).execute()
                    )
                    if hasattr(response, "error") and response.error is not None:
                        raise Exception(f"Error inserting row: {response.error}")
                    print(f"Row inserted at index {index}")
            except Exception as e:
                print(f"Error with row at index {index}: {e}")
                continue

    except Exception as e:
        print(e)
        driver.quit()
        continue
