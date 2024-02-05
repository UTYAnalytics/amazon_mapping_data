from apify_client import ApifyClient
import pandas as pd

# Replace 'your_api_access_token' with your actual Apify API access token
apify_client = ApifyClient("apify_api_L0SHnudrftNCT9xclBaUVBKTddBUB60WZ66u")

# Replace 'your_dataset.csv' with the path to your actual CSV file
data_to_upload = pd.read_csv("SellerProductData.csv").fillna("")

# Make sure to replace 'your_dataset_name' with a name for your dataset
dataset_collection_client = apify_client.datasets()
dataset_info = dataset_collection_client.get_or_create(
    name="SellerProductData"  # The name is just for your convenience, it can be anything
)

# Uploads the data to the Apify dataset
data_client = apify_client.dataset(dataset_info["id"])
data_client.push_items(data_to_upload.to_dict(orient="records"))
