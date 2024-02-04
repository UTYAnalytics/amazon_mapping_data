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
    "brand": ['excmark', 'amolife', 'koorui', 'intex', 'eastsport', 'hanes', 'cherokee', 'jienlioq', 'x-bull', 'time and tru'],
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

    # Specify the file path where you want to save the JSON file
    json_file_path = "keepa_data.json"

    # Write the data to the JSON file
    with open(json_file_path, "w") as json_file:
        json.dump(data, json_file, indent=2)

    print(f"Data exported to {json_file_path}")
else:
    print(f"Error: Failed to fetch data. Status code: {response.status_code}")
    print(response.text)  # Print the error response for debugging
