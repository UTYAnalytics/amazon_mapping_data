import psycopg2
from supabase import create_client, Client
import numpy as np
from urllib.parse import urlparse
import ssl
from urllib.request import urlopen
from skimage import io
import numpy as np
import cv2 as cv
import datetime
import decimal


SUPABASE_URL = "https://sxoqzllwkjfluhskqlfl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN4b3F6bGx3a2pmbHVoc2txbGZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MDIyODE1MTcsImV4cCI6MjAxNzg1NzUxN30.FInynnvuqN8JeonrHa9pTXuQXMp9tE4LO0g5gj0adYE"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


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


def load_data_mapping_amazon_seller():

    query2 = """
    select  
        a.sys_run_date,
        a.product_id,
        a.product_title,
        a.product_url_href product_url,
        a.product_image_1_src product_image,
        a.product_price,
        a.product_variants->>'size' product_size,
        a.product_variants->>'color' product_color,
        b.title amazon_title,
        concat('https://www.amazon.com/dp/',b.asin) amazon_url,
        b.image_urls amazon_image,
        b.categories_root amazon_category,
        b.brand,
        b.size amazon_size,
        b.color amazon_color,
        b.asin,
        b.number_of_items amazon_pack,
        b.buy_box_current_price,
        b.buy_box_90_days_avg_price
        from seller_product_data a 
        inner join product_keepa b on a.sys_run_date=b.sys_run_date and lower(a.product_brand)=lower(b.brand) and lower(a.product_variants->>'color')=lower(b.color)
        where a.product_price<=50
        and a.sys_run_date=(select max(sys_run_date) from seller_product_data);
    """
    cursor.execute(query2)
    # Fetch all the rows as a list
    result2 = cursor.fetchall()
    return result2


# Disable SSL certificate verification
ssl._create_default_https_context = ssl._create_unverified_context


def matching(path1, path2):
    img1 = io.imread(path1)
    img2 = io.imread(path2)
    h, w, s = img1.shape
    # Initiate SIFT detector
    sift = cv.SIFT_create()
    kp1, des1 = sift.detectAndCompute(img1, None)
    kp2, des2 = sift.detectAndCompute(img2, None)

    # Convert descriptors to the appropriate type if not None
    if des1 is not None:
        des1 = np.float32(des1)

    if des2 is not None:
        des2 = np.float32(des2)

    # Check if both descriptors are not None and have the same type
    if des1 is not None and des2 is not None and des1.dtype == des2.dtype:
        # BFMatcher with default params
        bf = cv.BFMatcher()
        matches = bf.knnMatch(des1, des2, k=2)

        # Apply ratio test
        good = []
        for m, n in matches:
            if m.distance < 0.6 * n.distance:
                good.append(m)

        MIN_MATCH_COUNT = 25
        if len(good) > MIN_MATCH_COUNT:
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            M, mask = cv.findHomography(src_pts, dst_pts, cv.RANSAC, 7.0)
            matchesMask = mask.ravel().tolist()
        else:
            matchesMask = None
    else:
        matchesMask = None
        good = []  # Initialize 'good' list here

    return matchesMask, good


data_mapping = load_data_mapping_amazon_seller()

for row in data_mapping:
    try:
        # Convert the tuple to a dictionary
        row_dict = dict(zip([column[0] for column in cursor.description], row))
        # Convert Decimal values to float
        for key, value in row_dict.items():
            if isinstance(value, decimal.Decimal):
                row_dict[key] = float(value)
        product_image = row_dict["product_image"]
        amazon_image = row_dict["amazon_image"]
        matchesMask, good = matching(product_image, amazon_image)

        if matchesMask:
            if len(matchesMask) / len(good) > 0.9:
                row_dict["image_matching"] = "MATCH"
            else:
                row_dict["image_matching"] = "NEARLY MATCH"

            # Generate MD5 hash as the primary key
            asin = row_dict["asin"]
            sys_run_date = row_dict["sys_run_date"]
            if isinstance(sys_run_date, datetime.date):
                sys_run_date_str = sys_run_date.strftime("%Y-%m-%d")
            else:
                sys_run_date_str = sys_run_date
            row_dict["sys_run_date"] = sys_run_date_str
            if asin and sys_run_date_str:
                response = (
                    supabase.table("product_seller_amazon_mapping")
                    .insert(row_dict)
                    .execute()
                )

                if hasattr(response, "error") and response.error is not None:
                    raise Exception(f"Error inserting row: {response.error}")

                print(f"Row inserted at index product_seller_amazon_mapping")

    except Exception as e:
        print(f"Error with row at index {e} product_seller_amazon_mapping")
        continue
