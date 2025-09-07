import requests
import json
from typing import Dict, List, Optional
import logging
from functools import lru_cache
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TIMEOUT = 10

class ProductAPIClient:
    """Unified client for product API services"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "FoodHealthAnalyzer/1.0 (Educational/Research)"
        })
        self.barcode_lookup_key = os.getenv("BARCODE_LOOKUP_API_KEY")

    def fetch_product_by_barcode(self, barcode: str) -> Dict:
        """
        Fetch product information using barcode from APIs.
        Priority: BarcodeLookup → OpenFoodFacts
        """
        # Validate and clean barcode
        cleaned_barcode = self._clean_barcode(barcode)
        if not self._validate_barcode(cleaned_barcode):
            return {"found": False, "error": "Invalid barcode format"}
        
        # Try APIs in order of preference
        api_methods = [
            self._fetch_from_barcodelookup,
            self._fetch_from_openfoodfacts,
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

    def _fetch_from_barcodelookup(self, barcode: str) -> Dict:
        """Fetch from BarcodeLookup API (primary source)"""
        if not self.barcode_lookup_key:
            raise Exception("BarcodeLookup API key not configured")
        
        url = "https://api.barcodelookup.com/v3/products"
        params = {
            "barcode": barcode,
            "formatted": "y",
            "key": self.barcode_lookup_key
        }
        
        try:
            response = self.session.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("products") and len(data["products"]) > 0:
                product = data["products"][0]
                return self._parse_barcodelookup_data(product, barcode)
            
            return {"found": False, "source": "BarcodeLookup", "error": "Product not found"}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"BarcodeLookup API error: {str(e)}")
            return {"found": False, "source": "BarcodeLookup", "error": str(e)}

    def _parse_barcodelookup_data(self, product: Dict, barcode: str) -> Dict:
        """Parse BarcodeLookup product data into standardized format"""
        # Extract ingredients
        ingredients = self._extract_ingredients_barcodelookup(product)
        
        # Extract nutrients
        nutrients = self._extract_nutrients_barcodelookup(product)
        
        # Get product metadata
        return {
            "found": True,
            "source": "BarcodeLookup",
            "barcode": barcode,
            "name": product.get("product_name", "Unknown Product"),
            "brand": product.get("brand", "Unknown Brand"),
            "ingredients": ingredients,
            "nutrients": nutrients,
            "image_url": product.get("images", [None])[0] if product.get("images") else None,
            "description": product.get("description", ""),
            "category": product.get("category", ""),
            "weight": product.get("weight", ""),
            "nutrition_facts": product.get("nutrition_facts", "")
        }

    def _extract_ingredients_barcodelookup(self, product: Dict) -> List[str]:
        """Extract ingredients from BarcodeLookup data"""
        ingredients = []
        
        # Try different ingredient fields
        ingredients_text = product.get("ingredients") or product.get("ingredients_english")
        
        if ingredients_text:
            # Basic parsing - split by common separators
            raw_ingredients = ingredients_text.replace(".", ",").split(",")
            ingredients = [ing.strip() for ing in raw_ingredients if ing.strip()]
        
        return ingredients[:20]  # Limit to first 20 ingredients

    def _extract_nutrients_barcodelookup(self, product: Dict) -> Dict:
        """Extract nutrients from BarcodeLookup data"""
        nutrients = {}
        
        # Check if nutrition facts are available
        nutrition_facts = product.get("nutrition_facts")
        if nutrition_facts:
            nutrients["nutrition_facts"] = nutrition_facts
        
        # Look for specific nutrient fields
        nutrient_mapping = {
            "calories": ("calories", "kcal"),
            "fat": ("fat", "g"),
            "saturated_fat": ("saturated_fat", "g"),
            "carbohydrates": ("carbohydrates", "g"),
            "sugar": ("sugars", "g"),
            "fiber": ("fiber", "g"),
            "protein": ("protein", "g"),
            "sodium": ("sodium", "mg")
        }
        
        for api_key, (our_key, unit) in nutrient_mapping.items():
            value = product.get(api_key)
            if value is not None:
                nutrients[our_key] = f"{value} {unit}"
        
        return nutrients

    def _fetch_from_openfoodfacts(self, barcode: str) -> Dict:
        """Fetch from OpenFoodFacts API (fallback)"""
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
            raw_ingredients = ingredients_text.replace(".", ",").split(",")
            ingredients = [ing.strip() for ing in raw_ingredients if ing.strip()]
        
        return ingredients[:20]

    def _extract_nutrients(self, nutriments: Dict) -> Dict:
        """Extract and normalize nutrient data"""
        nutrients = {}
        
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
                nutrients[our_key] = f"{value:.1f} {unit}"
        
        return nutrients

    @lru_cache(maxsize=100)
    def search_product_by_name(self, product_name: str) -> List[Dict]:
        """
        Search for products by name with caching.
        Uses BarcodeLookup API for better results
        """
        if len(product_name.strip()) < 3:
            return []
        
        if not self.barcode_lookup_key:
            # Fallback to OpenFoodFacts if no BarcodeLookup key
            return self._search_openfoodfacts(product_name)
        
        # Try BarcodeLookup search first
        try:
            url = "https://api.barcodelookup.com/v3/products"
            params = {
                "search": product_name.strip(),
                "formatted": "y",
                "key": self.barcode_lookup_key,
                "limit": 10
            }
            
            response = self.session.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            products = []
            
            for product in data.get("products", []):
                products.append({
                    "name": product.get("product_name", "Unknown"),
                    "brand": product.get("brand", "Unknown Brand"),
                    "barcode": product.get("barcode_number", ""),
                    "image_url": product.get("images", [None])[0] if product.get("images") else None,
                    "category": product.get("category", "")
                })
            
            return products
            
        except Exception as e:
            logger.error(f"BarcodeLookup search error: {str(e)}")
            # Fallback to OpenFoodFacts
            return self._search_openfoodfacts(product_name)

    def _search_openfoodfacts(self, product_name: str) -> List[Dict]:
        """Fallback search using OpenFoodFacts"""
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