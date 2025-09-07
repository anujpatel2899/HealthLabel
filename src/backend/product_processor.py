import logging
import json
import os
import requests
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductDataProcessor:
    """Class to process and normalize product data from various sources."""
    
    def __init__(self):
        """Initialize the data processor."""
        self.history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'product_history.json')
        self._ensure_history_file_exists()
        
    def _ensure_history_file_exists(self):
        """Create the history file if it doesn't exist."""
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w') as f:
                json.dump([], f)
    
    def process_barcode_data(self, barcode):
        """
        Process data from a barcode, attempt to fetch product information.
        Args:
            barcode: The barcode string
        Returns:
            dict: Normalized product data or None if not found
        """
        logger.info(f"Processing barcode: {barcode}")
        try:
            # Call Open Food Facts API
            url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch product data for barcode {barcode}: Status {response.status_code}")
                return None
            data = response.json()
            if data.get('status') != 1:
                logger.warning(f"Product not found for barcode {barcode}")
                return None
            product_data = data.get('product', {})
            normalized_data = self._normalize_product_data(product_data)
            self._save_to_history(normalized_data)
            return normalized_data
        except Exception as e:
            logger.error(f"Error processing barcode data: {str(e)}")
            return None
    
    def process_text_input(self, text_input, llm_processor=None):
        """
        Process text input (likely from OCR or manual entry).
        
        Args:
            text_input: The text input describing the product
            llm_processor: Optional LLM processor for text analysis (LangGraphProcessor or LLMProcessor)
            
        Returns:
            dict: Normalized product data
        """
        logger.info("Processing text input")
        
        # If we have an LLM processor, use it to extract structured data
        if llm_processor:
            # Check if it's a LangGraphProcessor (new implementation) or old LLMProcessor
            if hasattr(llm_processor, 'extract_nutrition_data'):
                structured_data = llm_processor.extract_nutrition_data(text_input)
                if structured_data:
                    # LangGraphProcessor returns a dict, so we can use it directly
                    # Save to history
                    self._save_to_history(structured_data)
                    return structured_data
        
        # Fallback: very basic parsing (would need more sophisticated approach in production)
        # This is just a placeholder for demonstration
        structured_data = {
            "product_name": "Unknown Product",
            "nutrition_data": {
                "energy_kcal": 0,
                "sugars_g": 0,
                "saturated_fat_g": 0,
                "salt_g": 0,
                "fiber_g": 0,
                "protein_g": 0,
                "fruits_veg_nuts_percent": 0
            },
            "ingredients": [],
            "source": "Text Input",
            "confidence": "Low"
        }
        
        # Save to history
        self._save_to_history(structured_data)
        
        return structured_data
    
    def _normalize_product_data(self, product_data):
        """
        Normalize product data into a consistent format.
        
        Args:
            product_data: Raw product data
            
        Returns:
            dict: Normalized product data
        """
        # Extract basic product information
        product_name = product_data.get('product_name', 'Unknown Product')
        
        # Extract nutrition data
        nutriments = product_data.get('nutriments', {})
        
        # Normalize nutrient values (per 100g/ml)
        energy_kcal = nutriments.get('energy-kcal_100g', nutriments.get('energy_100g', 0))
        sugars_g = nutriments.get('sugars_100g', 0)
        saturated_fat_g = nutriments.get('saturated-fat_100g', 0)
        salt_g = nutriments.get('salt_100g', 0)
        fiber_g = nutriments.get('fiber_100g', 0)
        protein_g = nutriments.get('proteins_100g', 0)
        
        # Extract ingredients
        ingredients_text = product_data.get('ingredients_text', '')
        ingredients = [i.strip() for i in ingredients_text.split(',') if i.strip()]
        
        # Estimate fruits/vegetables/nuts percentage if available
        fruits_veg_nuts_percent = 0
        if 'fruits-vegetables-nuts-estimate-from-ingredients_100g' in product_data:
            fruits_veg_nuts_percent = product_data.get('fruits-vegetables-nuts-estimate-from-ingredients_100g', 0)
        
        # Check for sweeteners in ingredients
        contains_sweeteners = any(sweetener in ingredients_text.lower() for sweetener in 
                                 ['aspartame', 'sucralose', 'saccharin', 'stevia', 'acesulfame', 'neotame'])
        
        # Determine if it's a beverage
        is_beverage = 'beverage' in product_data.get('categories_tags', []) or 'drink' in product_data.get('categories_tags', [])
        
        # Determine if it's a cheese product
        is_cheese = 'cheese' in product_data.get('categories_tags', [])
        
        # Create normalized data structure
        normalized_data = {
            "product_name": product_name,
            "product_id": product_data.get('code', ''),
            "brand": product_data.get('brands', ''),
            "quantity": product_data.get('quantity', ''),
            "categories": product_data.get('categories', ''),
            "nutrition_data": {
                "energy_kcal": energy_kcal,
                "sugars_g": sugars_g,
                "saturated_fat_g": saturated_fat_g,
                "salt_g": salt_g,
                "fiber_g": fiber_g,
                "protein_g": protein_g,
                "fruits_veg_nuts_percent": fruits_veg_nuts_percent
            },
            "product_type": {
                "is_beverage": is_beverage,
                "is_cheese": is_cheese,
                "contains_sweeteners": contains_sweeteners
            },
            "ingredients": ingredients,
            "image_url": product_data.get('image_url', ''),
            "source": "Open Food Facts",
            "confidence": "High",
            "timestamp": datetime.now().isoformat()
        }
        
        return normalized_data
    
    def _save_to_history(self, product_data):
        """Save processed product to history."""
        try:
            # Load existing history
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            # Add new entry
            history.append(product_data)
            
            # Save back to file
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
            logger.info("Product saved to history")
            
        except Exception as e:
            logger.error(f"Error saving to history: {str(e)}")
    
    def get_history(self, limit=10):
        """Get product search history."""
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            # Return the most recent entries
            return history[-limit:] if history else []
            
        except Exception as e:
            logger.error(f"Error loading history: {str(e)}")
            return []
    
    def delete_history_entry(self, entry_index):
        """Delete a specific entry from history by index.
        
        Args:
            entry_index: Index of the entry to delete (0 is the oldest)
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            if 0 <= entry_index < len(history):
                # Remove the entry
                del history[entry_index]
                
                # Save back to file
                with open(self.history_file, 'w') as f:
                    json.dump(history, f, indent=2)
                
                logger.info(f"History entry at index {entry_index} deleted")
                return True
            else:
                logger.warning(f"Invalid history index: {entry_index}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting history entry: {str(e)}")
            return False
