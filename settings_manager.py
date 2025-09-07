# [file name]: settings_manager.py
"""
Settings and preferences management for the food analyzer.
Handles unit conversions, regional preferences, and user settings.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class UserPreferences:
    """User preference settings"""
    region: str = "India (FSSAI)"
    weight_unit: str = "grams"
    volume_unit: str = "ml" 
    temperature_unit: str = "celsius"
    analysis_strictness: int = 3
    include_additives: bool = True
    show_evidence_by_default: bool = True
    language: str = "en"
    theme: str = "light"

class UnitConverter:
    """Unit conversion utilities"""
    
    # Weight conversions to grams
    WEIGHT_TO_GRAMS = {
        'g': 1,
        'grams': 1,
        'gram': 1,
        'kg': 1000,
        'kilogram': 1000,
        'kilograms': 1000,
        'mg': 0.001,
        'milligram': 0.001,
        'milligrams': 0.001,
        'oz': 28.3495,
        'ounce': 28.3495,
        'ounces': 28.3495,
        'lb': 453.592,
        'pound': 453.592,
        'pounds': 453.592
    }
    
    # Volume conversions to milliliters
    VOLUME_TO_ML = {
        'ml': 1,
        'milliliter': 1,
        'milliliters': 1,
        'l': 1000,
        'liter': 1000,
        'liters': 1000,
        'litre': 1000,
        'litres': 1000,
        'fl_oz': 29.5735,
        'fl oz': 29.5735,
        'fluid ounce': 29.5735,
        'fluid ounces': 29.5735,
        'cup': 236.588,
        'cups': 236.588,
        'pint': 473.176,
        'pints': 473.176,
        'quart': 946.353,
        'quarts': 946.353,
        'gallon': 3785.41,
        'gallons': 3785.41
    }
    
    @classmethod
    def convert_weight(cls, value: float, from_unit: str, to_unit: str) -> float:
        """Convert weight between units"""
        try:
            from_unit = from_unit.lower().strip()
            to_unit = to_unit.lower().strip()
            
            if from_unit not in cls.WEIGHT_TO_GRAMS or to_unit not in cls.WEIGHT_TO_GRAMS:
                raise ValueError(f"Unsupported weight units: {from_unit} or {to_unit}")
            
            # Convert to grams first, then to target unit
            grams = value * cls.WEIGHT_TO_GRAMS[from_unit]
            result = grams / cls.WEIGHT_TO_GRAMS[to_unit]
            
            return round(result, 3)
            
        except Exception as e:
            logger.error(f"Weight conversion failed: {e}")
            return value  # Return original if conversion fails
    
    @classmethod
    def convert_volume(cls, value: float, from_unit: str, to_unit: str) -> float:
        """Convert volume between units"""
        try:
            from_unit = from_unit.lower().strip()
            to_unit = to_unit.lower().strip()
            
            if from_unit not in cls.VOLUME_TO_ML or to_unit not in cls.VOLUME_TO_ML:
                raise ValueError(f"Unsupported volume units: {from_unit} or {to_unit}")
            
            # Convert to ml first, then to target unit  
            ml = value * cls.VOLUME_TO_ML[from_unit]
            result = ml / cls.VOLUME_TO_ML[to_unit]
            
            return round(result, 3)
            
        except Exception as e:
            logger.error(f"Volume conversion failed: {e}")
            return value  # Return original if conversion fails
    
    @classmethod
    def normalize_unit_name(cls, unit: str) -> str:
        """Normalize unit name to standard form"""
        unit_mappings = {
            # Weight units
            'g': 'g', 'grams': 'g', 'gram': 'g', 'gm': 'g',
            'kg': 'kg', 'kilogram': 'kg', 'kilograms': 'kg', 'kgs': 'kg',
            'mg': 'mg', 'milligram': 'mg', 'milligrams': 'mg', 'mgs': 'mg',
            'oz': 'oz', 'ounce': 'oz', 'ounces': 'oz',
            'lb': 'lb', 'pound': 'lb', 'pounds': 'lb', 'lbs': 'lb',
            
            # Volume units
            'ml': 'ml', 'milliliter': 'ml', 'milliliters': 'ml', 'mL': 'ml',
            'l': 'L', 'liter': 'L', 'liters': 'L', 'litre': 'L', 'litres': 'L',
            'fl oz': 'fl oz', 'fluid ounce': 'fl oz', 'fluid ounces': 'fl oz',
            'cup': 'cup', 'cups': 'cup',
        }
        
        return unit_mappings.get(unit.lower().strip(), unit)

class RegionalSettings:
    """Regional preference settings and guidelines"""
    
    REGIONS = {
        "India (FSSAI)": {
            "authority": "FSSAI",
            "currency": "INR",
            "weight_default": "grams",
            "volume_default": "ml",
            "guidelines": {
                "sugar_limit": 5.0,  # per 100g
                "salt_limit": 120,   # mg per 100g
                "trans_fat_limit": 2.0  # % of total fat
            },
            "languages": ["hindi", "english", "tamil", "bengali"]
        },
        
        "United States (FDA)": {
            "authority": "FDA",
            "currency": "USD", 
            "weight_default": "ounces",
            "volume_default": "fl oz",
            "guidelines": {
                "sugar_limit": 50,   # per day
                "sodium_limit": 2300,  # mg per day
                "trans_fat_limit": 0   # g per serving
            },
            "languages": ["english", "spanish"]
        },
        
        "Europe (EFSA)": {
            "authority": "EFSA",
            "currency": "EUR",
            "weight_default": "grams", 
            "volume_default": "ml",
            "guidelines": {
                "sugar_limit": 90,    # g per day
                "salt_limit": 5,      # g per day
                "trans_fat_limit": 2  # % of energy intake
            },
            "languages": ["english", "french", "german", "spanish", "italian"]
        },
        
        "Australia (FSANZ)": {
            "authority": "FSANZ",
            "currency": "AUD",
            "weight_default": "grams",
            "volume_default": "ml", 
            "guidelines": {
                "sugar_limit": 90,    # g per day
                "sodium_limit": 2000, # mg per day
                "trans_fat_limit": 1  # % of energy
            },
            "languages": ["english"]
        },
        
        "Global (WHO)": {
            "authority": "WHO",
            "currency": "USD",
            "weight_default": "grams",
            "volume_default": "ml",
            "guidelines": {
                "sugar_limit": 25,    # g per day (free sugars)
                "salt_limit": 5,      # g per day
                "trans_fat_limit": 1  # % of energy
            },
            "languages": ["english", "french", "spanish", "arabic", "chinese"]
        }
    }
    
    @classmethod
    def get_region_info(cls, region: str) -> Dict[str, Any]:
        """Get information for a specific region"""
        return cls.REGIONS.get(region, cls.REGIONS["Global (WHO)"])
    
    @classmethod
    def get_available_regions(cls) -> list:
        """Get list of available regions"""
        return list(cls.REGIONS.keys())
    
    @classmethod
    def get_regional_guidelines(cls, region: str) -> Dict[str, float]:
        """Get nutritional guidelines for a region"""
        region_info = cls.get_region_info(region)
        return region_info.get("guidelines", {})

class SettingsManager:
    """Manage user settings and preferences"""
    
    def __init__(self, db_path: str = "user_settings.db"):
        self.db_path = Path(db_path)
        self.converter = UnitConverter()
        self.regional = RegionalSettings()
        self._init_database()
    
    def _init_database(self):
        """Initialize settings database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        id INTEGER PRIMARY KEY,
                        user_id TEXT DEFAULT 'default',
                        preferences TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversion_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        from_value REAL,
                        from_unit TEXT,
                        to_unit TEXT,
                        converted_value REAL,
                        cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
                logger.info("Settings database initialized")
                
        except sqlite3.Error as e:
            logger.error(f"Settings database initialization failed: {e}")
            raise
    
    def save_preferences(self, preferences: UserPreferences, user_id: str = "default") -> bool:
        """Save user preferences"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                preferences_json = json.dumps(asdict(preferences))
                
                cursor.execute("""
                    INSERT OR REPLACE INTO user_preferences (user_id, preferences)
                    VALUES (?, ?)
                """, (user_id, preferences_json))
                
                conn.commit()
                logger.info(f"Saved preferences for user: {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")
            return False
    
    def load_preferences(self, user_id: str = "default") -> UserPreferences:
        """Load user preferences"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT preferences FROM user_preferences WHERE user_id = ?",
                    (user_id,)
                )
                
                result = cursor.fetchone()
                
                if result:
                    preferences_dict = json.loads(result[0])
                    return UserPreferences(**preferences_dict)
                else:
                    # Return default preferences
                    default_prefs = UserPreferences()
                    self.save_preferences(default_prefs, user_id)
                    return default_prefs
                    
        except Exception as e:
            logger.error(f"Failed to load preferences: {e}")
            return UserPreferences()  # Return defaults on error
    
    def convert_nutrient_value(
        self, 
        value: str, 
        from_unit: str, 
        to_unit: str, 
        nutrient_type: str = "weight"
    ) -> Tuple[float, str]:
        """Convert nutrient value between units"""
        try:
            # Extract numeric value
            import re
            numeric_match = re.search(r'(\d+\.?\d*)', value.strip())
            if not numeric_match:
                return 0.0, value
            
            numeric_value = float(numeric_match.group(1))
            
            if nutrient_type == "weight":
                converted = self.converter.convert_weight(numeric_value, from_unit, to_unit)
            elif nutrient_type == "volume":
                converted = self.converter.convert_volume(numeric_value, from_unit, to_unit)
            else:
                return numeric_value, value  # No conversion for other types
            
            # Format result
            if converted >= 1000:
                return converted, f"{converted:.1f} {to_unit}"
            elif converted >= 1:
                return converted, f"{converted:.2f} {to_unit}"
            else:
                return converted, f"{converted:.3f} {to_unit}"
                
        except Exception as e:
            logger.error(f"Nutrient conversion failed: {e}")
            return 0.0, value
    
    def apply_regional_preferences(
        self, 
        analysis_result: dict, 
        user_preferences: UserPreferences
    ) -> dict:
        """Apply regional preferences to analysis results"""
        try:
            regional_info = self.regional.get_region_info(user_preferences.region)
            guidelines = regional_info.get("guidelines", {})
            
            # Update thresholds based on regional preferences
            if "evidence" in analysis_result and "nutritional_analysis" in analysis_result["evidence"]:
                for nutrient in analysis_result["evidence"]["nutritional_analysis"]:
                    nutrient_name = nutrient.get("nutrient", "").lower()
                    
                    # Apply regional guidelines
                    if "sugar" in nutrient_name and "sugar_limit" in guidelines:
                        # Update guideline text with regional limit
                        regional_limit = guidelines["sugar_limit"]
                        nutrient["guideline"] = f"{regional_info['authority']}: ≤{regional_limit}g per 100g"
                        nutrient["sources"] = [f"{regional_info['authority']} Guidelines"]
            
            # Add regional context
            if "analysis_metadata" not in analysis_result:
                analysis_result["analysis_metadata"] = {}
            
            analysis_result["analysis_metadata"]["regional_context"] = {
                "region": user_preferences.region,
                "authority": regional_info["authority"],
                "guidelines_applied": list(guidelines.keys())
            }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Failed to apply regional preferences: {e}")
            return analysis_result
    
    def convert_analysis_units(
        self, 
        analysis_result: dict, 
        target_weight_unit: str = "g",
        target_volume_unit: str = "ml"
    ) -> dict:
        """Convert units in analysis results"""
        try:
            if "evidence" not in analysis_result or "nutritional_analysis" not in analysis_result["evidence"]:
                return analysis_result
            
            for nutrient in analysis_result["evidence"]["nutritional_analysis"]:
                product_value = nutrient.get("product_value", "")
                
                # Extract current unit and convert if needed
                import re
                unit_match = re.search(r'(\d+\.?\d*)\s*([a-zA-Z]+)', product_value)
                if unit_match:
                    value, current_unit = unit_match.groups()
                    
                    # Determine if it's weight or volume based on unit
                    if current_unit.lower() in self.converter.WEIGHT_TO_GRAMS:
                        converted_value, formatted = self.convert_nutrient_value(
                            product_value, current_unit, target_weight_unit, "weight"
                        )
                        nutrient["product_value"] = formatted
                    elif current_unit.lower() in self.converter.VOLUME_TO_ML:
                        converted_value, formatted = self.convert_nutrient_value(
                            product_value, current_unit, target_volume_unit, "volume"
                        )
                        nutrient["product_value"] = formatted
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Unit conversion failed: {e}")
            return analysis_result
    
    def get_accessibility_settings(self) -> dict:
        """Get accessibility settings"""
        return {
            "high_contrast": False,
            "large_text": False,
            "screen_reader_friendly": True,
            "reduced_motion": False,
            "color_blind_friendly": True
        }
    
    def get_export_options(self) -> dict:
        """Get available export options"""
        return {
            "formats": ["CSV", "JSON", "PDF", "TXT"],
            "include_evidence": True,
            "include_images": False,
            "date_range_limit": 365,  # days
            "max_records": 1000
        }
    
    def validate_preferences(self, preferences: UserPreferences) -> Tuple[bool, list]:
        """Validate user preferences"""
        errors = []
        
        # Validate region
        if preferences.region not in self.regional.get_available_regions():
            errors.append(f"Invalid region: {preferences.region}")
        
        # Validate units
        valid_weight_units = list(self.converter.WEIGHT_TO_GRAMS.keys())
        if preferences.weight_unit not in valid_weight_units:
            errors.append(f"Invalid weight unit: {preferences.weight_unit}")
        
        valid_volume_units = list(self.converter.VOLUME_TO_ML.keys())
        if preferences.volume_unit not in valid_volume_units:
            errors.append(f"Invalid volume unit: {preferences.volume_unit}")
        
        # Validate strictness level
        if not 1 <= preferences.analysis_strictness <= 5:
            errors.append("Analysis strictness must be between 1 and 5")
        
        return len(errors) == 0, errors
    
    def get_localization_settings(self, language: str = "en") -> dict:
        """Get localization settings for different languages"""
        localizations = {
            "en": {
                "decimal_separator": ".",
                "thousands_separator": ",",
                "date_format": "%Y-%m-%d",
                "currency_symbol": "$"
            },
            "hi": {  # Hindi
                "decimal_separator": ".",
                "thousands_separator": ",",
                "date_format": "%d/%m/%Y",
                "currency_symbol": "₹"
            },
            "fr": {  # French
                "decimal_separator": ",",
                "thousands_separator": " ",
                "date_format": "%d/%m/%Y",
                "currency_symbol": "€"
            },
            "de": {  # German
                "decimal_separator": ",", 
                "thousands_separator": ".",
                "date_format": "%d.%m.%Y",
                "currency_symbol": "€"
            }
        }
        
        return localizations.get(language, localizations["en"])
    
    def cache_conversion(
        self, 
        from_value: float, 
        from_unit: str, 
        to_unit: str, 
        converted_value: float
    ) -> None:
        """Cache conversion result for performance"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Clean old cache entries (older than 24 hours)
                cursor.execute("""
                    DELETE FROM conversion_cache 
                    WHERE cached_at < datetime('now', '-24 hours')
                """)
                
                # Insert new cache entry
                cursor.execute("""
                    INSERT INTO conversion_cache 
                    (from_value, from_unit, to_unit, converted_value)
                    VALUES (?, ?, ?, ?)
                """, (from_value, from_unit, to_unit, converted_value))
                
                conn.commit()
                
        except sqlite3.Error as e:
            logger.warning(f"Failed to cache conversion: {e}")
    
    def get_cached_conversion(
        self, 
        from_value: float, 
        from_unit: str, 
        to_unit: str
    ) -> Optional[float]:
        """Get cached conversion result"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT converted_value FROM conversion_cache 
                    WHERE from_value = ? AND from_unit = ? AND to_unit = ?
                    AND cached_at > datetime('now', '-24 hours')
                """, (from_value, from_unit, to_unit))
                
                result = cursor.fetchone()
                return result[0] if result else None
                
        except sqlite3.Error as e:
            logger.warning(f"Failed to get cached conversion: {e}")
            return None

# Global settings manager instance
_settings_manager = None

def get_settings_manager() -> SettingsManager:
    """Get or create global settings manager instance"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager

def convert_units(value: str, from_unit: str, to_unit: str, unit_type: str = "weight") -> str:
    """Public interface for unit conversion"""
    manager = get_settings_manager()
    converted_value, formatted = manager.convert_nutrient_value(value, from_unit, to_unit, unit_type)
    return formatted

def get_user_preferences(user_id: str = "default") -> UserPreferences:
    """Public interface to get user preferences"""
    manager = get_settings_manager()
    return manager.load_preferences(user_id)

def save_user_preferences(preferences: UserPreferences, user_id: str = "default") -> bool:
    """Public interface to save user preferences"""
    manager = get_settings_manager()
    return manager.save_preferences(preferences, user_id)

def get_regional_info(region: str) -> dict:
    """Public interface to get regional information"""
    return RegionalSettings.get_region_info(region)

def apply_regional_settings(analysis_result: dict, region: str) -> dict:
    """Public interface to apply regional settings to analysis"""
    manager = get_settings_manager()
    preferences = UserPreferences(region=region)
    return manager.apply_regional_preferences(analysis_result, preferences)