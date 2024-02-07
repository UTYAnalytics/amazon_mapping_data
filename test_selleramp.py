# import tempfile
# from selenium import webdriver
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# import os
# import time
# import pandas as pd
# import psycopg2
# import glob
# from supabase import create_client, Client
# import re
# import unicodedata
# from selenium.common.exceptions import TimeoutException
# import imaplib
# import email
# import re
# import chromedriver_autoinstaller
# from selenium.common.exceptions import NoSuchElementException
# from datetime import datetime, timedelta
# import numpy as np
# from pyvirtualdisplay import Display
# from urllib.parse import urlparse
# import requests
# import json

# with tempfile.TemporaryDirectory() as download_dir:
#     # and if it doesn't exist, download it automatically,
#     # then add chromedriver to path
#     chrome_options = webdriver.ChromeOptions()
#     prefs = {
#         "download.default_directory": download_dir,
#         "download.prompt_for_download": False,
#         "download.directory_upgrade": True,
#         "safebrowsing.enabled": True,
#     }
#     options = [
#         # Define window size here
#         "--window-size=1200,1200",
#         "--ignore-certificate-errors",
#     ]
#     chrome_options.add_experimental_option("prefs", prefs)
#     for option in options:
#         chrome_options.add_argument(option)


# def get_selleramp(asin, cost_price):
#     username_selleramp = "greatwallpurchasingdept@gmail.com"
#     password_selleramp = "H@h@h@365!"
#     driver = webdriver.Chrome(options=chrome_options)
#     # Open SellerAmp
#     driver.get("https://sas.selleramp.com/site/login")
#     wait = WebDriverWait(driver, 20)
#     # Login process
#     try:
#         username_field = wait.until(
#             EC.visibility_of_element_located((By.ID, "loginform-email"))
#         )
#         username_field.send_keys(username_selleramp)

#         password_field = driver.find_element(By.ID, "loginform-password")
#         password_field.send_keys(password_selleramp)
#         password_field.send_keys(Keys.RETURN)
#         time.sleep(8)
#     except:
#         raise Exception("Error during login SellerAmp")

#     try:
#         asin_field = wait.until(
#             EC.visibility_of_element_located((By.ID, "saslookup-search_term"))
#         )
#         asin_field.send_keys(asin)
#         search_button = wait.until(
#             EC.element_to_be_clickable(
#                 (By.XPATH, '//*[@id="sas-calc-form"]/div/div/div/div/div/div[2]/button')
#             )
#         )
#         search_button.click()
#         time.sleep(20)

#         # Execute JavaScript to clear the input field
#         driver.execute_script("document.getElementById('qi_cost').value = ''")
#         costprice_input = wait.until(
#             EC.visibility_of_element_located((By.ID, "qi_cost"))
#         )
#         # costprice_input.clear()
#         costprice_input.send_keys(cost_price)
#         time.sleep(2)

#     except Exception as e:
#         print(e)
#         driver.quit()


# get_selleramp("B010DNGITK", "18")


import re


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


# Examples of usage:
texts = [">30.78 $", "$30.68", "below 60", ".80.8", "%70.86"]
for text in texts:
    print(f"Original text: '{text}' extracted number: {extract_number(text)}")
