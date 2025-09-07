# [file name]: crew_setup.py
import os
import base64
import json
import logging
from pathlib import Path
from typing import Union, Dict, Any, Optional, List
import traceback
from datetime import datetime

# Import medical rules
try:
    from medical_rules import (
        NUTRITIONAL_THRESHOLDS,
        ADDITIVE_SAFETY,
        PROCESSING_LEVELS,
        get_nutrient_guideline,
        check_additive_safety,
        INDIAN_AUTHORITIES,
        GLOBAL_AUTHORITIES
    )
except ImportError:
    logging.warning("Medical rules module not found. Using fallback thresholds.")

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
    """Enhanced food analysis system with confidence scoring and robust error handling"""
    
    def __init__(self):
        self.llm = self._initialize_llm()
        self.agent = self._create_agent()
        self._ensure_prompts_exist()
        self.analysis_log = []  # Track analysis attempts for debugging

    def _initialize_llm(self) -> LLM:
        """Initialize the LLM with proper configuration"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")
        
        return LLM(
            model="openai/gpt-4o-mini",
            temperature=0.1,
            max_tokens=4096
        )

    def _create_agent(self) -> Agent:
        """Create the specialized food analysis agent with enhanced capabilities"""
        return Agent(
            role="Senior Evidence-Based Food Health Analyst",
            goal=(
                "Provide comprehensive, evidence-based health assessments of food products "
                "using only authoritative medical and nutritional guidelines. Include "
                "confidence scores for all assessments and clearly identify data limitations."
            ),
            backstory=(
                "You are a senior clinical nutritionist and food scientist with 15+ years "
                "of experience in evidence-based food analysis. You strictly adhere to "
                "established guidelines from WHO, FSSAI, FDA, EFSA, and other recognized "
                "health authorities. You never speculate beyond available evidence and "
                "always provide confidence scores for your assessments. Your analysis "
                "includes detailed reasoning for each conclusion with proper citations."
            ),
            llm=self.llm,
            verbose=False,
            max_execution_time=90,
        )

    def _ensure_prompts_exist(self):
        """Ensure enhanced prompt files exist"""
        prompts_dir = Path(__file__).parent / "prompts"
        prompts_dir.mkdir(exist_ok=True)
        
        default_prompts = {
            "data_analysis_prompt.txt": self._get_enhanced_data_prompt(),
            "image_analysis_prompt.txt": self._get_enhanced_image_prompt()
        }
        
        for filename, content in default_prompts.items():
            prompt_path = prompts_dir / filename
            if not prompt_path.exists():
                prompt_path.write_text(content)
                logger.info(f"Created enhanced prompt: {filename}")

    def _get_enhanced_data_prompt(self) -> str:
        """Enhanced prompt with confidence scoring and detailed analysis"""
        return '''Analyze this packaged food product using STRICT evidence-based guidelines with confidence scoring.

Product Data:
{product_info}

**MANDATORY ANALYSIS FRAMEWORK:**

1. **DATA COMPLETENESS ASSESSMENT:**
   - Rate data completeness: Complete (>90%), Good (70-90%), Limited (50-70%), Poor (<50%)
   - Identify missing critical information
   - Note any unclear or ambiguous data

2. **EVIDENCE-BASED NUTRITIONAL EVALUATION:**
   Apply ONLY these established thresholds per 100g:
   
   **Sugar Content:**
   - Good: ≤5g (WHO/FSSAI guidelines)
   - Medium: 5.1-15g
   - Poor: >15g
   
   **Saturated Fat:**
   - Good: ≤1.5g (WHO/FDA guidelines)
   - Medium: 1.6-5g
   - Poor: >5g
   
   **Sodium Content:**
   - Good: ≤120mg (WHO/FSSAI guidelines)
   - Medium: 121-600mg
   - Poor: >600mg
   
   **Fiber Content:**
   - Good: ≥6g (ICMR-NIN/FDA guidelines)
   - Medium: 3-5.9g
   - Poor: <3g
   
   **Trans Fat:**
   - Good: 0g
   - Medium: 0.1-0.5g
   - Poor: >0.5g (WHO/FSSAI: ≤2% limit)

3. **ADDITIVE SAFETY ASSESSMENT:**
   - Reference only FSSAI/FDA/EFSA approved lists
   - Flag high-concern additives (artificial colors, certain preservatives)
   - Note NOVA processing classification

4. **CONFIDENCE SCORING:**
   Rate confidence (0-100%) for each assessment based on:
   - Data completeness and quality
   - Clarity of ingredient/nutrient information
   - Availability of authoritative guidelines
   - Consistency of data points

**MANDATORY OUTPUT FORMAT (JSON only):**
{{
    "score": [0-100 integer based on guideline compliance],
    "band": "Good/Medium/Poor/Insufficient Data",
    "confidence": [0-100 integer representing overall analysis confidence],
    "summary": "[Clear 2-sentence evidence-based summary with key findings]",
    "drivers": {{
        "positive": ["[Specific evidence-based positive factors with sources]"],
        "negative": ["[Specific evidence-based concerns with sources]"]
    }},
    "evidence": {{
        "data_completeness": {{
            "rating": "Complete/Good/Limited/Poor",
            "percentage": [0-100],
            "missing_critical": ["List of missing key information"],
            "confidence_impact": "[How missing data affects confidence]"
        }},
        "nutritional_analysis": [
            {{
                "nutrient": "Sugar",
                "product_value": "[X]g per 100g",
                "guideline": "WHO/FSSAI: Good ≤5g, Medium 5-15g, Poor >15g",
                "rating": "Good/Medium/Poor",
                "confidence": [0-100],
                "sources": ["WHO Guideline 2015", "FSSAI Regulations 2020"]
            }}
        ],
        "additive_assessment": {{
            "total_additives": [number],
            "high_concern": ["List with safety classification"],
            "moderate_concern": ["List"],
            "safety_confidence": [0-100],
            "sources": ["FSSAI Approved List", "FDA GRAS List"]
        }},
        "processing_classification": {{
            "nova_group": [1-4],
            "classification": "Unprocessed/Processed/Ultra-processed",
            "health_impact": "[Evidence-based assessment]",
            "confidence": [0-100],
            "sources": ["WHO NOVA Classification 2019"]
        }},
        "limitations": [
            "[List specific limitations in analysis due to missing/unclear data]"
        ],
        "authoritative_sources": [
            "FSSAI: Food Safety and Standards Regulations",
            "WHO: Healthy Diet Guidelines 2020",
            "ICMR-NIN: Dietary Guidelines for Indians 2020",
            "FDA: Nutrition Labeling Guide"
        ]
    }},
    "analysis_metadata": {{
        "analysis_date": "{analysis_date}",
        "guidelines_version": "2024",
        "total_confidence": [0-100],
        "data_quality_score": [0-100]
    }}
}}

**CRITICAL REQUIREMENTS:**
- NEVER speculate beyond available evidence
- If data is insufficient, state "Insufficient Data" rather than guessing
- Confidence scores must reflect actual data quality and completeness
- All assessments must cite specific authoritative sources
- Include detailed reasoning for confidence scores'''

    def _get_enhanced_image_prompt(self) -> str:
        """Enhanced image analysis prompt with OCR confidence scoring"""
        return '''Analyze this food label image using evidence-based guidelines with OCR confidence assessment.

**ENHANCED IMAGE ANALYSIS PROTOCOL:**

1. **TEXT EXTRACTION CONFIDENCE:**
   - Rate OCR confidence for each text section: High (>90%), Medium (70-90%), Low (<70%)
   - Identify unclear or partially visible text
   - Note image quality factors affecting analysis

2. **INGREDIENT LIST ANALYSIS:**
   - Extract all visible ingredients in order
   - Rate extraction confidence for ingredient list
   - Flag any unclear or partially obscured ingredients

3. **NUTRITIONAL INFORMATION EXTRACTION:**
   - Extract all visible nutritional values with units
   - Rate confidence for each nutritional value
   - Note any missing or unclear nutritional data

4. **EVIDENCE-BASED ASSESSMENT:**
   Apply same thresholds as data analysis:
   - Sugar: Good ≤5g, Medium 5-15g, Poor >15g
   - Saturated Fat: Good ≤1.5g, Medium 1.6-5g, Poor >5g
   - Sodium: Good ≤120mg, Medium 121-600mg, Poor >600mg
   - Fiber: Good ≥6g, Medium 3-5.9g, Poor <3g

**OUTPUT FORMAT (JSON only):**
{{
    "score": [0-100 based on visible evidence],
    "band": "Good/Medium/Poor/Insufficient Data",
    "confidence": [0-100 overall analysis confidence],
    "summary": "[Evidence-based summary noting OCR limitations]",
    "drivers": {{
        "positive": ["Visible positive factors with confidence notes"],
        "negative": ["Visible concerns with confidence notes"]
    }},
    "evidence": {{
        "ocr_quality": {{
            "overall_confidence": [0-100],
            "image_quality": "High/Medium/Low",
            "text_clarity": "Clear/Partially Clear/Unclear",
            "completeness": "Complete/Partial/Limited"
        }},
        "ingredients_extracted": {{
            "ingredients": ["All extracted ingredients"],
            "extraction_confidence": [0-100],
            "unclear_items": ["Any unclear ingredients"]
        }},
        "nutrients_extracted": {{
            "nutrients": {{"nutrient": "value with unit"}},
            "extraction_confidence": [0-100],
            "missing_nutrients": ["Key nutrients not visible"]
        }},
        "analysis_limitations": [
            "[Specific limitations due to image quality/OCR issues]"
        ],
        "authoritative_sources": ["FSSAI", "WHO", "FDA", "ICMR-NIN"]
    }},
    "analysis_metadata": {{
        "analysis_date": "{analysis_date}",
        "ocr_method": "image_analysis",
        "confidence_basis": "OCR quality and visible information"
    }}
}}'''

    def load_prompt(self, filename: str) -> str:
        """Load a prompt with dynamic content injection"""
        try:
            prompt_path = Path(__file__).parent / "prompts" / filename
            if not prompt_path.exists():
                logger.warning(f"Prompt file {filename} not found, using default")
                if "data" in filename:
                    content = self._get_enhanced_data_prompt()
                else:
                    content = self._get_enhanced_image_prompt()
            else:
                content = prompt_path.read_text(encoding='utf-8')
            
            # Inject current timestamp for analysis metadata
            content = content.replace("{analysis_date}", datetime.now().isoformat())
            
            return content
        except Exception as e:
            logger.error(f"Error loading prompt {filename}: {e}")
            raise

    def analyze_food_data(self, product_data: Dict[str, Any]):
        """Enhanced food data analysis with comprehensive error handling"""
        analysis_start = datetime.now()
        
        try:
            # Log analysis attempt
            self.analysis_log.append({
                'timestamp': analysis_start,
                'type': 'data_analysis',
                'product': product_data.get('name', 'Unknown'),
                'status': 'started'
            })
            
            # Pre-analysis validation
            validation_result = self._validate_product_data(product_data)
            if not validation_result['valid']:
                return self._create_validation_error_response(validation_result['errors'])
            
            # Calculate initial data confidence
            data_confidence = self._calculate_data_confidence(product_data)
            
            # Load and prepare prompt
            prompt = self.load_prompt("data_analysis_prompt.txt")
            
            # Format product info with confidence indicators
            enhanced_product_info = self._enhance_product_data(product_data, data_confidence)
            
            task = Task(
                description=prompt.format(
                    product_info=json.dumps(enhanced_product_info, indent=2)
                ),
                agent=self.agent,
                expected_output="JSON analysis with confidence scoring and evidence citations"
            )
            
            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                verbose=False
            )
            
            logger.info(f"Starting analysis for: {product_data.get('name', 'Unknown Product')}")
            result = crew.kickoff()
            
            # Process and validate result
            processed_result = self._process_result_with_confidence(result, data_confidence)
            
            # Log successful analysis
            self.analysis_log[-1].update({
                'status': 'completed',
                'duration': (datetime.now() - analysis_start).total_seconds(),
                'confidence': processed_result.get('confidence', 0) if isinstance(processed_result, dict) else 0
            })
            
            return processed_result
            
        except Exception as e:
            error_msg = f"Food data analysis failed: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            # Log failed analysis
            if self.analysis_log:
                self.analysis_log[-1].update({
                    'status': 'failed',
                    'error': str(e),
                    'duration': (datetime.now() - analysis_start).total_seconds()
                })
            
            return self._create_error_response_with_confidence(error_msg, product_data)

    def analyze_food_image(self, image_file):
        """Enhanced image analysis with OCR confidence assessment"""
        analysis_start = datetime.now()
        
        try:
            # Log analysis attempt
            self.analysis_log.append({
                'timestamp': analysis_start,
                'type': 'image_analysis',
                'status': 'started'
            })
            
            # Convert image to base64
            image_bytes = image_file.read()
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Assess image quality
            image_confidence = self._assess_image_quality(image_bytes)
            
            prompt = self.load_prompt("image_analysis_prompt.txt")
            
            task = Task(
                description=prompt,
                agent=self.agent,
                expected_output="JSON analysis with OCR confidence assessment"
            )
            
            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                verbose=False
            )
            
            logger.info("Starting image analysis")
            result = crew.kickoff()
            
            # Process result with image confidence
            processed_result = self._process_result_with_confidence(result, image_confidence)
            
            # Log successful analysis
            self.analysis_log[-1].update({
                'status': 'completed',
                'duration': (datetime.now() - analysis_start).total_seconds(),
                'confidence': processed_result.get('confidence', 0) if isinstance(processed_result, dict) else 0
            })
            
            return processed_result
            
        except Exception as e:
            error_msg = f"Image analysis failed: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            # Log failed analysis
            if self.analysis_log:
                self.analysis_log[-1].update({
                    'status': 'failed',
                    'error': str(e),
                    'duration': (datetime.now() - analysis_start).total_seconds()
                })
            
            return self._create_error_response_with_confidence(error_msg)
        finally:
            # Reset file pointer for potential reuse
            if hasattr(image_file, 'seek'):
                image_file.seek(0)

    def _validate_product_data(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate product data completeness and quality"""
        errors = []
        warnings = []
        
        # Check essential fields
        if not product_data.get('name') or product_data['name'] == 'Unknown Product':
            errors.append("Product name is missing or invalid")
        
        # Check ingredients
        ingredients = product_data.get('ingredients', [])
        if not ingredients:
            warnings.append("No ingredients list available")
        elif len(ingredients) < 3:
            warnings.append("Very short ingredients list - may be incomplete")
        
        # Check nutrients
        nutrients = product_data.get('nutrients', {})
        if not nutrients:
            warnings.append("No nutritional information available")
        else:
            key_nutrients = ['calories', 'fat', 'carbohydrates', 'protein']
            missing_nutrients = [n for n in key_nutrients if n not in nutrients]
            if missing_nutrients:
                warnings.append(f"Missing key nutrients: {', '.join(missing_nutrients)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'completeness_score': self._calculate_completeness_score(product_data)
        }

    def _calculate_data_confidence(self, product_data: Dict[str, Any]) -> float:
        """Calculate confidence score based on data completeness and quality"""
        confidence_factors = {
            'name': 0.15,
            'brand': 0.05,
            'ingredients': 0.30,
            'nutrients': 0.35,
            'source': 0.10,
            'image_url': 0.05
        }
        
        total_confidence = 0.0
        
        for field, weight in confidence_factors.items():
            if field in product_data and product_data[field]:
                if field == 'ingredients':
                    # Score based on ingredient list completeness
                    ingredient_count = len(product_data[field])
                    ingredient_score = min(ingredient_count / 15, 1.0)  # Full score at 15+ ingredients
                    total_confidence += weight * ingredient_score
                elif field == 'nutrients':
                    # Score based on nutrient completeness
                    nutrient_count = len(product_data[field])
                    nutrient_score = min(nutrient_count / 10, 1.0)  # Full score at 10+ nutrients
                    total_confidence += weight * nutrient_score
                else:
                    total_confidence += weight
        
        return round(total_confidence * 100, 1)

    def _assess_image_quality(self, image_bytes: bytes) -> float:
        """Assess image quality for OCR confidence (simplified version)"""
        # In a real implementation, you'd use image processing libraries
        # This is a placeholder that returns a reasonable confidence score
        
        image_size = len(image_bytes)
        
        # Basic size-based confidence (larger images generally better for OCR)
        if image_size > 1000000:  # > 1MB
            base_confidence = 85
        elif image_size > 500000:  # > 500KB
            base_confidence = 75
        elif image_size > 100000:  # > 100KB
            base_confidence = 65
        else:
            base_confidence = 50
        
        return float(base_confidence)

    def _enhance_product_data(self, product_data: Dict[str, Any], data_confidence: float) -> Dict[str, Any]:
        """Enhance product data with confidence indicators"""
        enhanced = product_data.copy()
        enhanced['_data_confidence'] = data_confidence
        enhanced['_analysis_timestamp'] = datetime.now().isoformat()
        
        return enhanced

    def _calculate_completeness_score(self, product_data: Dict[str, Any]) -> float:
        """Calculate data completeness score"""
        required_fields = ['name', 'ingredients', 'nutrients']
        optional_fields = ['brand', 'category', 'image_url', 'pack_size']
        
        required_score = sum(1 for field in required_fields if product_data.get(field))
        optional_score = sum(0.5 for field in optional_fields if product_data.get(field))
        
        max_score = len(required_fields) + (len(optional_fields) * 0.5)
        total_score = required_score + optional_score
        
        return round((total_score / max_score) * 100, 1)

    def _process_result_with_confidence(self, result, input_confidence: float) -> str:
        """Process CrewAI result with confidence validation and enhancement"""
        try:
            if hasattr(result, 'raw'):
                result_str = result.raw
            elif hasattr(result, 'result'):
                result_str = result.result
            else:
                result_str = str(result)
            
            result_str = result_str.strip()
            
            # Clean JSON formatting
            if result_str.startswith('```json'):
                result_str = result_str[7:]
            if result_str.startswith('```'):
                result_str = result_str[3:]
            if result_str.endswith('```'):
                result_str = result_str[:-3]
            
            result_str = result_str.strip()
            
            # Parse and validate JSON
            try:
                parsed = json.loads(result_str)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in result: {e}")
                return self._create_json_error_response(result_str, input_confidence)
            
            # Enhance with confidence validation
            enhanced_result = self._enhance_result_confidence(parsed, input_confidence)
            
            return json.dumps(enhanced_result, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Result processing failed: {e}")
            return self._create_error_response_with_confidence(f"Result processing error: {str(e)}")

    def _enhance_result_confidence(self, parsed_result: Dict[str, Any], input_confidence: float) -> Dict[str, Any]:
        """Enhance result with comprehensive confidence scoring"""
        
        # Ensure score is integer
        if 'score' in parsed_result and isinstance(parsed_result['score'], str):
            try:
                parsed_result['score'] = int(parsed_result['score'])
            except (ValueError, TypeError):
                parsed_result['score'] = 0
        
        # Validate and adjust confidence based on input data quality
        result_confidence = parsed_result.get('confidence', 70)
        if isinstance(result_confidence, str):
            try:
                result_confidence = int(result_confidence)
            except (ValueError, TypeError):
                result_confidence = 70
        
        # Adjust confidence based on input quality
        adjusted_confidence = min(result_confidence, input_confidence)
        parsed_result['confidence'] = int(adjusted_confidence)
        
        # Ensure evidence structure exists
        if 'evidence' not in parsed_result:
            parsed_result['evidence'] = {}
        
        # Add confidence metadata
        if 'analysis_metadata' not in parsed_result:
            parsed_result['analysis_metadata'] = {}
        
        parsed_result['analysis_metadata'].update({
            'input_confidence': input_confidence,
            'analysis_confidence': result_confidence,
            'final_confidence': adjusted_confidence,
            'confidence_factors': self._get_confidence_factors(parsed_result)
        })
        
        # Add required evidence sections if missing
        required_sections = ['authoritative_sources', 'limitations']
        for section in required_sections:
            if section not in parsed_result['evidence']:
                if section == 'authoritative_sources':
                    parsed_result['evidence'][section] = [
                        "FSSAI: Food Safety and Standards Authority of India",
                        "WHO: World Health Organization Guidelines",
                        "ICMR-NIN: Dietary Guidelines for Indians 2020"
                    ]
                else:
                    parsed_result['evidence'][section] = []
        
        return parsed_result

    def _get_confidence_factors(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate detailed confidence factors"""
        factors = {}
        
        # Data completeness factor
        evidence = result.get('evidence', {})
        if 'data_completeness' in evidence:
            factors['data_completeness'] = evidence['data_completeness'].get('percentage', 0)
        
        # Analysis depth factor
        nutritional_analysis = evidence.get('nutritional_analysis', [])
        factors['analysis_depth'] = min(len(nutritional_analysis) * 15, 100)  # Full score at 7+ nutrients
        
        # Source reliability factor
        sources = evidence.get('authoritative_sources', [])
        factors['source_reliability'] = min(len(sources) * 25, 100)  # Full score at 4+ sources
        
        return factors

    def _create_validation_error_response(self, errors: List[str]) -> str:
        """Create response for validation errors"""
        error_response = {
            "score": 0,
            "band": "Insufficient Data",
            "confidence": 10,
            "summary": f"Analysis cannot proceed due to data validation errors: {', '.join(errors)}",
            "drivers": {
                "positive": [],
                "negative": [f"Data validation failed: {error}" for error in errors]
            },
            "evidence": {
                "validation_errors": errors,
                "data_completeness": {
                    "rating": "Poor",
                    "percentage": 0,
                    "confidence_impact": "Critical - prevents reliable analysis"
                },
                "limitations": ["Cannot perform evidence-based analysis with insufficient data"],
                "authoritative_sources": ["FSSAI", "WHO", "ICMR-NIN"]
            },
            "analysis_metadata": {
                "analysis_date": datetime.now().isoformat(),
                "status": "validation_failed",
                "total_confidence": 10
            }
        }
        return json.dumps(error_response)

    def _create_json_error_response(self, raw_result: str, input_confidence: float) -> str:
        """Create response when JSON parsing fails"""
        error_response = {
            "score": 0,
            "band": "Unknown",
            "confidence": max(20, int(input_confidence * 0.3)),  # Reduced confidence due to parsing error
            "summary": "Analysis completed but result format is invalid. Raw analysis available.",
            "drivers": {
                "positive": [],
                "negative": ["Analysis result parsing failed - format error"]
            },
            "evidence": {
                "parsing_error": "AI returned invalid JSON format",
                "raw_analysis": raw_result[:500] + "..." if len(raw_result) > 500 else raw_result,
                "limitations": ["Cannot parse structured analysis", "Manual review of raw result required"],
                "authoritative_sources": ["FSSAI", "WHO", "ICMR-NIN"]
            },
            "analysis_metadata": {
                "analysis_date": datetime.now().isoformat(),
                "status": "parsing_failed",
                "input_confidence": input_confidence
            }
        }
        return json.dumps(error_response)

    def _create_error_response_with_confidence(self, error_message: str, product_data: Optional[Dict] = None) -> str:
        """Create comprehensive error response with confidence assessment"""
        confidence = 15
        
        if product_data:
            # Calculate confidence based on available data even in error state
            data_confidence = self._calculate_data_confidence(product_data)
            confidence = max(15, int(data_confidence * 0.2))  # Very low confidence due to analysis failure
        
        error_response = {
            "score": 0,
            "band": "Unknown",
            "confidence": confidence,
            "summary": f"Analysis failed due to technical error: {error_message}",
            "drivers": {
                "positive": [],
                "negative": [f"Technical analysis failure: {error_message}"]
            },
            "evidence": {
                "technical_error": error_message,
                "data_available": bool(product_data),
                "fallback_assessment": "Manual analysis recommended",
                "limitations": [
                    "Automated analysis system failure",
                    "Evidence-based guidelines could not be applied",
                    "Manual expert review recommended"
                ],
                "authoritative_sources": ["FSSAI", "WHO", "ICMR-NIN", "FDA"],
                "recovery_suggestions": [
                    "Try re-analyzing with clearer product data",
                    "Verify all product information is complete",
                    "Contact support if issue persists"
                ]
            },
            "analysis_metadata": {
                "analysis_date": datetime.now().isoformat(),
                "status": "technical_failure",
                "error_type": "system_error",
                "recovery_possible": True
            }
        }
        return json.dumps(error_response)

    def get_analysis_log(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent analysis attempts for debugging"""
        return self.analysis_log[-limit:] if self.analysis_log else []

    def clear_analysis_log(self) -> None:
        """Clear analysis log"""
        self.analysis_log = []

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status and health check"""
        try:
            # Test LLM connection
            test_task = Task(
                description="Reply with 'OK' if system is working",
                agent=self.agent,
                expected_output="Simple OK response"
            )
            
            test_crew = Crew(agents=[self.agent], tasks=[test_task], verbose=False)
            test_result = test_crew.kickoff()
            
            llm_status = "healthy" if test_result else "error"
        except Exception as e:
            llm_status = f"error: {str(e)}"
        
        recent_failures = [log for log in self.analysis_log[-20:] if log.get('status') == 'failed']
        
        return {
            'llm_status': llm_status,
            'total_analyses': len(self.analysis_log),
            'recent_failures': len(recent_failures),
            'failure_rate': len(recent_failures) / max(len(self.analysis_log[-20:]), 1) * 100,
            'last_analysis': self.analysis_log[-1] if self.analysis_log else None,
            'system_healthy': llm_status == "healthy" and len(recent_failures) < 5
        }

# Global analyzer instance
_analyzer = None

def get_analyzer() -> FoodAnalyzer:
    """Get or create global analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = FoodAnalyzer()
    return _analyzer

def analyze_food_image(image_file):
    """Analyze food label image with enhanced error handling"""
    analyzer = get_analyzer()
    return analyzer.analyze_food_image(image_file)

def analyze_food_data(product_data: Dict[str, Any]):
    """Analyze structured product data with enhanced error handling"""
    analyzer = get_analyzer()
    return analyzer.analyze_food_data(product_data)

def get_system_health():
    """Get system health status"""
    analyzer = get_analyzer()
    return analyzer.get_system_status()