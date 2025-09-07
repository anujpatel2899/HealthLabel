# [file name]: medical_rules.py
"""
Evidence-based nutritional guidelines from authoritative sources worldwide.
All thresholds are based on official guidelines from recognized health authorities.
"""

# Primary sources for Indian market
INDIAN_AUTHORITIES = {
    "FSSAI": "Food Safety and Standards Authority of India",
    "CDSCO": "Central Drugs Standard Control Organization",
    "AYUSH": "Ministry of Ayurveda, Yoga & Naturopathy, Unani, Siddha and Homeopathy",
    "ICMR": "Indian Council of Medical Research",
    "NIN": "National Institute of Nutrition"
}

# Global authorities
GLOBAL_AUTHORITIES = {
    "WHO": "World Health Organization",
    "FAO": "Food and Agriculture Organization",
    "CODEX": "Codex Alimentarius Commission",
    "FDA": "US Food and Drug Administration",
    "EFSA": "European Food Safety Authority",
    "FSANZ": "Food Standards Australia New Zealand",
    "FSA": "UK Food Standards Agency",
    "HC": "Health Canada",
    "CFIA": "Canadian Food Inspection Agency",
    "MHLW": "Japanese Ministry of Health, Labour and Welfare"
}

# Nutritional thresholds per 100g (unless specified otherwise)
NUTRITIONAL_THRESHOLDS = {
    "sugar": {
        "good": {"max": 5.0, "unit": "g"},
        "medium": {"max": 15.0, "unit": "g"},
        "poor": {"min": 15.1, "unit": "g"},
        "sources": [
            "WHO: Guideline: Sugars intake for adults and children (2015)",
            "FSSAI: Food Safety and Standards (Labelling and Display) Regulations, 2020"
        ]
    },
    "saturated_fat": {
        "good": {"max": 1.5, "unit": "g"},
        "medium": {"max": 5.0, "unit": "g"},
        "poor": {"min": 5.1, "unit": "g"},
        "sources": [
            "WHO: Healthy diet (2020)",
            "FDA: Daily Value on the Nutrition and Supplement Facts Labels (2020)"
        ]
    },
    "sodium": {
        "good": {"max": 120, "unit": "mg"},
        "medium": {"max": 600, "unit": "mg"},
        "poor": {"min": 601, "unit": "mg"},
        "sources": [
            "WHO: Guideline: Sodium intake for adults and children (2012)",
            "FSSAI: Food Safety and Standards (Labelling and Display) Regulations, 2020"
        ]
    },
    "fiber": {
        "good": {"min": 6.0, "unit": "g"},
        "medium": {"min": 3.0, "unit": "g"},
        "poor": {"max": 2.9, "unit": "g"},
        "sources": [
            "ICMR-NIN: Dietary Guidelines for Indians (2020)",
            "FDA: Daily Value on the Nutrition and Supplement Facts Labels (2020)"
        ]
    },
    "trans_fat": {
        "good": {"max": 0.0, "unit": "g"},
        "medium": {"max": 0.5, "unit": "g"},
        "poor": {"min": 0.6, "unit": "g"},
        "sources": [
            "WHO: REPLACE trans fat (2018)",
            "FSSAI: Limits trans fatty acids to not more than 2% (2022)"
        ]
    }
}

# Additive safety classifications
ADDITIVE_SAFETY = {
    "high_concern": {
        "artificial_sweeteners": ["Aspartame", "Saccharin", "Acesulfame K"],
        "artificial_colors": ["Tartrazine", "Sunset Yellow", "Carmoisine"],
        "preservatives": ["Sodium Benzoate", "Potassium Sorbate", "Sodium Nitrite"],
        "flavor_enhancers": ["Monosodium Glutamate (MSG)"],
        "sources": [
            "FSSAI: Food Safety and Standards (Food Products Standards and Food Additives) Regulations, 2011",
            "EFSA: Scientific Opinion on food additives",
            "FDA: Food Additive Status List"
        ]
    },
    "moderate_concern": {
        "items": ["High Fructose Corn Syrup", "Hydrogenated Oils", "Sodium Phosphates"],
        "sources": [
            "WHO: Healthy diet (2020)",
            "ICMR: Guidelines for Indians (2020)"
        ]
    }
}

# Processing level classification (NOVA system adapted)
PROCESSING_LEVELS = {
    "unprocessed_minimally_processed": {
        "examples": ["Fresh fruits", "Vegetables", "Grains", "Legumes", "Meat", "Milk", "Eggs"],
        "health_impact": "Generally beneficial",
        "sources": ["WHO: Healthy diet (2020)", "ICMR-NIN: Dietary Guidelines (2020)"]
    },
    "processed_culinary_ingredients": {
        "examples": ["Oils", "Butter", "Sugar", "Salt", "Vinegar"],
        "health_impact": "Use in moderation",
        "sources": ["WHO: Healthy diet (2020)"]
    },
    "processed_foods": {
        "examples": ["Canned vegetables", "Cheese", "Fresh bread", "Cured meats"],
        "health_impact": "Variable - check nutritional content",
        "sources": ["FAO: Food-based dietary guidelines"]
    },
    "ultra_processed_foods": {
        "examples": ["Soft drinks", "Packaged snacks", "Instant noodles", "Sweetened cereals"],
        "health_impact": "Limit consumption",
        "sources": [
            "WHO: Ultra-processed foods, diet quality, and health using the NOVA classification system (2019)",
            "ICMR: Avoid ultra-processed foods in dietary guidelines"
        ]
    }
}

# Health claim regulations
HEALTH_CLAIM_STANDARDS = {
    "nutrient_content_claims": {
        "low_fat": {"max": 3.0, "unit": "g/100g", "source": "FSSAI Regulations"},
        "low_sugar": {"max": 5.0, "unit": "g/100g", "source": "FSSAI Regulations"},
        "low_sodium": {"max": 120, "unit": "mg/100g", "source": "FSSAI Regulations"},
        "high_fiber": {"min": 6.0, "unit": "g/100g", "source": "FSSAI Regulations"}
    },
    "sources": [
        "FSSAI: Food Safety and Standards (Advertising and Claims) Regulations, 2018",
        "FDA: Food Labeling Guide",
        "EFSA: Nutrition and health claims"
    ]
}

def get_nutrient_guideline(nutrient: str, value: float) -> dict:
    """
    Get the appropriate guideline for a nutrient value
    Returns: {"rating": "Good/Medium/Poor", "guideline": "text", "sources": []}
    """
    if nutrient not in NUTRITIONAL_THRESHOLDS:
        return {
            "rating": "Unknown",
            "guideline": "No established guideline available",
            "sources": ["Guideline not established for this nutrient"]
        }
    
    thresholds = NUTRITIONAL_THRESHOLDS[nutrient]
    
    if "good" in thresholds and "max" in thresholds["good"] and value <= thresholds["good"]["max"]:
        rating = "Good"
        guideline = f"≤ {thresholds['good']['max']} {thresholds['good']['unit']}"
    elif "medium" in thresholds and "max" in thresholds["medium"] and value <= thresholds["medium"]["max"]:
        rating = "Medium"
        guideline = f"≤ {thresholds['medium']['max']} {thresholds['medium']['unit']}"
    else:
        rating = "Poor"
        if "poor" in thresholds and "min" in thresholds["poor"]:
            guideline = f"> {thresholds['poor']['min']} {thresholds['poor']['unit']}"
        else:
            guideline = "Exceeds recommended limits"
    
    return {
        "rating": rating,
        "guideline": guideline,
        "sources": thresholds["sources"]
    }

def check_additive_safety(additive_name: str) -> dict:
    """
    Check if an additive is of concern and return safety information
    """
    additive_lower = additive_name.lower()
    
    # Check high concern categories
    for category, items in ADDITIVE_SAFETY["high_concern"].items():
        if category != "sources":
            for item in items:
                if item.lower() in additive_lower:
                    return {
                        "level": "high_concern",
                        "category": category.replace("_", " ").title(),
                        "recommendation": "Avoid or limit consumption",
                        "sources": ADDITIVE_SAFETY["high_concern"]["sources"]
                    }
    
    # Check moderate concern
    for item in ADDITIVE_SAFETY["moderate_concern"]["items"]:
        if item.lower() in additive_lower:
            return {
                "level": "moderate_concern",
                "category": "Moderate Concern Additive",
                "recommendation": "Consume in moderation",
                "sources": ADDITIVE_SAFETY["moderate_concern"]["sources"]
            }
    
    return {
        "level": "low_concern",
        "category": "Generally Recognized as Safe",
        "recommendation": "No significant concerns",
        "sources": ["FDA: GRAS list", "FSSAI: Approved additives list"]
    }