from urllib.parse import urlparse

url = 'https://www.amazon.com/-/es/refrescantes-individual-bolsillo-ajustables-decoloraci%C3%B3n/dp/B0B927SM93'

# Parse the URL
parsed_url = urlparse(url)

# Extract the last component of the path, which is the value you're looking for
product_id = parsed_url.path.split('/')[-1]

print(product_id)
