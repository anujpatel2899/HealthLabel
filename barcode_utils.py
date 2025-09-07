import requests
import json
from typing import Dict, List, Optional
import logging
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TIMEOUT = 10
MAX_RETRIES = 2

class ProductAPIClient:
    """Unified client for multiple product API services"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "FoodHealthAnalyzer/1.0 (Educational/Research)"
        })

    def fetch_product_by_barcode(self, barcode: str) -> Dict:
        """
        Fetch product information using barcode from multiple APIs.
        
        Args:
            barcode: Product barcode/EAN/UPC code
            
        Returns:
            Dict with product info or error status
        """
        # Validate and clean barcode
        cleaned_barcode = self._clean_barcode(barcode)
        if not self._validate_barcode(cleaned_barcode):
            return {"found": False, "error": "Invalid barcode format"}
        
        # Try APIs in order of preference
        api_methods = [
            self._fetch_from_openfoodfacts,
            self._fetch_from_upcitemdb,
        ]
        
        for method in api_methods:
            try:
                result = method(cleaned_barcode)
                if result.get("found"):
                    logger.info(f"Product found using {result.get('source')}")
                    return result
            except Exception as e:
                logger.warning(f"API method {method.__name__} failed: {str(e)}")
                continue
        
        return {"found": False, "error": "Product not found in any database"}

    def _clean_barcode(self, barcode: str) -> str:
        """Clean and normalize barcode string"""
        return barcode.strip().replace(" ", "").replace("-", "")

    def _validate_barcode(self, barcode: str) -> bool:
        """Validate barcode format"""
        if not barcode.isdigit():
            return False
        return len(barcode) in [8, 12, 13, 14]

    def _fetch_from_openfoodfacts(self, barcode: str) -> Dict:
        """Fetch from OpenFoodFacts API"""
        url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}"
        
        try:
            response = self.session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") == 1:
                product = data.get("product", {})
                return self._parse_openfoodfacts_data(product)
            
            return {"found": False, "source": "OpenFoodFacts", "error": "Product not found"}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenFoodFacts API error: {str(e)}")
            return {"found": False, "source": "OpenFoodFacts", "error": str(e)}

    def _parse_openfoodfacts_data(self, product: Dict) -> Dict:
        """Parse OpenFoodFacts product data into standardized format"""
        # Extract and process ingredients
        ingredients = self._extract_ingredients(product)
        
        # Extract and normalize nutrients
        nutrients = self._extract_nutrients(product.get("nutriments", {}))
        
        # Get product metadata
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
            "nova_group": product.get("nova_group", "unknown"),
            "serving_size": product.get("serving_size"),
            "packaging": product.get("packaging_tags", [])
        }

    def _extract_ingredients(self, product: Dict) -> List[str]:
        """Extract and clean ingredients list"""
        ingredients = []
        
        # Try structured ingredients first
        if product.get("ingredients"):
            for ing in product["ingredients"]:
                ingredient_text = ing.get("text", ing.get("id", "")).strip()
                if ingredient_text:
                    ingredients.append(ingredient_text)
        
        # Fallback to ingredients text
        elif product.get("ingredients_text"):
            ingredients_text = product["ingredients_text"]
            # Basic parsing - split by common separators
            raw_ingredients = ingredients_text.replace(".", ",").split(",")
            ingredients = [ing.strip() for ing in raw_ingredients if ing.strip()]
        
        return ingredients[:20]  # Limit to first 20 ingredients

    def _extract_nutrients(self, nutriments: Dict) -> Dict:
        """Extract and normalize nutrient data"""
        nutrients = {}
        
        # Nutrient mapping with priority for per 100g values
        nutrient_mapping = {
            "energy-kcal_100g": ("calories", "kcal"),
            "fat_100g": ("fat", "g"),
            "saturated-fat_100g": ("saturated_fat", "g"),
            "carbohydrates_100g": ("carbohydrates", "g"),
            "sugars_100g": ("sugars", "g"),
            "fiber_100g": ("fiber", "g"),
            "proteins_100g": ("protein", "g"),
            "salt_100g": ("salt", "g"),
            "sodium_100g": ("sodium", "mg")
        }
        
        for off_key, (our_key, unit) in nutrient_mapping.items():
            value = nutriments.get(off_key)
            if value is not None:
                # Convert sodium from g to mg if needed
                if our_key == "sodium" and unit == "mg" and "salt" not in off_key:
                    value = value * 1000 if value < 10 else value  # Assume it's in grams if < 10
                
                nutrients[our_key] = f"{value:.1f} {unit}"
        
        return nutrients

    def _fetch_from_upcitemdb(self, barcode: str) -> Dict:
        """Fetch from UPCitemdb API (limited free tier)"""
        url = "https://api.upcitemdb.com/prod/trial/lookup"
        params = {"upc": barcode}
        
        try:
            response = self.session.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("items") and len(data["items"]) > 0:
                item = data["items"][0]
                
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
            
        except requests.exceptions.RequestException as e:
            logger.error(f"UPCitemdb API error: {str(e)}")
            return {"found": False, "source": "UPCitemdb", "error": str(e)}

    @lru_cache(maxsize=100)
    def search_product_by_name(self, product_name: str) -> List[Dict]:
        """
        Search for products by name with caching.
        
        Args:
            product_name: Product name to search for
            
        Returns:
            List of matching products
        """
        if len(product_name.strip()) < 3:
            return []
        
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            "search_terms": product_name.strip(),
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 10,
            "fields": "code,product_name,brands,image_small_url,nutriscore_grade"
        }
        
        try:
            response = self.session.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            products = []
            
            for product in data.get("products", []):
                # Filter out products with missing essential data
                if not product.get("product_name") or not product.get("code"):
                    continue
                
                products.append({
                    "name": product.get("product_name", "Unknown"),
                    "brand": product.get("brands", "Unknown Brand"),
                    "barcode": product.get("code", ""),
                    "image_url": product.get("image_small_url"),
                    "nutriscore": product.get("nutriscore_grade", "").upper()
                })
            
            return products
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Product search error: {str(e)}")
            return []

# Global client instance
_api_client = None

def get_api_client() -> ProductAPIClient:
    """Get or create global API client instance"""
    global _api_client
    if _api_client is None:
        _api_client = ProductAPIClient()
    return _api_client

# Public API functions
def fetch_product_by_barcode(barcode: str) -> Dict:
    """Public interface for barcode lookup"""
    client = get_api_client()
    return client.fetch_product_by_barcode(barcode)

def search_product_by_name(product_name: str) -> List[Dict]:
    """Public interface for product name search"""
    client = get_api_client()
    return client.search_product_by_name(product_name)

def validate_barcode(barcode: str) -> bool:
    """Public interface for barcode validation"""
    client = get_api_client()
    return client._validate_barcode(client._clean_barcode(barcode))

# Test function
def test_api():
    """Test function for development"""
    # Test with a known barcode (Coca-Cola)
    test_barcode = "5449000000996"
    print(f"Testing barcode: {test_barcode}")
    
    result = fetch_product_by_barcode(test_barcode)
    print(json.dumps(result, indent=2))
    
    # Test search
    print("\nTesting search:")
    search_results = search_product_by_name("Nutella")
    for product in search_results[:3]:
        print(f"- {product['name']} ({product['brand']})")

if __name__ == "__main__":
    test_api()