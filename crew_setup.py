from crewai import Agent, Task, Crew, LLM
import base64
import json

# --- LLM Setup ---
# Using Gemini 2.0 Flash for multimodal capabilities (text + image)
llm = LLM(
    model="gemini/gemini-2.0-flash",  # Supports both text and image inputs
    temperature=0.1,  # Low temperature for consistent analysis
)

# --- Agents ---
# Multi-modal agent that can handle both text data and images
food_analyzer_agent = Agent(
    role="Food Health Analyst & Nutritionist",
    goal="Analyze food products for health impact and provide evidence-based scores",
    backstory="""You are an expert nutritionist with 20 years of experience in food science 
    and public health. You specialize in analyzing packaged foods, understanding their 
    ingredients, nutritional profiles, and health implications. You always provide 
    evidence-based assessments using scientific literature and established nutrition guidelines.""",
    llm=llm,
    verbose=True
)

# --- Helper Functions ---
def analyze_food_image(image_file):
    """
    Analyzes an uploaded food label image using multimodal LLM.
    Extracts ingredients, nutrients, and provides health analysis.
    """
    # Reset file pointer and read image
    image_file.seek(0)
    image_bytes = image_file.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    
    # Task for image analysis
    image_analysis_task = Task(
        description="""
        Analyze this food label image and provide a comprehensive health assessment.
        
        Steps:
        1. Extract all visible ingredients from the image
        2. Extract all nutritional information (per 100g/serving)
        3. Evaluate the healthiness based on:
           - Ingredient quality (whole foods vs processed)
           - Sugar content (WHO recommends <25g/day)
           - Sodium levels (WHO recommends <2000mg/day)
           - Saturated fat (<10% of calories)
           - Fiber content (>3g per serving is good)
           - Protein quality and quantity
           - Presence of artificial additives/preservatives
           - Allergens and controversial ingredients
        
        Output MUST be valid JSON with this exact structure:
        {
            "score": [0-100 integer, where 100 is healthiest],
            "band": ["Good" if score>70, "Medium" if 40-70, "Poor" if <40],
            "summary": "[1-2 sentences describing overall healthiness]",
            "drivers": [
                "[Key factor 1 affecting health score]",
                "[Key factor 2]",
                "[Up to 5 key factors total]"
            ],
            "evidence": {
                "ingredients_found": ["list of ingredients extracted"],
                "nutrients_found": {"nutrient": "value with unit"},
                "guidelines_used": ["WHO sugar guidelines", "FDA sodium limits", etc],
                "health_concerns": ["specific concerns if any"]
            }
        }
        
        Base the score on scientific nutrition guidelines and evidence.
        """,
        agent=food_analyzer_agent,
        expected_output="Valid JSON with score, band, summary, drivers, and evidence",
        context={"image_base64": image_b64}
    )
    
    crew = Crew(
        agents=[food_analyzer_agent],
        tasks=[image_analysis_task],
        verbose=True
    )
    
    result = crew.kickoff(inputs={"image_base64": image_b64})
    return result

def analyze_food_data(product_data):
    """
    Analyzes structured product data (from barcode lookup) and provides health assessment.
    """
    # Prepare input data
    ingredients = product_data.get("ingredients", [])
    nutrients = product_data.get("nutrients", {})
    product_name = product_data.get("name", "Unknown Product")
    
    # Create a formatted input string
    input_text = f"""
    Product: {product_name}
    
    Ingredients: {', '.join(ingredients) if ingredients else 'Not available'}
    
    Nutrition Facts:
    {json.dumps(nutrients, indent=2) if nutrients else 'Not available'}
    """
    
    # Task for data analysis
    data_analysis_task = Task(
        description="""
        Analyze this packaged food product and provide a comprehensive health assessment.
        
        Evaluation criteria:
        1. Ingredient Quality:
           - Whole foods vs ultra-processed ingredients
           - Artificial additives, colors, preservatives
           - Hidden sugars (corn syrup, dextrose, etc.)
           - Quality of protein sources
        
        2. Nutritional Profile (per 100g):
           - Sugar: <5g excellent, 5-15g moderate, >15g poor
           - Sodium: <120mg excellent, 120-600mg moderate, >600mg poor
           - Saturated fat: <1.5g excellent, 1.5-5g moderate, >5g poor
           - Fiber: >6g excellent, 3-6g good, <3g poor
           - Protein: Consider quality and quantity
        
        3. Health Impact:
           - Risk factors for chronic diseases
           - Beneficial nutrients present
           - Overall processing level (NOVA classification)
        
        Output MUST be valid JSON with this exact structure:
        {
            "score": [0-100 integer based on overall healthiness],
            "band": ["Good" if score>70, "Medium" if 40-70, "Poor" if <40],
            "summary": "[1-2 sentences with specific details about THIS product]",
            "drivers": [
                "[Specific health factor 1 with detail]",
                "[Specific health factor 2 with detail]",
                "[3-5 specific factors total]"
            ],
            "evidence": {
                "nutritional_analysis": {
                    "positive_aspects": ["list positive nutritional elements"],
                    "negative_aspects": ["list concerning nutritional elements"]
                },
                "ingredient_concerns": ["specific problematic ingredients if any"],
                "health_guidelines": ["WHO/FDA guidelines applied"],
                "nova_classification": "[1-4, where 4 is ultra-processed]"
            }
        }
        
        Be specific and mention actual values from the product data.
        Base scoring on established nutritional science and guidelines.
        """,
        agent=food_analyzer_agent,
        expected_output="Valid JSON with detailed health analysis"
    )
    
    crew = Crew(
        agents=[food_analyzer_agent],
        tasks=[data_analysis_task],
        verbose=True
    )
    
    result = crew.kickoff(inputs={"product_info": input_text})
    return result

def normalize_product_data(raw_data):
    """
    Helper function to normalize data from different sources into standard format.
    """
    normalized = {
        "ingredients": [],
        "nutrients": {}
    }
    
    # Handle different data formats
    if isinstance(raw_data, dict):
        # Extract ingredients
        if "ingredients" in raw_data:
            normalized["ingredients"] = raw_data["ingredients"]
        elif "ingredients_text" in raw_data:
            # Parse comma-separated ingredients
            normalized["ingredients"] = [
                ing.strip() 
                for ing in raw_data["ingredients_text"].split(",")
            ]
        
        # Extract nutrients
        if "nutrients" in raw_data:
            normalized["nutrients"] = raw_data["nutrients"]
        elif "nutriments" in raw_data:
            # OpenFoodFacts format
            nutriments = raw_data["nutriments"]
            normalized["nutrients"] = {
                "energy": nutriments.get("energy-kcal_100g", "N/A"),
                "fat": f"{nutriments.get('fat_100g', 'N/A')}g",
                "saturated_fat": f"{nutriments.get('saturated-fat_100g', 'N/A')}g",
                "carbohydrates": f"{nutriments.get('carbohydrates_100g', 'N/A')}g",
                "sugars": f"{nutriments.get('sugars_100g', 'N/A')}g",
                "fiber": f"{nutriments.get('fiber_100g', 'N/A')}g",
                "proteins": f"{nutriments.get('proteins_100g', 'N/A')}g",
                "salt": f"{nutriments.get('salt_100g', 'N/A')}g",
                "sodium": f"{nutriments.get('sodium_100g', 'N/A')}mg"
            }
    
    return normalized