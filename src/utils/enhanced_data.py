"""
Enhanced data handling for the Health Rater application.
"""

import json
import os
import pandas as pd
from datetime import datetime
import uuid
from typing import List, Dict, Any, Optional

class EnhancedHistoryManager:
    """Enhanced history manager with search and comparison features."""
    
    def __init__(self, history_file_path: str = "data/product_history.json"):
        """Initialize the history manager."""
        self.history_file_path = history_file_path
        self.comparison_products = []
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(history_file_path), exist_ok=True)
        
        # Create empty history file if it doesn't exist
        if not os.path.exists(history_file_path):
            with open(history_file_path, 'w') as f:
                json.dump([], f)
    
    def add_to_history(self, product_data: Dict[str, Any], score_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a product and its score to the history."""
        try:
            # Read current history
            history = self._read_history()
            
            # Create history entry
            entry = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "product_name": product_data.get("product_name", "Unknown Product"),
                "brand": product_data.get("brand", "Unknown"),
                "source": product_data.get("source", "Unknown"),
                "confidence": product_data.get("confidence", "Unknown"),
                "product_data": product_data,
                "score_data": score_data
            }
            
            # Add to history
            history.append(entry)
            
            # Limit history size to 100 entries
            if len(history) > 100:
                history = history[-100:]
            
            # Save history
            self._write_history(history)
            
            return entry
        except Exception as e:
            print(f"Error adding to history: {str(e)}")
            return {}
    
    def get_history(self, limit: int = None, search_query: str = None) -> List[Dict[str, Any]]:
        """Get history entries, optionally filtered by search query."""
        history = self._read_history()
        
        # Apply search filter if provided
        if search_query:
            search_query = search_query.lower()
            filtered_history = []
            
            for entry in history:
                # Search in product name, brand, and source
                product_name = entry.get("product_name", "").lower()
                brand = entry.get("brand", "").lower()
                source = entry.get("source", "").lower()
                
                if (search_query in product_name or 
                    search_query in brand or 
                    search_query in source):
                    filtered_history.append(entry)
            
            history = filtered_history
        
        # Apply limit if provided
        if limit is not None and limit > 0:
            history = history[-limit:]
        
        return history
    
    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get a product by its ID."""
        history = self._read_history()
        
        for entry in history:
            if entry.get("id") == product_id:
                return entry
        
        return None
    
    def delete_product(self, product_id: str) -> bool:
        """Delete a product from history by its ID."""
        try:
            history = self._read_history()
            
            # Filter out the product to delete
            updated_history = [entry for entry in history if entry.get("id") != product_id]
            
            # If no products were removed, return False
            if len(updated_history) == len(history):
                return False
            
            # Save updated history
            self._write_history(updated_history)
            
            # Remove from comparison list if present
            self.comparison_products = [p for p in self.comparison_products if p != product_id]
            
            return True
        except Exception as e:
            print(f"Error deleting product: {str(e)}")
            return False
    
    def clear_history(self) -> bool:
        """Clear all history."""
        try:
            self._write_history([])
            self.comparison_products = []
            return True
        except Exception as e:
            print(f"Error clearing history: {str(e)}")
            return False
    
    def add_to_comparison(self, product_id: str) -> bool:
        """Add a product to the comparison list."""
        # Check if product exists
        product = self.get_product_by_id(product_id)
        if not product:
            return False
        
        # Check if already in comparison
        if product_id in self.comparison_products:
            return True
        
        # Add to comparison (limit to 4 products)
        if len(self.comparison_products) >= 4:
            self.comparison_products.pop(0)  # Remove oldest
        
        self.comparison_products.append(product_id)
        return True
    
    def remove_from_comparison(self, product_id: str) -> bool:
        """Remove a product from the comparison list."""
        if product_id in self.comparison_products:
            self.comparison_products.remove(product_id)
            return True
        return False
    
    def get_comparison_products(self) -> List[Dict[str, Any]]:
        """Get all products in the comparison list."""
        products = []
        
        for product_id in self.comparison_products:
            product = self.get_product_by_id(product_id)
            if product:
                products.append(product)
        
        return products
    
    def clear_comparison(self) -> None:
        """Clear the comparison list."""
        self.comparison_products = []
    
    def export_to_csv(self, product_ids: List[str] = None) -> pd.DataFrame:
        """Export product data to a DataFrame for CSV export."""
        history = self._read_history()
        
        if product_ids:
            # Filter to specified products
            products = [p for p in history if p.get("id") in product_ids]
        else:
            products = history
        
        # Extract relevant data for each product
        data = []
        for product in products:
            product_data = product.get("product_data", {})
            score_data = product.get("score_data", {})
            nutrition_data = product_data.get("nutrition_data", {})
            
            row = {
                "Product Name": product.get("product_name", "Unknown"),
                "Brand": product.get("brand", "Unknown"),
                "Source": product.get("source", "Unknown"),
                "Confidence": product.get("confidence", "Unknown"),
                "Nutri-Score Grade": score_data.get("grade", "?"),
                "Nutri-Score Value": score_data.get("raw_score", 0),
                "Health Score (0-100)": score_data.get("normalized_score", 0),
                "Energy (kcal)": nutrition_data.get("energy_kcal", 0),
                "Sugars (g)": nutrition_data.get("sugars_g", 0),
                "Saturated Fat (g)": nutrition_data.get("saturated_fat_g", 0),
                "Salt (g)": nutrition_data.get("salt_g", 0),
                "Fiber (g)": nutrition_data.get("fiber_g", 0),
                "Protein (g)": nutrition_data.get("protein_g", 0),
                "Fruits/Veg/Nuts (%)": nutrition_data.get("fruits_veg_nuts_percent", 0),
                "Date Added": product.get("timestamp", "")
            }
            
            data.append(row)
        
        return pd.DataFrame(data)
    
    def _read_history(self) -> List[Dict[str, Any]]:
        """Read history from file."""
        try:
            with open(self.history_file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _write_history(self, history: List[Dict[str, Any]]) -> None:
        """Write history to file."""
        with open(self.history_file_path, 'w') as f:
            json.dump(history, f, indent=2)

# Export URL generator for sharing
def generate_share_url(product_id: str, base_url: str = "http://localhost:8050") -> str:
    """Generate a shareable URL for a product."""
    return f"{base_url}?product={product_id}"

# Helper for unit conversion
def convert_units(value: float, unit_system: str, unit_type: str) -> Dict[str, Any]:
    """Convert units based on selected unit system."""
    if unit_system == "metric":
        if unit_type == "weight":
            return {"value": value, "unit": "g"}
        elif unit_type == "volume":
            return {"value": value, "unit": "ml"}
        elif unit_type == "energy":
            return {"value": value, "unit": "kcal"}
    elif unit_system == "imperial":
        if unit_type == "weight":
            # Convert grams to ounces
            return {"value": value * 0.03527396, "unit": "oz"}
        elif unit_type == "volume":
            # Convert ml to fluid ounces
            return {"value": value * 0.033814, "unit": "fl oz"}
        elif unit_type == "energy":
            # Keep same value but use "Cal" instead of "kcal"
            return {"value": value, "unit": "Cal"}
    
    # Default return if no conversion applies
    return {"value": value, "unit": ""}
