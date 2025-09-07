"""
LangGraph Processor for Health Rater

This module implements a LangGraph-based workflow for extracting and processing
nutrition information from food labels.
"""

import logging
import json
import os
from datetime import datetime
from typing import List, TypedDict, Literal, Optional
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define state schema
class NutritionData(BaseModel):
    energy_kcal: float = Field(default=0, description="Energy in kcal per 100g/ml")
    sugars_g: float = Field(default=0, description="Sugars in g per 100g/ml")
    saturated_fat_g: float = Field(default=0, description="Saturated fat in g per 100g/ml")
    salt_g: float = Field(default=0, description="Salt in g per 100g/ml")
    fiber_g: float = Field(default=0, description="Dietary fiber in g per 100g/ml")
    protein_g: float = Field(default=0, description="Protein in g per 100g/ml")
    fruits_veg_nuts_percent: float = Field(default=0, description="Percentage of fruits/vegetables/nuts")

class ProductType(BaseModel):
    is_beverage: bool = Field(default=False, description="Whether the product is a beverage")
    is_cheese: bool = Field(default=False, description="Whether the product is a cheese")
    contains_sweeteners: bool = Field(default=False, description="Whether the product contains sweeteners")

class ProductData(BaseModel):
    product_name: str = Field(default="", description="Name of the product")
    nutrition_data: NutritionData = Field(default_factory=NutritionData, description="Nutritional information")
    product_type: ProductType = Field(default_factory=ProductType, description="Product categorization")
    ingredients: List[str] = Field(default_factory=list, description="List of ingredients")
    source: str = Field(default="LangGraph Analysis", description="Source of the data")
    confidence: str = Field(default="Medium", description="Confidence level in the extracted data")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp of processing")
    missing_fields: List[str] = Field(default_factory=list, description="Fields that couldn't be extracted")

class ExtractionState(TypedDict):
    input_text: str
    extracted_data: Optional[ProductData]
    error: Optional[str]
    confidence_level: Optional[str]
    missing_fields: List[str]
    extraction_complete: bool
    analysis_needed: bool

def init_state(text: str) -> ExtractionState:
    """Initialize the state with input text."""
    return {
        "input_text": text,
        "extracted_data": None,
        "error": None,
        "confidence_level": None,
        "missing_fields": [],
        "extraction_complete": False,
        "analysis_needed": False
    }

def extract_nutrition_data(state: ExtractionState, llm) -> ExtractionState:
    """Extract structured nutrition data from text using LLM."""
    try:
        # Create the prompt for extracting nutritional information
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="You are a nutrition data extraction assistant. Extract structured data from food label text."),
            HumanMessage(content="""
            Extract nutritional information from the following food label text. 
            Return a JSON object with the following structure:
            {
                "product_name": "Name of the product",
                "nutrition_data": {
                    "energy_kcal": [energy in kcal per 100g/ml],
                    "sugars_g": [sugars in g per 100g/ml],
                    "saturated_fat_g": [saturated fat in g per 100g/ml],
                    "salt_g": [salt in g per 100g/ml],
                    "fiber_g": [fiber in g per 100g/ml],
                    "protein_g": [protein in g per 100g/ml],
                    "fruits_veg_nuts_percent": [estimated percentage of fruits/vegetables/nuts, 0 if unknown]
                },
                "product_type": {
                    "is_beverage": [true/false],
                    "is_cheese": [true/false],
                    "contains_sweeteners": [true/false]
                },
                "ingredients": ["ingredient1", "ingredient2", ...],
                "source": "LangGraph Analysis",
                "confidence": "Medium"
            }
            
            For missing values, use 0 for numerical fields and empty strings for text fields.
            Only extract facts directly stated in the text, don't invent information.
            
            TEXT TO ANALYZE:
            {input_text}
            """)
        ])
        
        # Run the extraction
        chain = prompt | llm
        response = chain.invoke({"input_text": state["input_text"]})
        
        # Parse the response
        json_str = None
        response_text = response.content
        
        # Find the JSON object in the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            data_dict = json.loads(json_str)
            
            # Create a ProductData object
            nutrition_data = NutritionData(**data_dict.get("nutrition_data", {}))
            product_type = ProductType(**data_dict.get("product_type", {}))
            
            product_data = ProductData(
                product_name=data_dict.get("product_name", ""),
                nutrition_data=nutrition_data,
                product_type=product_type,
                ingredients=data_dict.get("ingredients", []),
                source=data_dict.get("source", "LangGraph Analysis"),
                confidence=data_dict.get("confidence", "Medium"),
                timestamp=datetime.now().isoformat()
            )
            
            # Update state
            state["extracted_data"] = product_data
            state["confidence_level"] = data_dict.get("confidence", "Medium")
            state["extraction_complete"] = True
            state["analysis_needed"] = True
            
            # Check for missing fields
            missing = []
            if not data_dict.get("product_name", ""):
                missing.append("product_name")
            if nutrition_data.energy_kcal == 0:
                missing.append("energy_kcal")
            if nutrition_data.sugars_g == 0:
                missing.append("sugars_g")
            if nutrition_data.saturated_fat_g == 0:
                missing.append("saturated_fat_g")
            if nutrition_data.salt_g == 0:
                missing.append("salt_g")
            
            state["missing_fields"] = missing
            
            logger.info("Successfully extracted nutrition data using LangGraph")
        else:
            state["error"] = "Failed to extract JSON from LLM response"
            logger.error("Failed to extract JSON from LLM response")
    
    except Exception as e:
        state["error"] = f"Error in extraction: {str(e)}"
        logger.error(f"Error in LangGraph processing: {str(e)}")
    
    return state

def analyze_missing_data(state: ExtractionState, llm) -> ExtractionState:
    """Analyze what data is missing and generate suggestions."""
    if not state["analysis_needed"] or not state["extracted_data"]:
        return state
    
    try:
        # Create the prompt for analyzing missing data
        product_json = json.dumps(state["extracted_data"].model_dump(), indent=2)
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="You are a nutrition data analysis assistant."),
            HumanMessage(content=f"""
            Analyze the following product data and identify what important nutritional information is missing.
            Generate suggestions for what the user should look for on the product packaging.
            
            PRODUCT DATA:
            {product_json}
            
            Return a JSON object with the following structure:
            {{
                "missing_fields": ["field1", "field2", ...],
                "suggestions": "Detailed suggestions for what to look for on the packaging"
            }}
            """)
        ])
        
        # Run the analysis
        chain = prompt | llm
        response = chain.invoke({})
        
        # Parse the response
        response_text = response.content
        
        # Find the JSON object in the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)
            
            # Update state
            if "missing_fields" in data:
                state["missing_fields"].extend(data["missing_fields"])
                # Remove duplicates
                state["missing_fields"] = list(set(state["missing_fields"]))
            
            if "suggestions" in data:
                # Add suggestions to extracted data
                state["extracted_data"].missing_fields = state["missing_fields"]
            
            logger.info("Successfully analyzed missing data using LangGraph")
    
    except Exception as e:
        logger.error(f"Error in LangGraph analysis of missing data: {str(e)}")
    
    return state

def should_analyze_missing_data(state: ExtractionState) -> Literal["analyze", "complete"]:
    """Determine if missing data analysis is needed."""
    if state["analysis_needed"] and state["extracted_data"]:
        return "analyze"
    return "complete"

class LangGraphProcessor:
    """Class to handle LangGraph-based workflow for food label analysis."""
    
    def __init__(self, api_key=None):
        """
        Initialize the LangGraph processor.
        
        Args:
            api_key: OpenAI API key (if None, will look for OPENAI_API_KEY env var)
        """
        # Import here to avoid circular imports
        from langchain_openai import ChatOpenAI
        
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        
        if not self.api_key:
            logger.warning("No OpenAI API key provided. LangGraph processing will not be available.")
            self.llm = None
        else:
            self.llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0.2,
                api_key=self.api_key
            )
            
            # Build the graph
            self._build_graph()
            
            logger.info("LangGraph Processor initialized with API key")
    
    def _build_graph(self):
        """Build the LangGraph workflow."""
        # Create the graph
        builder = StateGraph(ExtractionState)
        
        # Add nodes
        builder.add_node("extract", lambda state: extract_nutrition_data(state, self.llm))
        builder.add_node("analyze", lambda state: analyze_missing_data(state, self.llm))
        
        # Add edges
        builder.add_edge(START, "extract")
        builder.add_conditional_edges(
            "extract",
            should_analyze_missing_data,
            {
                "analyze": "analyze",
                "complete": END
            }
        )
        builder.add_edge("analyze", END)
        
        # Compile the graph
        self.graph = builder.compile()
    
    def extract_nutrition_data(self, text):
        """
        Extract structured nutrition data from text using LangGraph.
        
        Args:
            text: The text to analyze (e.g., OCR from label)
            
        Returns:
            dict: Structured nutrition data or None if processing failed
        """
        if not self.llm:
            logger.error("Cannot process text: No OpenAI API key available")
            return None
        
        try:
            # Initialize state with input text
            initial_state = init_state(text)
            
            # Run the graph
            final_state = self.graph.invoke(initial_state)
            
            # Return the extracted data
            if final_state["extracted_data"]:
                return final_state["extracted_data"].model_dump()
            
            return None
            
        except Exception as e:
            logger.error(f"Error in LangGraph processing: {str(e)}")
            return None
    
    def analyze_missing_data(self, product_data):
        """
        Analyze what data is missing and generate suggestions for the user.
        
        Args:
            product_data: The product data structure with potentially missing fields
            
        Returns:
            dict: Analysis of missing data and suggestions
        """
        if not self.llm:
            logger.warning("Cannot analyze missing data: No OpenAI API key available")
            return {"missing_fields": [], "suggestions": ""}
        
        # This is now handled as part of the graph workflow, but we include this method
        # for compatibility with the existing API
        try:
            # Extract missing fields from the product data
            missing_fields = product_data.get("missing_fields", [])
            
            return {
                "missing_fields": missing_fields,
                "suggestions": "Please check the product packaging for the missing nutritional information."
            }
                
        except Exception as e:
            logger.error(f"Error in LangGraph analysis of missing data: {str(e)}")
            return {"missing_fields": [], "suggestions": ""}
            
    def process_image_with_ocr(self, image):
        """
        Process an image using LLM-based OCR to extract nutritional information.
        
        Args:
            image: PIL Image to process
            
        Returns:
            str: Extracted text from the image
        """
        if not self.llm:
            logger.error("Cannot process image: No OpenAI API key available")
            return None
            
        try:
            # Convert the image to base64 for LLM processing
            import base64
            import io
            
            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")
                
            # Resize the image if it's too large (to reduce API costs)
            max_dimension = 800
            if max(image.size) > max_dimension:
                ratio = max_dimension / max(image.size)
                new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                image = image.resize(new_size)
                
            # Convert to base64
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG", quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # Create the prompt for OCR processing with vision capabilities
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage
            
            # Use a multimodal model
            vision_llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0.1,
                api_key=self.api_key if isinstance(self.api_key, str) else None
            )
            
            # Send the image to the LLM with instruction to extract nutritional information
            messages = [
                HumanMessage(
                    content=[
                        {
                            "type": "text", 
                            "text": "This is an image of a food product label. Please extract ALL text you can see, focusing on nutritional information such as calories, fat, sugar, protein, salt/sodium, and ingredients. Format it as a comprehensive list of all information visible, preserving the structure. Include EVERYTHING you can read from the packaging."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}"
                            }
                        }
                    ]
                )
            ]
            
            # Get the response
            response = vision_llm.invoke(messages)
            extracted_text = response.content
            
            logger.info("Successfully extracted text from image using LLM-based OCR")
            return extracted_text
            
        except Exception as e:
            logger.error(f"Error in LLM-based OCR processing: {str(e)}")
            return None
