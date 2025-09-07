import urllib.request
import json
import os
import ssl
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("BARCODE_LOOKUP_API_KEY")
url = f"https://api.barcodelookup.com/v3/products?barcode=077341125112&formatted=y&key={api_key}"

# Create an unverified SSL context
ssl_context = ssl._create_unverified_context()

try:
    with urllib.request.urlopen(url, context=ssl_context) as response:
        data = json.loads(response.read().decode())
    barcode = data["products"][0]["barcode_number"]
    print("Barcode Number:", barcode)
    name = data["products"][0]["title"]
    print("Title:", name)
    print("Entire Response:")
    print(json.dumps(data, indent=2))
except Exception as e:
    print("Error:", e)
