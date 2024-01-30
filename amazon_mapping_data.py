from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException
from selenium import webdriver
from apify_client import ApifyClient
from google_img_source_search import ReverseImageSearcher
import json
import psycopg2
from supabase import create_client, Client
from datetime import datetime, timezone, timedelta
from fuzzywuzzy import fuzz
from decimal import Decimal
from json import JSONEncoder
import os
import asyncio
import pandas as pd
import numpy as np
import time
# import chromedriver_autoinstaller


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
                concat(a.product_title,' size ',product_variants->>'size',' color ',product_variants->>'color') as product_name,
                a.product_image_1_src product_image_src,
                a.product_price,
                a.product_original_price,
                a.product_brand,
                a.product_url_href 
                from seller_product_data a 
                left join amazon_mapping_data b on a.product_id=b.product_id and a.sys_run_date=b.sys_run_date
                where b.product_id is null and lower(a.product_brand) not in (select lower(brand) from "IP_Brand")
                order by sys_run_date desc;
    """
    cursor.execute(query)
    # Fetch all the rows as a list
    deal_products = cursor.fetchall()
    return deal_products


async def run_parallel(limit, function_name, begin, end):
    semaphore = asyncio.Semaphore(value=limit)

    tasks = []
    print(f"start path: {begin}: {end}")
    for j in range(begin, end):
        task = asyncio.create_task(
            wrapper(semaphore, function_name, deal_products[j], j)
        )
        tasks.append(task)

    # Run tasks
    await asyncio.gather(*tasks)

    # results = await asyncio.gather(*tasks)
    # data = []
    # [data.extend(json_list) for json_list in results]
    # return data


async def wrapper(semaphore, function_name, *args, **kwargs):
    async with semaphore:
        # Call the synchronous get_data function in a separate thread
        result = await asyncio.to_thread(function_name, *args, **kwargs)
        return result


def search_row(row, counter, est_sales_min_threshold=10):
    print("counter: ", counter)
    print(row)
    for row in deal_products:
        (
            sys_run_date,
            product_id,
            product_name,
            product_image_src,
            product_price,
            product_original_price,
            product_brand,
            product_url_href,
        ) = row
        image_url_search = []
        image_url = product_image_src
        rev_img_searcher = ReverseImageSearcher()
        res = rev_img_searcher.search(image_url)

        for search_item in res:
            if "amazon.com/" in str(search_item.page_url):
                image_url_search.append(search_item.page_url)

        # Prepare the Actor input
        run_input = {
            "amazonTld": ".com",
            "customMapFunction": "(object) => { return {...object} }",
            "endPage": 1,
            "extendOutputFunction": "($) => { return {} }",
            "getReviews": False,
            "maxItems": 60,
            "proxy": {"useApifyProxy": True},
            "reviewsEndPage": 1,
            "startUrls": image_url_search,
            "search": product_name,
        }

        # Run the Actor and wait for it to finish
        run = client.actor("yoFyGfllOo00TGKLl").call(run_input=run_input)

        data = []
        # Fetch and print Actor results from the run's dataset (if there are any)
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            item["sys_run_date"] = sys_run_date.strftime("%Y-%m-%d")
            item["product_id"] = product_id
            item["product_name"] = product_name
            item["product_image_src"] = product_image_src
            item["product_price"] = product_price
            item["product_original_price"] = product_original_price
            item["product_brand"] = product_brand
            item["product_url"] = product_url_href
            item["score_matching"] = fuzz.ratio(
                product_name, item["title"]
            )  # Use fuzz.ratio to get a similarity score (percentage)

            cleaned_item = clean_columns(item)
            if cleaned_item is not None:
                est_sales = get_estimated_sales(cleaned_item["asin"])
                cleaned_item["est_sales"] = est_sales
                insert_new_data("amazon_mapping_data", [cleaned_item])
                # data.append(cleaned_item)
    # return data


def clean_columns(json_object) -> json:
    df = pd.json_normalize(json_object, max_level=0)
    # df.to_csv("test.csv", index=False)
    # print(df.columns.tolist())
    cols = [
        "type",
        "title",
        "url",
        "inStock",
        "maxQuantitySelection",
        "brand",
        "shippingText",
        "stars",
        "reviewsCount",
        "categories",
        "images",
        "specs",
        "delivery",
        "sys_run_date",
        "product_id",
        "product_name",
        "product_image_src",
        "product_price",
        "product_original_price",
        "product_brand",
        "score_matching",
        # "image_matching",
        "price",
        "listPrice",
        "shippingPrice",
        "seller",
        "product_url",
    ]
    missing_cols = set(cols) - set(df.columns.tolist())
    for col in missing_cols:
        df[col] = None

    df = df[cols]

    col = "specs"
    df["temp1"] = df[col].apply(
        lambda items: sum(
            [
                1 if (isinstance(item, dict) and item.get("key") == "ASIN") else 0
                for item in items
            ]
        )
    )
    df = df[df.temp1 >= 1]
    # Drop the 'temp1' column
    df = df.drop(columns=["temp1"])
    if len(df) == 0:
        return None

    df["images"] = df["images"].apply(lambda list1: list1[0] if len(list1) else None)
    df = df[~pd.isnull(df["images"])]

    df["specs"] = df["specs"].apply(
        lambda specs_list: dict(
            [(json_item["key"], json_item["value"]) for json_item in specs_list]
        )
    )
    df["asin"] = df["specs"].apply(lambda specs_json: specs_json["ASIN"])

    df.replace(np.nan, None, inplace=True)
    #     load_data(raw_data, "raw_data", counter)
    #     print(f"Row {counter} is done")

    if len(df) == 0:
        return None

    return df.to_dict("records")[0]


def get_estimated_sales(asin):
    # Specify the path to your webdriver executable (e.g., chromedriver.exe)
    print("get est_sales")
    chrome_driver_path = '/usr/local/bin/chromedriver'
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # print(chrome_options)
    # print(dir(chrome_options))
    driver = webdriver.Chrome(executable_path=chrome_driver_path,options=chrome_options)
    try:
        # Navigate to the ProfitGuru website
        driver.get("https://www.profitguru.com/calculator/sales")
        # Input ASIN value
        wait = WebDriverWait(driver, 100)
        asin_input = wait.until(
            EC.presence_of_element_located((By.ID, "calc_asin_input"))
        )
        asin_input.send_keys(asin)
        asin_input.send_keys(Keys.ENTER)
        time.sleep(8)
        # Get text from the element
        wait = WebDriverWait(driver, 10)
        estimated_sales_element = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "tr:nth-of-type(6) .pr-2 div")
            )
        )
        estimated_sales_text = estimated_sales_element.text.strip()
        # Check if the text is a number
        try:
            estimated_sales = float(estimated_sales_text.replace(",", ""))
        except ValueError:
            estimated_sales = 0
        return estimated_sales

    finally:
        # Close the browser window
        driver.quit()


# def load_data(json_data, folder, counter):
#     with open(os.path.join(folder, f"{counter}.json"), "w", encoding="utf-8") as file:
#         json.dump(json_data, file, ensure_ascii=False, cls=DecimalEncoder)


def insert_new_data(table, data: json):
    data = format_data(data)
    try:
        print("len data: ", len(data))
        size = 10000
        for i in range(0, len(data), size):
            json_list = (
                data.loc[i : i + size - 1,]
                .copy()
                .replace({np.nan: None})
                .to_dict(orient="records")
            )

            # json_list = data.to_dict(orient="records")
            # Insert the rows into the database using executemany
            response = supabase.table(table).insert(json_list).execute()

            if hasattr(response, "error") and response.error is not None:
                print(f"Error inserting rows: {response.error}")

        print(f"Row inserted successfully")

    except Exception as e:
        print(f"Error with row: {e}")
        # Optionally, break or continue based on your preference


def format_data(json_list):
    # Proceed with the database insertion
    data = pd.json_normalize(json_list, max_level=0)

    data["shippingprice_value"] = data["shippingPrice"].apply(
        lambda value: value["value"]
    )
    data["shippingprice_currency"] = data["shippingPrice"].apply(
        lambda value: value["currency"]
    )

    data["listprice_value"] = data["listPrice"].apply(lambda value: value["value"])
    data["listprice_currency"] = data["listPrice"].apply(
        lambda value: value["currency"]
    )

    data["price_value"] = data["price"].apply(lambda value: value["value"])
    data["price_currency"] = data["price"].apply(lambda value: value["currency"])

    data["seller_name"] = data["seller"].apply(lambda value: value["name"])
    data["seller_id"] = data["seller"].apply(lambda value: value["id"])

    # data["reviewscount"] = data["reviewsCount"]
    data.columns = [col.lower() for col in data.columns.tolist()]

    table_cols = [
        "type",
        "title",
        "url",
        "instock",
        "maxquantityselection",
        "brand",
        "shippingtext",
        "stars",
        "reviewscount",
        "categories",
        "images",
        "specs",
        "delivery",
        "sys_run_date",
        "product_id",
        "product_name",
        "product_image_src",
        "product_price",
        "product_original_price",
        "product_brand",
        "score_matching",
        "price_value",
        "price_currency",
        "listprice_value",
        "listprice_currency",
        "shippingprice_value",
        "shippingprice_currency",
        "seller_name",
        "seller_id",
        "est_sales",
        "asin",
        "product_url",
    ]

    # real_cols = df.columns.tolist()

    # extra_columns = set(real_cols) - set(table_cols)
    # missing_columns = set(table_cols) - set(real_cols)
    # print("extra_columns = ", extra_columns)
    # print("    missing_columns = ", missing_columns)
    numeric_cols = [
        "est_sales",
        "listprice_value",
        "price_value",
        "product_original_price",
        "product_price",
        "reviewscount",
        "shippingprice_value",
        "stars",
    ]
    for col in numeric_cols:
        data[col] = data[col].astype(float).fillna(0)

    integer_cols = [
        "score_matching",
    ]
    for col in integer_cols:
        data[col] = data[col].astype(float).fillna(0).astype(int)

    data = data[table_cols]

    return data


# chromedriver_autoinstaller.install()

SUPABASE_URL = "https://sxoqzllwkjfluhskqlfl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN4b3F6bGx3a2pmbHVoc2txbGZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MDIyODE1MTcsImV4cCI6MjAxNzg1NzUxN30.FInynnvuqN8JeonrHa9pTXuQXMp9tE4LO0g5gj0adYE"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize the ApifyClient with your API token
client = ApifyClient("apify_api_L0SHnudrftNCT9xclBaUVBKTddBUB60WZ66u")

deal_products = get_deal_products()
print("running")
print("len deal products: ", len(deal_products))

limit = 4
# begin = 2
# end = 4
begin = 0
end = len(deal_products)

data = asyncio.run(
    run_parallel(
        limit=limit,
        function_name=search_row,
        begin=begin,
        end=end,
    )
)

# load_data(data, "", "test")
# insert_new_data(table="amazon_mapping_data", data=data)

print("done")
