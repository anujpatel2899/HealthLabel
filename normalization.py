# [file name]: normalization.py
"""
Product data normalization and standardization module.
Cleans and standardizes ingredient names, units, and categories.
"""

import re
import json
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Standard ingredient mappings for common variations
INGREDIENT_STANDARDIZATION = {
    # Sugars
    "sugar": ["sugar", "sucrose", "cane sugar", "white sugar", "refined sugar"],
    "high_fructose_corn_syrup": ["hfcs", "corn syrup", "high fructose corn syrup", "glucose-fructose syrup"],
    "honey": ["honey", "natural honey", "organic honey"],
    "maple_syrup": ["maple syrup", "pure maple syrup"],
    "agave": ["agave nectar", "agave syrup", "agave"],
    
    # Fats and oils
    "palm_oil": ["palm oil", "palm kernel oil", "palmitic acid"],
    "coconut_oil": ["coconut oil", "copra oil"],
    "sunflower_oil": ["sunflower oil", "sunflower seed oil"],
    "soybean_oil": ["soybean oil", "soy oil", "soya oil"],
    "canola_oil": ["canola oil", "rapeseed oil"],
    
    # Preservatives
    "sodium_benzoate": ["sodium benzoate", "benzoate of soda", "e211"],
    "potassium_sorbate": ["potassium sorbate", "e202"],
    "bha": ["bha", "butylated hydroxyanisole", "e320"],
    "bht": ["bht", "butylated hydroxytoluene", "e321"],
    
    # Artificial colors
    "tartrazine": ["tartrazine", "yellow 5", "e102", "fd&c yellow no. 5"],
    "sunset_yellow": ["sunset yellow", "yellow 6", "e110", "fd&c yellow no. 6"],
    "red_40": ["red 40", "allura red", "e129", "fd&c red no. 40"],
    
    # Artificial sweeteners
    "aspartame": ["aspartame", "e951", "nutrasweet", "equal"],
    "sucralose": ["sucralose", "e955", "splenda"],
    "acesulfame_k": ["acesulfame k", "acesulfame potassium", "e950", "ace-k"],
    
    # Common additives
    "msg": ["monosodium glutamate", "msg", "e621", "glutamic acid"],
    "carrageenan": ["carrageenan", "e407", "irish moss extract"],
    "guar_gum": ["guar gum", "e412"],
    "xanthan_gum": ["xanthan gum", "e415"],
}

# Unit standardization mappings
UNIT_CONVERSIONS = {
    # Weight units
    "g": ["g", "grams", "gram", "gm"],
    "kg": ["kg", "kilograms", "kilogram", "kgs"],
    "mg": ["mg", "milligrams", "milligram", "mgs"],
    "oz": ["oz", "ounce", "ounces"],
    "lb": ["lb", "pound", "pounds", "lbs"],
    
    # Volume units
    "ml": ["ml", "milliliter", "milliliters", "mL"],
    "l": ["l", "liter", "liters", "L", "litre", "litres"],
    "fl_oz": ["fl oz", "fluid ounce", "fluid ounces", "fl. oz."],
    "cup": ["cup", "cups", "c"],
    
    # Energy units
    "kcal": ["kcal", "calories", "cal", "kilocalories"],
    "kj": ["kj", "kilojoules", "kilojoule"],
}

# Category mappings
CATEGORY_MAPPINGS = {
    "beverages": [
        "soft drinks", "sodas", "juices", "energy drinks", "sports drinks",
        "tea", "coffee", "water", "alcoholic beverages", "beer", "wine"
    ],
    "snacks": [
        "chips", "crackers", "cookies", "biscuits", "nuts", "popcorn",
        "pretzels", "candy", "chocolate", "confectionery"
    ],
    "dairy": [
        "milk", "cheese", "yogurt", "yoghurt", "butter", "cream",
        "ice cream", "dairy products"
    ],
    "cereals": [
        "breakfast cereals", "cereal", "oats", "muesli", "granola",
        "corn flakes", "rice cereals"
    ],
    "processed_foods": [
        "ready meals", "instant noodles", "frozen foods", "canned foods",
        "packaged foods", "convenience foods"
    ],
    "condiments": [
        "sauces", "dressings", "ketchup", "mayonnaise", "mustard",
        "vinegar", "oils", "spices"
    ]
}

def normalize_product_data(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize and standardize product data
    
    Args:
        product_data: Raw product data dictionary
    
    Returns:
        Normalized product data dictionary
    """
    try:
        normalized = product_data.copy()
        
        # Normalize basic product information
        normalized['name'] = clean_product_name(normalized.get('name', ''))
        normalized['brand'] = clean_brand_name(normalized.get('brand', ''))
        normalized['category'] = standardize_category(normalized.get('category', ''))
        
        # Normalize ingredients
        if normalized.get('ingredients'):
            normalized['ingredients'] = normalize_ingredients(normalized['ingredients'])
        
        # Normalize nutrients
        if normalized.get('nutrients'):
            normalized['nutrients'] = normalize_nutrients(normalized['nutrients'])
        
        # Extract and normalize pack size
        normalized['pack_size'] = extract_pack_size(normalized)
        
        # Add normalization metadata
        normalized['_normalization'] = {
            'processed_at': str(pd.Timestamp.now()),
            'version': '1.0',
            'confidence': calculate_data_confidence(normalized)
        }
        
        logger.info(f"Successfully normalized product: {normalized['name']}")
        return normalized
        
    except Exception as e:
        logger.error(f"Normalization failed: {str(e)}")
        return product_data

def clean_product_name(name: str) -> str:
    """Clean and standardize product name"""
    if not name or not isinstance(name, str):
        return "Unknown Product"
    
    # Remove extra whitespace and convert to title case
    name = re.sub(r'\s+', ' ', name.strip())
    
    # Remove common unwanted characters
    name = re.sub(r'[™®©]', '', name)
    
    # Standardize common abbreviations
    replacements = {
        r'\bPkt\b': 'Pack',
        r'\bPcs\b': 'Pieces',
        r'\bGm\b': 'g',
        r'\bMl\b': 'ml',
        r'\bLtr\b': 'L'
    }
    
    for pattern, replacement in replacements.items():
        name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)
    
    return name.title()

def clean_brand_name(brand: str) -> str:
    """Clean and standardize brand name"""
    if not brand or not isinstance(brand, str):
        return "Unknown Brand"
    
    # Remove extra whitespace
    brand = re.sub(r'\s+', ' ', brand.strip())
    
    # Remove common unwanted characters
    brand = re.sub(r'[™®©]', '', brand)
    
    return brand.title()

def standardize_category(category: str) -> str:
    """Standardize product category"""
    if not category or not isinstance(category, str):
        return "Unknown"
    
    category_lower = category.lower()
    
    # Check against known category mappings
    for standard_category, variations in CATEGORY_MAPPINGS.items():
        if any(variation in category_lower for variation in variations):
            return standard_category.replace('_', ' ').title()
    
    # Clean the original category
    return category.replace('-', ' ').replace('_', ' ').title()

def normalize_ingredients(ingredients: List[str]) -> List[str]:
    """Normalize and standardize ingredient names"""
    if not ingredients or not isinstance(ingredients, list):
        return []
    
    normalized_ingredients = []
    
    for ingredient in ingredients:
        if not isinstance(ingredient, str):
            continue
            
        # Clean the ingredient string
        cleaned = clean_ingredient(ingredient)
        
        # Standardize known ingredients
        standardized = standardize_ingredient(cleaned)
        
        if standardized:
            normalized_ingredients.append(standardized)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_ingredients = []
    for ingredient in normalized_ingredients:
        if ingredient.lower() not in seen:
            unique_ingredients.append(ingredient)
            seen.add(ingredient.lower())
    
    return unique_ingredients

def clean_ingredient(ingredient: str) -> str:
    """Clean individual ingredient string"""
    if not ingredient:
        return ""
    
    # Remove parenthetical information and percentages
    ingredient = re.sub(r'\([^)]*\)', '', ingredient)
    ingredient = re.sub(r'\d+\.?\d*%', '', ingredient)
    
    # Remove extra whitespace and punctuation
    ingredient = re.sub(r'[,;.]$', '', ingredient.strip())
    ingredient = re.sub(r'\s+', ' ', ingredient)
    
    return ingredient.strip()

def standardize_ingredient(ingredient: str) -> str:
    """Standardize ingredient name against known mappings"""
    if not ingredient:
        return ""
    
    ingredient_lower = ingredient.lower()
    
    # Check against standardization mappings
    for standard_name, variations in INGREDIENT_STANDARDIZATION.items():
        if any(variation in ingredient_lower for variation in variations):
            return standard_name.replace('_', ' ').title()
    
    # Return cleaned original if no mapping found
    return ingredient.title()

def normalize_nutrients(nutrients: Dict[str, str]) -> Dict[str, str]:
    """Normalize nutrient data with standardized units"""
    if not nutrients or not isinstance(nutrients, dict):
        return {}
    
    normalized_nutrients = {}
    
    for nutrient, value in nutrients.items():
        if not isinstance(value, str):
            value = str(value)
        
        # Standardize nutrient name
        standard_nutrient = standardize_nutrient_name(nutrient)
        
        # Standardize value and unit
        standard_value = standardize_nutrient_value(value)
        
        if standard_nutrient and standard_value:
            normalized_nutrients[standard_nutrient] = standard_value
    
    return normalized_nutrients

def standardize_nutrient_name(nutrient: str) -> str:
    """Standardize nutrient name"""
    if not nutrient:
        return ""
    
    # Common nutrient name mappings
    mappings = {
        'energy': ['energy', 'calories', 'kcal', 'cal'],
        'protein': ['protein', 'proteins'],
        'carbohydrates': ['carbohydrates', 'carbs', 'carbohydrate', 'total carbohydrates'],
        'sugar': ['sugar', 'sugars', 'total sugars'],
        'fiber': ['fiber', 'fibre', 'dietary fiber', 'dietary fibre'],
        'fat': ['fat', 'total fat', 'fats'],
        'saturated_fat': ['saturated fat', 'saturated fats', 'sat fat'],
        'trans_fat': ['trans fat', 'trans fats'],
        'sodium': ['sodium', 'salt'],
        'cholesterol': ['cholesterol'],
        'calcium': ['calcium'],
        'iron': ['iron'],
        'vitamin_c': ['vitamin c', 'ascorbic acid'],
        'vitamin_d': ['vitamin d']
    }
    
    nutrient_lower = nutrient.lower()
    
    for standard, variations in mappings.items():
        if any(variation in nutrient_lower for variation in variations):
            return standard
    
    # Clean original name
    return re.sub(r'[_-]', ' ', nutrient.lower())

def standardize_nutrient_value(value: str) -> str:
    """Standardize nutrient value with proper units"""
    if not value:
        return ""
    
    # Extract number and unit
    match = re.match(r'(\d+\.?\d*)\s*([a-zA-Z%]*)', str(value).strip())
    
    if not match:
        return value
    
    number, unit = match.groups()
    
    # Standardize unit
    standard_unit = standardize_unit(unit)
    
    return f"{number} {standard_unit}".strip()

def standardize_unit(unit: str) -> str:
    """Standardize measurement unit"""
    if not unit:
        return ""
    
    unit_lower = unit.lower()
    
    for standard, variations in UNIT_CONVERSIONS.items():
        if unit_lower in variations:
            return standard
    
    return unit

def extract_pack_size(product_data: Dict[str, Any]) -> Optional[str]:
    """Extract and standardize pack size information"""
    potential_sources = [
        product_data.get('pack_size'),
        product_data.get('weight'),
        product_data.get('volume'),
        product_data.get('size'),
        product_data.get('quantity')
    ]
    
    for source in potential_sources:
        if source and isinstance(source, str):
            # Look for size patterns
            size_patterns = [
                r'(\d+\.?\d*)\s*(g|grams?|kg|kilograms?|oz|ounces?|lbs?|pounds?)',
                r'(\d+\.?\d*)\s*(ml|milliliters?|l|liters?|litres?|fl\s*oz)',
                r'(\d+)\s*(pieces?|pcs?|count|ct)'
            ]
            
            for pattern in size_patterns:
                match = re.search(pattern, source.lower())
                if match:
                    number, unit = match.groups()
                    standard_unit = standardize_unit(unit)
                    return f"{number} {standard_unit}"
    
    return None

def calculate_data_confidence(normalized_data: Dict[str, Any]) -> float:
    """Calculate confidence score for normalized data completeness"""
    confidence_factors = {
        'name': 0.2,
        'brand': 0.1,
        'ingredients': 0.25,
        'nutrients': 0.25,
        'pack_size': 0.1,
        'category': 0.1
    }
    
    total_confidence = 0.0
    
    for field, weight in confidence_factors.items():
        if field in normalized_data and normalized_data[field]:
            if field == 'ingredients':
                # Score based on number of ingredients
                ingredient_score = min(len(normalized_data[field]) / 10, 1.0)
                total_confidence += weight * ingredient_score
            elif field == 'nutrients':
                # Score based on number of nutrients
                nutrient_score = min(len(normalized_data[field]) / 8, 1.0)
                total_confidence += weight * nutrient_score
            else:
                total_confidence += weight
    
    return round(total_confidence, 2)

def format_ingredients_display(ingredients: List[str]) -> str:
    """Format ingredients list for display with categorization"""
    if not ingredients:
        return "No ingredients available"
    
    # Categorize ingredients
    categorized = categorize_ingredients(ingredients)
    
    formatted_parts = []
    
    for category, items in categorized.items():
        if items:
            category_title = category.replace('_', ' ').title()
            formatted_parts.append(f"**{category_title}:**")
            for item in items:
                formatted_parts.append(f"- {item}")
            formatted_parts.append("")  # Add spacing
    
    # If no categorization, list all ingredients
    if not any(categorized.values()):
        formatted_parts = [f"- {ingredient}" for ingredient in ingredients[:20]]
        if len(ingredients) > 20:
            formatted_parts.append(f"... and {len(ingredients) - 20} more")
    
    return "\n".join(formatted_parts)

def categorize_ingredients(ingredients: List[str]) -> Dict[str, List[str]]:
    """Categorize ingredients by type"""
    categories = {
        'sugars_sweeteners': [],
        'fats_oils': [],
        'preservatives': [],
        'colors_flavors': [],
        'other_additives': [],
        'main_ingredients': []
    }
    
    # Category keywords
    category_keywords = {
        'sugars_sweeteners': ['sugar', 'syrup', 'honey', 'sweetener', 'aspartame', 'sucralose'],
        'fats_oils': ['oil', 'fat', 'butter', 'margarine'],
        'preservatives': ['benzoate', 'sorbate', 'citric acid', 'bha', 'bht'],
        'colors_flavors': ['color', 'flavoring', 'tartrazine', 'msg', 'natural flavor'],
        'other_additives': ['gum', 'lecithin', 'emulsifier', 'stabilizer']
    }
    
    for ingredient in ingredients:
        ingredient_lower = ingredient.lower()
        categorized = False
        
        for category, keywords in category_keywords.items():
            if any(keyword in ingredient_lower for keyword in keywords):
                categories[category].append(ingredient)
                categorized = True
                break
        
        if not categorized:
            categories['main_ingredients'].append(ingredient)
    
    return categories

def convert_units(value_str: str, from_size: str, to_type: str) -> str:
    """Convert units for different serving sizes"""
    try:
        # Extract numeric value
        value_match = re.match(r'(\d+\.?\d*)', value_str.strip())
        if not value_match:
            return "N/A"
        
        value = float(value_match.group(1))
        
        # Extract unit
        unit_match = re.search(r'([a-zA-Z%]+)', value_str)
        unit = unit_match.group(1) if unit_match else ""
        
        if to_type == 'serving':
            # Convert from 100g to serving size
            size_match = re.match(r'(\d+)', from_size)
            if size_match:
                serving_size = float(size_match.group(1))
                converted_value = (value * serving_size) / 100
                return f"{converted_value:.1f} {unit}"
        
        return value_str
        
    except Exception:
        return "N/A"