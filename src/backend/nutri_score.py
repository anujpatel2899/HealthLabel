import logging
import json
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NutriScoreCalculator:
    """Class to calculate the Nutri-Score of a food product based on the 2024 algorithm."""
    
    def __init__(self, nutri_score_json_path=None):
        """
        Initialize the NutriScore calculator with criteria from JSON file.
        
        Args:
            nutri_score_json_path: Path to the JSON file containing Nutri-Score criteria
        """
        if nutri_score_json_path is None:
            # Default to the project's JSON file
            this_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(this_dir, '..', '..'))
            nutri_score_json_path = os.path.join(project_root, 'nutri_score.json')
        
        self.criteria = self._load_criteria(nutri_score_json_path)
        self._calculation_cache = {}
        logger.info("NutriScore calculator initialized with criteria from: %s", nutri_score_json_path)
    
    def _load_criteria(self, json_path):
        """Load Nutri-Score criteria from JSON file."""
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            return data.get('nutri_score_criteria_2024', {})
        except Exception as e:
            logger.error(f"Error loading Nutri-Score criteria: {str(e)}")
            return {}
    
    def _parse_threshold(self, threshold_str):
        """Parse threshold string to get numeric value."""
        try:
            # Handle various threshold formats
            if '≤' in threshold_str:
                value_str = threshold_str.split('≤')[1].split()[0]
                # Remove unit suffixes and percentage sign
                value_str = ''.join(c for c in value_str if c.isdigit() or c == '.')
                return float(value_str)
            elif '>' in threshold_str:
                value_str = threshold_str.split('>')[1].split()[0]
                # Remove unit suffixes and percentage sign
                value_str = ''.join(c for c in value_str if c.isdigit() or c == '.')
                return float(value_str)
            elif '-' in threshold_str:
                parts = threshold_str.split('-')
                values = []
                for part in parts:
                    # Extract numeric part and remove percentage sign if present
                    numeric_part = ''.join(c for c in part if c.isdigit() or c == '.')
                    values.append(float(numeric_part))
                # Always return a list of length 2 for range thresholds
                if len(values) == 2:
                    return values
                # If there are more than 2 values (e.g., triplets), use the first and last
                elif len(values) > 2:
                    logger.warning(f"Found {len(values)} values in threshold range: {threshold_str}. Using first and last.")
                    return [values[0], values[-1]]
                # If there's only 1 value, duplicate it to create a range
                elif len(values) == 1:
                    return [values[0], values[0]]
                else:
                    return None
            else:
                return None
        except Exception as e:
            logger.error(f"Error parsing threshold: {threshold_str}, {str(e)}")
            return None
    
    def _get_points_for_component(self, component_name, value, is_negative=True):
        """
        Calculate points for a specific nutritional component.
        
        Args:
            component_name: Name of the component (e.g., 'energy_calories')
            value: Nutritional value to evaluate
            is_negative: Whether this is a negative component (adds points) or positive (subtracts points)
            
        Returns:
            int: Points assigned for this component
        """
        components = self.criteria.get('negative_components', {}) if is_negative else self.criteria.get('positive_components', {})
        component = components.get(component_name, {})
        
        if not component:
            logger.warning(f"Component not found: {component_name}")
            return 0
            
        thresholds = component.get('thresholds', {})
        max_points = component.get('max_points', 0)
        
        # Special handling for certain components
        if component_name == 'energy_calories' and 'conversion_note' in component:
            # Convert kcal to kJ if needed
            if value < 1000:  # Assuming it's in kcal if less than 1000
                value = value * 4.184  # 1 kcal = 4.184 kJ
        
        # Iterate through thresholds to find the correct point value
        for points in range(max_points + 1):
            threshold_key = f"{points}_points"
            if threshold_key not in thresholds:
                continue
                
            threshold_str = thresholds[threshold_key]
            parsed = self._parse_threshold(threshold_str)
            
            if parsed is None:
                continue
                
            if isinstance(parsed, list):
                # Range threshold (e.g., "1.1-2.0g")
                min_val, max_val = parsed
                if min_val <= value <= max_val:
                    return points
            elif '≤' in threshold_str and value <= parsed:
                return points
            elif '>' in threshold_str and value > parsed:
                return points
        
        # If we get here, use the maximum points if exceeding all thresholds
        return max_points
    
    def _cache_key(self, nutrition_data, is_beverage, is_cheese, contains_sweeteners):
        """Generate a cache key from the input parameters."""
        # Convert nutrition_data to a tuple of sorted items for hashability
        nutrition_items = tuple(sorted((k, v) for k, v in nutrition_data.items()))
        return (nutrition_items, is_beverage, is_cheese, contains_sweeteners)
    
    def calculate_score(self, nutrition_data, is_beverage=False, is_cheese=False, contains_sweeteners=False):
        """
        Calculate the Nutri-Score for a food product with caching for better performance.
        
        Args:
            nutrition_data: Dictionary containing nutritional values per 100g/ml
                Required keys: 'energy_kcal', 'sugars_g', 'saturated_fat_g', 'salt_g', 
                               'fiber_g', 'protein_g', 'fruits_veg_nuts_percent'
            is_beverage: Whether the product is a beverage
            is_cheese: Whether the product is cheese (special protein scoring)
            contains_sweeteners: Whether the product contains artificial sweeteners
            
        Returns:
            dict: Calculation results including score, grade, and detailed breakdown
        """
        # Check cache first using a hashable representation
        cache_key = self._cache_key(nutrition_data, is_beverage, is_cheese, contains_sweeteners)
        if cache_key in self._calculation_cache:
            logger.debug("Cache hit for Nutri-Score calculation")
            return self._calculation_cache[cache_key]
        
        # Initialize counters
        negative_points = 0
        positive_points = 0
        calculation_log = []
        
        # Calculate negative points
        for component, key in [
            ('energy_calories', 'energy_kcal'),
            ('sugars', 'sugars_g'),
            ('saturated_fatty_acids', 'saturated_fat_g'),
            ('salt_sodium', 'salt_g')
        ]:
            if key in nutrition_data:
                points = self._get_points_for_component(component, nutrition_data[key], is_negative=True)
                negative_points += points
                calculation_log.append({
                    "component": component,
                    "value": nutrition_data[key],
                    "points": points,
                    "is_negative": True
                })
        
        # Special consideration for non-nutritive sweeteners
        if contains_sweeteners:
            # Apply penalty according to 2024 rules
            sweetener_penalty = 2  # Example penalty value, adjust according to actual rules
            negative_points += sweetener_penalty
            calculation_log.append({
                "component": "non_nutritive_sweeteners",
                "value": "Present",
                "points": sweetener_penalty,
                "is_negative": True,
                "note": "Additional penalty for artificial sweeteners (2024 update)"
            })
        
        # Calculate positive points
        for component, key in [
            ('fiber', 'fiber_g'),
            ('protein', 'protein_g')
        ]:
            if key in nutrition_data:
                # Special rule for cheese products
                if component == 'protein' and is_cheese:
                    points = 7  # Maximum protein points for cheese
                    calculation_log.append({
                        "component": component,
                        "value": nutrition_data[key],
                        "points": points,
                        "is_negative": False,
                        "note": "Special rule: Cheese products receive full protein points"
                    })
                else:
                    points = self._get_points_for_component(component, nutrition_data[key], is_negative=False)
                    positive_points += points
                    calculation_log.append({
                        "component": component,
                        "value": nutrition_data[key],
                        "points": points,
                        "is_negative": False
                    })
        
        # Calculate fruits, vegetables, legumes, nuts points
        if 'fruits_veg_nuts_percent' in nutrition_data:
            component = 'fruits_vegetables_legumes_nuts'
            value = nutrition_data['fruits_veg_nuts_percent']
            points = self._get_points_for_component(component, value, is_negative=False)
            positive_points += points
            calculation_log.append({
                "component": component,
                "value": value,
                "points": points,
                "is_negative": False
            })
        
        # Calculate final score
        final_score = negative_points - positive_points
        
        # Determine grade based on food type
        grade_thresholds = self.criteria.get('final_grade_assignment', {})
        thresholds = grade_thresholds.get('beverages', {}) if is_beverage else grade_thresholds.get('solid_foods', {})
        
        grade = 'E'  # Default to worst grade
        for g, threshold_str in thresholds.items():
            # Parse the threshold
            if '≤' in threshold_str:
                value = float(threshold_str.split('≤')[1].split()[0])
                if final_score <= value:
                    grade = g
                    break
            elif '≥' in threshold_str:
                value = float(threshold_str.split('≥')[1].split()[0])
                if final_score >= value:
                    grade = g
                    break
            elif 'to' in threshold_str:
                parts = threshold_str.split('to')
                min_val = float(parts[0].strip())
                max_val = float(parts[1].split()[0].strip())
                if min_val <= final_score <= max_val:
                    grade = g
                    break
        
        # Convert to 0-100 score (100 being best health score)
        # A = 80-100, B = 60-79, C = 40-59, D = 20-39, E = 0-19
        score_map = {'A': 90, 'B': 70, 'C': 50, 'D': 30, 'E': 10}
        normalized_score = score_map.get(grade, 0)
        
        # Create result dictionary
        result = {
            "raw_score": final_score,
            "normalized_score": normalized_score,
            "grade": grade,
            "calculation_log": calculation_log,
            "is_beverage": is_beverage,
            "is_cheese": is_cheese,
            "contains_sweeteners": contains_sweeteners,
            "sources": [
                "Nutri-Score 2024 Algorithm",
                "EU Regulation 1169/2011 (INCO)"
            ],
            "explanation": self._generate_explanation(final_score, grade, calculation_log, is_beverage)
        }
        
        # Save to cache
        self._calculation_cache[cache_key] = result
        
        # Limit cache size to avoid memory issues
        if len(self._calculation_cache) > 128:
            # Remove oldest item (simplistic approach)
            try:
                self._calculation_cache.pop(next(iter(self._calculation_cache)))
            except (StopIteration, KeyError):
                pass
                
        logger.info(f"Calculated Nutri-Score: {grade} (raw score: {final_score}, normalized: {normalized_score})")
        return result
    
    def _generate_explanation(self, score, grade, calculation_log, is_beverage):
        """Generate a plain-language explanation of the score."""
        # Sort components by points contribution
        negative_components = [c for c in calculation_log if c['is_negative']]
        positive_components = [c for c in calculation_log if not c['is_negative']]
        
        negative_components.sort(key=lambda x: x['points'], reverse=True)
        positive_components.sort(key=lambda x: x['points'], reverse=True)
        
        # Identify main contributors
        main_negative = negative_components[:2] if negative_components else []
        main_positive = positive_components[:2] if positive_components else []
        
        # Generate explanation
        product_type = "beverage" if is_beverage else "food product"
        explanation = f"This {product_type} received a Nutri-Score grade of {grade}."
        
        # Add information about negative contributors
        if main_negative:
            explanation += "\n\nMain negative factors:"
            for comp in main_negative:
                component_name = comp['component'].replace('_', ' ').title()
                explanation += f"\n- {component_name}: {comp['value']} ({comp['points']} points)"
        
        # Add information about positive contributors
        if main_positive:
            explanation += "\n\nMain positive factors:"
            for comp in main_positive:
                component_name = comp['component'].replace('_', ' ').title()
                explanation += f"\n- {component_name}: {comp['value']} ({comp['points']} points)"
        
        # Add general interpretation
        if grade in ['A', 'B']:
            explanation += f"\n\nOverall, this is considered a relatively healthy {product_type} according to the Nutri-Score system."
        elif grade == 'C':
            explanation += f"\n\nOverall, this {product_type} falls in the middle range of the Nutri-Score system."
        else:
            explanation += f"\n\nOverall, this {product_type} received a lower health rating according to the Nutri-Score system."
        
        explanation += "\n\nThe Nutri-Score is based on the 2024 algorithm, which evaluates both negative components (calories, sugars, saturated fat, salt) and positive components (fiber, protein, fruits/vegetables/nuts)."
        
        return explanation
