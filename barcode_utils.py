import requests
import json
from typing import Dict, List, Optional

def fetch_product_by_barcode(barcode: str) -> Dict:
    """
    Fetches product information using barcode from multiple APIs.
    
    Args:
        barcode: Product barcode/EAN/UPC code
        
    Returns:
        Dict with product info or error status
    """
    # Clean the barcode input
    barcode = barcode.strip()
    
    # Try OpenFoodFacts first (most comprehensive free database)
    product_data = fetch_from_openfoodfacts(barcode)
    
    # If not found, try UPCitemdb as fallback
    if not product_data.get("found"):
        product_data = fetch_from_upcitemdb(barcode)
    
    # If still not found, try Barcode Lookup
    if not product_data.get("found"):
        product_data = fetch_from_barcode_lookup(barcode)
    
    return product_data

def fetch_from_openfoodfacts(barcode: str) -> Dict:
    """
    Fetches product data from OpenFoodFacts API.
    Free, no API key required, extensive database.
    """
    try:
        url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}"
        headers = {
            "User-Agent": "FoodHealthAnalyzer/1.0"
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("status") == 1:  # Product found
                product = data.get("product", {})
                
                # Extract ingredients
                ingredients = []
                if product.get("ingredients_text"):
                    # Basic parsing of ingredients text
                    ingredients_text = product.get("ingredients_text", "")
                    ingredients = [
                        ing.strip() 
                        for ing in ingredients_text.replace(".", ",").split(",")
                        if ing.strip()
                    ]
                elif product.get("ingredients"):
                    # Structured ingredients data
                    ingredients = [
                        ing.get("text", ing.get("id", ""))
                        for ing in product.get("ingredients", [])
                    ]
                
                # Extract nutrients (per 100g)
                nutriments = product.get("nutriments", {})
                nutrients = {}
                
                # Map OpenFoodFacts nutrients to our format
                nutrient_mapping = {
                    "energy-kcal_100g": "calories",
                    "fat_100g": "fat",
                    "saturated-fat_100g": "saturated_fat",
                    "carbohydrates_100g": "carbohydrates",
                    "sugars_100g": "sugars",
                    "fiber_100g": "fiber",
                    "proteins_100g": "protein",
                    "salt_100g": "salt",
                    "sodium_100g": "sodium"
                }
                
                for off_key, our_key in nutrient_mapping.items():
                    if off_key in nutriments:
                        value = nutriments[off_key]
                        # Add appropriate units
                        if "energy" in off_key:
                            nutrients[our_key] = f"{value} kcal"
                        elif "sodium" in off_key:
                            nutrients[our_key] = f"{value} mg"
                        else:
                            nutrients[our_key] = f"{value} g"
                
                return {
                    "found": True,
                    "source": "OpenFoodFacts",
                    "name": product.get("product_name", "Unknown Product"),
                    "brand": product.get("brands", "Unknown Brand"),
                    "ingredients": ingredients,
                    "nutrients": nutrients,
                    "image_url": product.get("image_url"),
                    "categories": product.get("categories_tags", []),
                    "nutriscore": product.get("nutriscore_grade", "unknown").upper(),
                    "nova_group": product.get("nova_group", "unknown")
                }
        
        return {"found": False, "source": "OpenFoodFacts", "error": "Product not found"}
    
    except requests.RequestException as e:
        return {"found": False, "source": "OpenFoodFacts", "error": f"API error: {str(e)}"}
    except Exception as e:
        return {"found": False, "source": "OpenFoodFacts", "error": f"Processing error: {str(e)}"}

def fetch_from_upcitemdb(barcode: str) -> Dict:
    """
    Fetches from UPCitemdb API (limited free tier).
    Note: This has rate limits on free tier.
    """
    try:
        url = f"https://api.upcitemdb.com/prod/trial/lookup"
        params = {"upc": barcode}
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("items") and len(data["items"]) > 0:
                item = data["items"][0]
                
                # UPCitemdb has limited nutritional data
                return {
                    "found": True,
                    "source": "UPCitemdb",
                    "name": item.get("title", "Unknown Product"),
                    "brand": item.get("brand", "Unknown Brand"),
                    "ingredients": [],  # UPCitemdb doesn't provide ingredients
                    "nutrients": {},  # Limited nutritional data
                    "description": item.get("description", ""),
                    "image_url": item.get("images", [None])[0] if item.get("images") else None
                }
        
        return {"found": False, "source": "UPCitemdb", "error": "Product not found"}
    
    except Exception as e:
        return {"found": False, "source": "UPCitemdb", "error": f"API error: {str(e)}"}

def fetch_from_barcode_lookup(barcode: str) -> Dict:
    """
    Fetches from Barcode Lookup API.
    Note: Requires API key for production use.
    """
    try:
        # This is a demo endpoint - for production, use API key
        url = f"https://www.barcodelookup.com/api/v3/products"
        params = {
            "barcode": barcode,
            "key": "demo"  # Replace with actual API key for production
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("products") and len(data["products"]) > 0:
                product = data["products"][0]
                
                # Extract available nutrition info
                nutrients = {}
                nutrition = product.get("nutrition_facts", {})
                if nutrition:
                    nutrients = {
                        "calories": nutrition.get("calories", "N/A"),
                        "fat": nutrition.get("fat", "N/A"),
                        "carbohydrates": nutrition.get("carbs", "N/A"),
                        "protein": nutrition.get("protein", "N/A")
                    }
                
                return {
                    "found": True,
                    "source": "Barcode Lookup",
                    "name": product.get("product_name", "Unknown Product"),
                    "brand": product.get("brand", "Unknown Brand"),
                    "ingredients": product.get("ingredients", "").split(",") if product.get("ingredients") else [],
                    "nutrients": nutrients,
                    "image_url": product.get("images", [None])[0] if product.get("images") else None
                }
        
        return {"found": False, "source": "Barcode Lookup", "error": "Product not found"}
    
    except Exception as e:
        return {"found": False, "source": "Barcode Lookup", "error": f"API error: {str(e)}"}

def search_product_by_name(product_name: str) -> List[Dict]:
    """
    Search for products by name (useful when barcode fails).
    Returns a list of matching products.
    """
    try:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            "search_terms": product_name,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 5  # Limit results
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            products = []
            
            for product in data.get("products", []):
                products.append({
                    "name": product.get("product_name", "Unknown"),
                    "brand": product.get("brands", "Unknown"),
                    "barcode": product.get("code", ""),
                    "image_url": product.get("image_small_url")
                })
            
            return products
        
        return []
    
    except Exception:
        return []

def validate_barcode(barcode: str) -> bool:
    """
    Validates if a barcode is in correct format.
    Most common formats: EAN-13 (13 digits), UPC-A (12 digits), EAN-8 (8 digits)
    """
    # Remove any spaces or dashes
    barcode = barcode.replace(" ", "").replace("-", "")
    
    # Check if it's all digits
    if not barcode.isdigit():
        return False
    
    # Check common barcode lengths
    if len(barcode) in [8, 12, 13, 14]:
        return True
    
    return False

# Example usage and testing
if __name__ == "__main__":
    # Test with a known barcode (Coca-Cola example)
    test_barcode = "5449000000996"
    print(f"Testing barcode: {test_barcode}")
    
    result = fetch_product_by_barcode(test_barcode)
    print(json.dumps(result, indent=2))