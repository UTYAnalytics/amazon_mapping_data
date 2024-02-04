import requests
import json

# Existing parameters
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
    "brand": ["reebok"],
    "itemWeight_gte": 0,
    "itemWeight_lte": 2500,
    "productType": ["0"],
    "sort": [["current_SALES", "asc"]],
    "lastOffersUpdate_gte": 6882569,
    "lastRatingUpdate_gte": 6757289,
    "perPage": 5000,
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

    # Specify the file path where you want to save the JSON file
    json_file_path = "keepa_data.json"

    # Write the data to the JSON file
    with open(json_file_path, "w") as json_file:
        json.dump(data, json_file, indent=2)

    print(f"Data exported to {json_file_path}")
else:
    print(f"Error: Failed to fetch data. Status code: {response.status_code}")
    print(response.text)  # Print the error response for debugging


# from urllib.parse import urlparse, parse_qs

# api_url = "https://api.keepa.com/query?key=4vveri0fi2h7tr6trfuphq19j5ilqj23hlu0cqviofk9r35i8me73pq4iq3ulquo&domain=1&selection=%7B%22deltaPercent90_SALES_gte%22%3A50%2C%22current_COUNT_REVIEWS_gte%22%3A3%2C%22current_BUY_BOX_SHIPPING_gte%22%3A3000%2C%22current_AMAZON_gte%22%3A-1%2C%22current_AMAZON_lte%22%3A-1%2C%22current_COUNT_NEW_gte%22%3A3%2C%22offerCountFBA_gte%22%3A0%2C%22packageWeight_gte%22%3A0%2C%22packageWeight_lte%22%3A2500%2C%22buyBoxIsFBA%22%3Afalse%2C%22buyBoxUsedIsFBA%22%3Afalse%2C%22brand%22%3A%5B%22reebok%22%5D%2C%22itemWeight_gte%22%3A0%2C%22itemWeight_lte%22%3A2500%2C%22productType%22%3A%5B%220%22%5D%2C%22sort%22%3A%5B%5B%22current_SALES%22%2C%22asc%22%5D%5D%2C%22lastOffersUpdate_gte%22%3A6882569%2C%22lastRatingUpdate_gte%22%3A6757289%2C%22perPage%22%3A5000%2C%22page%22%3A0%7D"

# # Parse the URL
# parsed_url = urlparse(api_url)

# # Extract query parameters from the URL
# query_params = parse_qs(parsed_url.query)

# # Print the individual parameters
# for key, value in query_params.items():
#     print(f"{key}: {value[0]}")
