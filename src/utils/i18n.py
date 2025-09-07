"""
Utilities for internationalization and unit conversions in Health Rater.
"""

import locale
from typing import Dict, Any

# Supported languages
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'fr': 'Français',
    'es': 'Español',
    'de': 'Deutsch'
}

# Translation dictionaries for UI elements
TRANSLATIONS = {
    # English translations (default)
    'en': {
        'app_title': 'Health Rater - Nutrition Score Calculator',
        'header': 'Health Rater',
        'subheader': 'Calculate the health score of food products using the Nutri-Score algorithm.',
        'input_methods': 'Input Methods',
        'barcode_tab': 'Barcode',
        'photo_tab': 'Product Photo',
        'text_tab': 'Text Input',
        'enter_barcode': 'Enter Barcode Number',
        'barcode_placeholder': 'Enter barcode number...',
        'upload_barcode': 'Or Upload Barcode Image',
        'upload_photo': 'Upload Product Label Photo',
        'enter_product_info': 'Enter Product Information',
        'text_placeholder': 'Enter product information (e.g., nutrition facts, ingredients)...',
        'calculate_button': 'Calculate Health Score',
        'results': 'Results',
        'results_placeholder': 'Enter product information and click \'Calculate Health Score\' to see results.',
        'evidence': 'Evidence & Detailed Analysis',
        'evidence_placeholder': 'Detailed analysis will appear here after calculation.',
        'history': 'Search History',
        'history_placeholder': 'Your search history will appear here.',
        'compare': 'Compare Products',
        'compare_placeholder': 'Select products from your history to compare.',
        'export': 'Export/Share',
        'settings': 'Settings',
        'language': 'Language',
        'unit_system': 'Unit System',
        'metric': 'Metric (g, ml)',
        'imperial': 'Imperial (oz, fl oz)',
        'accessibility': 'Accessibility',
        'high_contrast': 'High Contrast Mode',
        'large_text': 'Large Text',
        'search_history': 'Search History',
        'clear_history': 'Clear History',
        'no_results': 'No results found.',
        'error_processing': 'Error processing request:',
        'product_name': 'Product Name',
        'brand': 'Brand',
        'source': 'Source',
        'confidence': 'Confidence',
        'nutri_score': 'Nutri-Score',
        'health_score': 'Health Score (0-100)',
        'nutrition_data': 'Nutrition Data',
        'per_100g': 'per 100g/ml',
        'nutrient': 'Nutrient',
        'value': 'Value',
        'unit': 'Unit',
        'energy': 'Energy',
        'sugars': 'Sugars',
        'saturated_fat': 'Saturated Fat',
        'salt': 'Salt',
        'fiber': 'Fiber',
        'protein': 'Protein',
        'fruits_veg_nuts': 'Fruits/Veg/Nuts',
        'calculation': 'Score Calculation Breakdown',
        'component': 'Component',
        'points': 'Points',
        'impact': 'Impact',
        'positive': 'Positive',
        'negative': 'Negative',
        'sources': 'Sources & References',
        'processing_log': 'Processing Log',
        'show_log': 'Show Processing Log',
        'hide_log': 'Hide Processing Log',
        'share': 'Share Result',
        'compare_selected': 'Compare Selected',
        'export_pdf': 'Export as PDF',
        'export_image': 'Export as Image',
        'export_csv': 'Export Data as CSV',
        'add_to_comparison': 'Add to Comparison',
        'remove_from_comparison': 'Remove from Comparison',
        'comparison_title': 'Product Comparison',
        'no_products_selected': 'No products selected for comparison.',
        'select_products': 'Select products from your history to compare.',
        'drag_drop': 'Drag and Drop or',
        'select_file': 'Select a File',
        'uploaded': 'Uploaded:',
        'detected_barcode': 'Detected Barcode:',
        'no_barcode': 'None',
        'error': 'Error'
    },
    
    # French translations
    'fr': {
        'app_title': 'Évaluateur de Santé - Calculateur de Score Nutritionnel',
        'header': 'Évaluateur de Santé',
        'subheader': 'Calculez le score de santé des produits alimentaires en utilisant l\'algorithme Nutri-Score.',
        'input_methods': 'Méthodes d\'entrée',
        'barcode_tab': 'Code-barres',
        'photo_tab': 'Photo du Produit',
        'text_tab': 'Saisie de Texte',
        'enter_barcode': 'Entrez le Numéro de Code-barres',
        'barcode_placeholder': 'Entrez le numéro de code-barres...',
        'upload_barcode': 'Ou Téléchargez une Image de Code-barres',
        'upload_photo': 'Téléchargez une Photo d\'Étiquette de Produit',
        'enter_product_info': 'Entrez les Informations du Produit',
        'text_placeholder': 'Entrez les informations du produit (ex: valeurs nutritionnelles, ingrédients)...',
        'calculate_button': 'Calculer le Score de Santé',
        'results': 'Résultats',
        'results_placeholder': 'Entrez les informations du produit et cliquez sur \'Calculer le Score de Santé\' pour voir les résultats.',
        'evidence': 'Preuves et Analyse Détaillée',
        'evidence_placeholder': 'L\'analyse détaillée apparaîtra ici après le calcul.',
        'history': 'Historique des Recherches',
        'history_placeholder': 'Votre historique de recherche apparaîtra ici.',
        'compare': 'Comparer les Produits',
        'compare_placeholder': 'Sélectionnez des produits de votre historique pour comparer.',
        'export': 'Exporter/Partager',
        'settings': 'Paramètres',
        'language': 'Langue',
        'unit_system': 'Système d\'Unités',
        'metric': 'Métrique (g, ml)',
        'imperial': 'Impérial (oz, fl oz)',
        'accessibility': 'Accessibilité',
        'high_contrast': 'Mode Contraste Élevé',
        'large_text': 'Texte Large',
        'search_history': 'Rechercher dans l\'Historique',
        'clear_history': 'Effacer l\'Historique',
        'no_results': 'Aucun résultat trouvé.',
        'error_processing': 'Erreur de traitement de la demande:',
        'product_name': 'Nom du Produit',
        'brand': 'Marque',
        'source': 'Source',
        'confidence': 'Confiance',
        'nutri_score': 'Nutri-Score',
        'health_score': 'Score de Santé (0-100)',
        'nutrition_data': 'Données Nutritionnelles',
        'per_100g': 'pour 100g/ml',
        'nutrient': 'Nutriment',
        'value': 'Valeur',
        'unit': 'Unité',
        'energy': 'Énergie',
        'sugars': 'Sucres',
        'saturated_fat': 'Graisses Saturées',
        'salt': 'Sel',
        'fiber': 'Fibres',
        'protein': 'Protéines',
        'fruits_veg_nuts': 'Fruits/Légumes/Noix',
        'calculation': 'Détail du Calcul du Score',
        'component': 'Composant',
        'points': 'Points',
        'impact': 'Impact',
        'positive': 'Positif',
        'negative': 'Négatif',
        'sources': 'Sources et Références',
        'processing_log': 'Journal de Traitement',
        'show_log': 'Afficher le Journal de Traitement',
        'hide_log': 'Masquer le Journal de Traitement',
        'share': 'Partager le Résultat',
        'compare_selected': 'Comparer la Sélection',
        'export_pdf': 'Exporter en PDF',
        'export_image': 'Exporter en Image',
        'export_csv': 'Exporter les Données en CSV',
        'add_to_comparison': 'Ajouter à la Comparaison',
        'remove_from_comparison': 'Retirer de la Comparaison',
        'comparison_title': 'Comparaison de Produits',
        'no_products_selected': 'Aucun produit sélectionné pour la comparaison.',
        'select_products': 'Sélectionnez des produits de votre historique pour comparer.',
        'drag_drop': 'Glissez-déposez ou',
        'select_file': 'Sélectionnez un Fichier',
        'uploaded': 'Téléchargé:',
        'detected_barcode': 'Code-barres Détecté:',
        'no_barcode': 'Aucun',
        'error': 'Erreur'
    },
    
    # Spanish translations (add more as needed)
    'es': {
        'app_title': 'Evaluador de Salud - Calculadora de Puntuación Nutricional',
        'header': 'Evaluador de Salud',
        'subheader': 'Calcule la puntuación de salud de productos alimenticios utilizando el algoritmo Nutri-Score.',
        'input_methods': 'Métodos de Entrada',
        'barcode_tab': 'Código de Barras',
        'photo_tab': 'Foto del Producto',
        'text_tab': 'Entrada de Texto',
        'calculate_button': 'Calcular Puntuación de Salud',
        'results': 'Resultados',
        'nutri_score': 'Nutri-Score',
        'product_name': 'Nombre del Producto',
        'error': 'Error'
        # Add more translations as needed
    },
    
    # German translations (add more as needed)
    'de': {
        'app_title': 'Gesundheitsbewertung - Nährwert-Score-Rechner',
        'header': 'Gesundheitsbewertung',
        'subheader': 'Berechnen Sie den Gesundheitsscore von Lebensmitteln mit dem Nutri-Score-Algorithmus.',
        'input_methods': 'Eingabemethoden',
        'barcode_tab': 'Barcode',
        'photo_tab': 'Produktfoto',
        'text_tab': 'Texteingabe',
        'calculate_button': 'Gesundheitsscore berechnen',
        'results': 'Ergebnisse',
        'nutri_score': 'Nutri-Score',
        'product_name': 'Produktname',
        'error': 'Fehler'
        # Add more translations as needed
    }
}

# Unit conversion factors
UNIT_CONVERSIONS = {
    'g_to_oz': 0.03527396,  # 1 gram = 0.03527396 ounces
    'ml_to_floz': 0.033814,  # 1 milliliter = 0.033814 fluid ounces
    'kcal_to_cal': 1,        # 1 kcal = 1 Calorie (nutritional calorie)
    'kj_to_kcal': 0.239006   # 1 kilojoule = 0.239006 kilocalories
}

def get_translation(key: str, lang: str = 'en') -> str:
    """Get a translated string for the given key and language."""
    if lang not in SUPPORTED_LANGUAGES:
        lang = 'en'  # Fallback to English
    
    translations = TRANSLATIONS.get(lang, TRANSLATIONS['en'])
    return translations.get(key, TRANSLATIONS['en'].get(key, key))

def convert_units(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a value from one unit to another."""
    if from_unit == to_unit:
        return value
    
    conversion_key = f"{from_unit}_to_{to_unit}"
    conversion_factor = UNIT_CONVERSIONS.get(conversion_key)
    
    if conversion_factor is None:
        # If direct conversion not available, try reverse
        conversion_key = f"{to_unit}_to_{from_unit}"
        conversion_factor = UNIT_CONVERSIONS.get(conversion_key)
        
        if conversion_factor is None:
            # No conversion available
            return value
        
        # Use reciprocal for reverse conversion
        return value / conversion_factor
    
    return value * conversion_factor

def format_nutrition_data(nutrition_data: Dict[str, Any], unit_system: str = 'metric', lang: str = 'en') -> Dict[str, Dict[str, Any]]:
    """Format nutrition data with proper units based on the selected unit system."""
    formatted_data = {}
    
    # Define unit mapping based on unit system
    units = {
        'metric': {
            'weight': 'g',
            'volume': 'ml',
            'energy': 'kcal'
        },
        'imperial': {
            'weight': 'oz',
            'volume': 'fl oz',
            'energy': 'cal'
        }
    }
    
    # Get the appropriate units
    system_units = units.get(unit_system, units['metric'])
    
    # Map nutrition keys to unit types
    unit_types = {
        'energy_kcal': 'energy',
        'sugars_g': 'weight',
        'saturated_fat_g': 'weight',
        'salt_g': 'weight',
        'fiber_g': 'weight',
        'protein_g': 'weight',
        'fruits_veg_nuts_percent': 'percent'  # Percentage doesn't change
    }
    
    # Format each nutrition value with appropriate unit
    for key, value in nutrition_data.items():
        unit_type = unit_types.get(key, None)
        
        if unit_type is None:
            # Skip if we don't know the unit type
            formatted_data[key] = {'value': value, 'unit': ''}
            continue
        
        if unit_type == 'percent':
            # Percentages don't need conversion
            formatted_data[key] = {'value': value, 'unit': '%'}
            continue
        
        # Get source and target units from the key and unit system
        source_unit = key.split('_')[-1]  # e.g., 'g' from 'sugars_g'
        target_unit = system_units[unit_type]
        
        # Convert value if needed
        if source_unit != target_unit:
            converted_value = convert_units(value, source_unit, target_unit)
        else:
            converted_value = value
        
        # Format for display
        formatted_data[key] = {
            'value': round(converted_value, 2),
            'unit': target_unit
        }
    
    return formatted_data

def get_locale_for_language(lang: str) -> str:
    """Get the appropriate locale string for a language code."""
    locale_map = {
        'en': 'en_US.UTF-8',
        'fr': 'fr_FR.UTF-8',
        'es': 'es_ES.UTF-8',
        'de': 'de_DE.UTF-8'
    }
    return locale_map.get(lang, 'en_US.UTF-8')

def set_language_locale(lang: str) -> None:
    """Set the locale based on the selected language."""
    try:
        locale_str = get_locale_for_language(lang)
        locale.setlocale(locale.LC_ALL, locale_str)
    except locale.Error:
        # Fallback if the specific locale is not available
        try:
            # Try with just the language code
            locale.setlocale(locale.LC_ALL, lang)
        except locale.Error:
            # If all else fails, use system default
            locale.setlocale(locale.LC_ALL, '')
