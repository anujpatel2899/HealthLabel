import os
import base64
import json
import logging
from pathlib import Path
from typing import Union, Dict, Any

# Import with error handling
try:
    from crewai import Agent, Task, Crew, LLM
except ImportError as e:
    logging.error(f"CrewAI import failed: {e}")
    raise ImportError("CrewAI not installed. Run: pip install crewai")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FoodAnalyzer:
    """Centralized food analysis system using CrewAI"""
    
    def __init__(self):
        self.llm = self._initialize_llm()
        self.agent = self._create_agent()
        self._ensure_prompts_exist()

    def _initialize_llm(self) -> LLM:
        """Initialize the LLM with proper configuration for OpenAI"""
        # Check for API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables. "
                "Please set it in your .env file or environment."
            )
        
        return LLM(
            model="openai/gpt-4o-mini",
            temperature=0.1,
            max_tokens=4096
        )

    def _create_agent(self) -> Agent:
        """Create the specialized food analysis agent"""
        return Agent(
            role="Expert Food Health Analyst & Nutritionist",
            goal=(
                "Analyze food products for health impact, providing clear, evidence-based "
                "scores and insights based on established nutritional guidelines from WHO, "
                "FDA, and other health organizations."
            ),
            backstory=(
                "You are a world-renowned nutritionist with 20+ years of experience in "
                "food science and public health nutrition. You specialize in translating "
                "complex nutritional data into actionable health insights for consumers. "
                "Your analysis is always objective, scientific, and based on the latest "
                "research and international health guidelines."
            ),
            llm=self.llm,
            verbose=False,
            max_execution_time=60,
        )

    def _ensure_prompts_exist(self):
        """Ensure prompt files exist, create defaults if missing"""
        prompts_dir = Path(__file__).parent / "prompts"
        prompts_dir.mkdir(exist_ok=True)
        
        # Create default prompts if they don't exist
        default_prompts = {
            "data_analysis_prompt.txt": self._get_default_data_prompt(),
            "image_analysis_prompt.txt": self._get_default_image_prompt()
        }
        
        for filename, content in default_prompts.items():
            prompt_path = prompts_dir / filename
            if not prompt_path.exists():
                prompt_path.write_text(content)
                logger.info(f"Created default prompt: {filename}")

    def _get_default_data_prompt(self) -> str:
        """Default prompt for structured data analysis"""
        return '''Analyze this packaged food product and provide a comprehensive health assessment.

Product Data:
{product_info}

**Evaluation Criteria:**
1. **Ingredient Quality**: Analyze for whole foods vs. ultra-processed items, hidden sugars, artificial additives, and preservatives.
2. **Nutritional Profile**: Evaluate nutrients per 100g using these thresholds:
   - **Sugar**: <5g Good, 5-15g Medium, >15g Poor
   - **Sodium**: <120mg Good, 120-600mg Medium, >600mg Poor  
   - **Saturated Fat**: <1.5g Good, 1.5-5g Medium, >5g Poor
   - **Fiber**: >6g Good, 3-6g Medium, <3g Poor
3. **Processing Level**: Assess NOVA classification and health impact.

**Output Format** (JSON only):
{{
    "score": "[0-100 integer]",
    "band": "['Good'/'Medium'/'Poor']",
    "summary": "[1-2 sentence health summary]",
    "drivers": {{
        "positive": ["Up to 3 specific positive factors"],
        "negative": ["Up to 3 specific concerns"]
    }},
    "evidence": {{
        "ingredient_analysis": {{
            "key_ingredients": ["Top 5 ingredients"],
            "additives_of_concern": "List or 'None identified'"
        }},
        "nutritional_guidelines": [
            {{
                "nutrient": "Sugar",
                "product_value": "[X]g per 100g",
                "guideline": "Good <5g, Medium 5-15g, Poor >15g",
                "rating": "['Good'/'Medium'/'Poor']"
            }}
        ],
        "citations": ["WHO", "FDA", "NHS"]
    }}
}}'''

    def _get_default_image_prompt(self) -> str:
        """Default prompt for image analysis"""
        return '''Analyze this food label image and provide a comprehensive health assessment.

Steps:
1. Extract all visible ingredients from the image
2. Extract nutritional information (per 100g preferred)
3. Evaluate healthiness based on extracted data

**Output Format** (JSON only):
{{
    "score": "[0-100 integer]",
    "band": "['Good'/'Medium'/'Poor']", 
    "summary": "[1-2 sentences describing health profile]",
    "drivers": {{
        "positive": ["Specific positive factors found"],
        "negative": ["Specific concerns identified"]
    }},
    "evidence": {{
        "ingredients_found": ["All ingredients extracted"],
        "nutrients_found": {{"nutrient": "value with unit"}},
        "guidelines_used": ["Health guidelines referenced"],
        "health_concerns": ["Specific concerns if any"]
    }}
}}'''

    def load_prompt(self, filename: str) -> str:
        """Load a prompt from the prompts directory"""
        try:
            prompt_path = Path(__file__).parent / "prompts" / filename
            if not prompt_path.exists():
                logger.warning(f"Prompt file {filename} not found, using default")
                if "data" in filename:
                    return self._get_default_data_prompt()
                else:
                    return self._get_default_image_prompt()
            
            return prompt_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error loading prompt {filename}: {e}")
            raise

    def analyze_food_image(self, image_file) -> str:
        """
        Analyze a food label image using multimodal LLM
        """
        try:
            # Convert image to base64
            image_file.seek(0)
            image_data = image_file.read()
            image_b64 = base64.b64encode(image_data).decode("utf-8")
            
            # Load prompt
            prompt = self.load_prompt("image_analysis_prompt.txt")
            
            # Create analysis task
            task = Task(
                description=prompt,
                agent=self.agent,
                expected_output="Valid JSON object with health analysis results"
            )
            
            # Create and run crew
            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                verbose=False
            )
            
            result = crew.kickoff(inputs={"image_base64": image_b64})
            return self._process_result(result)
            
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return self._create_error_response(f"Image analysis error: {str(e)}")

    def analyze_food_data(self, product_data: Dict[str, Any]) -> str:
        """
        Analyze structured product data from barcode lookup
        """
        try:
            # Convert product data to formatted string
            product_info = json.dumps(product_data, indent=2)
            
            # Load and format prompt
            prompt_template = self.load_prompt("data_analysis_prompt.txt")
            prompt = prompt_template.format(product_info=product_info)
            
            # Create analysis task
            task = Task(
                description=prompt,
                agent=self.agent,
                expected_output="Valid JSON object with health analysis results"
            )
            
            # Create and run crew
            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                verbose=False
            )
            
            result = crew.kickoff()
            return self._process_result(result)
            
        except Exception as e:
            logger.error(f"Data analysis failed: {e}")
            return self._create_error_response(f"Data analysis error: {str(e)}")

def _process_result(self, result) -> str:
    """Process CrewAI result into clean JSON string"""
    try:
        # Handle different result types
        if hasattr(result, 'raw'):
            result_str = result.raw
        elif hasattr(result, 'result'):
            result_str = result.result  
        else:
            result_str = str(result)
        
        # Clean up the result string
        result_str = result_str.strip()
        
        # Remove markdown code blocks if present
        if result_str.startswith('```json'):
            result_str = result_str[7:]
        if result_str.startswith('```'):
            result_str = result_str[3:]
        if result_str.endswith('```'):
            result_str = result_str[:-3]
        
        result_str = result_str.strip()
        
        # Validate JSON
        try:
            parsed = json.loads(result_str)
            
            # FIX: Convert score from string to integer
            if 'score' in parsed and isinstance(parsed['score'], str):
                try:
                    parsed['score'] = int(parsed['score'])
                except (ValueError, TypeError):
                    parsed['score'] = 0  # Default if conversion fails
            
            # Ensure required fields exist
            required_fields = ['score', 'band', 'summary', 'drivers']
            for field in required_fields:
                if field not in parsed:
                    logger.warning(f"Missing required field: {field}")
                    # Add default values for missing fields
                    if field == 'score':
                        parsed['score'] = 0
                    elif field == 'band':
                        parsed['band'] = 'Unknown'
                    elif field == 'summary':
                        parsed['summary'] = 'No summary available'
                    elif field == 'drivers':
                        parsed['drivers'] = {'positive': [], 'negative': []}
            
            return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in result: {e}")
            return self._create_error_response("AI returned invalid JSON format")
            
    except Exception as e:
        logger.error(f"Result processing failed: {e}")
        return self._create_error_response(f"Result processing error: {str(e)}")
    
    def _create_error_response(self, error_message: str) -> str:
        """Create a standardized error response"""
        error_response = {
            "score": 0,
            "band": "Unknown",
            "summary": f"Analysis failed: {error_message}",
            "drivers": {
                "positive": [],
                "negative": ["Analysis error occurred"]
            },
            "evidence": {
                "error": error_message,
                "status": "failed"
            }
        }
        return json.dumps(error_response)

# Global analyzer instance
_analyzer = None

def get_analyzer() -> FoodAnalyzer:
    """Get or create global analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = FoodAnalyzer()
    return _analyzer

def analyze_food_image(image_file):
    """Analyze food label image"""
    analyzer = get_analyzer()
    return analyzer.analyze_food_image(image_file)

def analyze_food_data(product_data: Dict[str, Any]):
    """Analyze structured product data"""
    analyzer = get_analyzer()
    return analyzer.analyze_food_data(product_data)

def test_analyzer():
    """Test the analyzer with sample data"""
    test_data = {
        "name": "Test Product",
        "ingredients": ["Water", "Sugar", "Natural Flavors"],
        "nutrients": {
            "calories": "150 kcal",
            "sugars": "25 g",
            "sodium": "200 mg",
            "fiber": "2 g"
        }
    }
    
    try:
        analyzer = get_analyzer()
        result = analyzer.analyze_food_data(test_data)
        print("Test analysis result:")
        print(json.dumps(json.loads(result), indent=2))
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_analyzer()