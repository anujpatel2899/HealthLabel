import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from src.backend.langgraph_processor import LangGraphProcessor

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LLMProcessor:
    """
    Adapter class that wraps the LangGraphProcessor for backward compatibility.
    Originally used direct OpenAI API calls, now uses LangGraph workflow.
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the LLM processor adapter.
        
        Args:
            api_key: OpenAI API key (if None, will look for OPENAI_API_KEY env var)
        """
        logger.info("Initializing LLMProcessor (adapter for LangGraphProcessor)")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.processor = LangGraphProcessor(self.api_key)
    
    def extract_nutrition_data(self, text):
        """
        Extract structured nutrition data from text using LangGraph.
        
        Args:
            text: The text to analyze (e.g., OCR from label)
            
        Returns:
            dict: Structured nutrition data or None if processing failed
        """
        if not self.api_key:
            logger.error("Cannot process text: No OpenAI API key available")
            return None
            
        try:
            logger.info("LLMProcessor adapter: Forwarding request to LangGraphProcessor")
            result = self.processor.extract_nutrition_data(text)
            
            if result:
                # Add timestamp if not already present
                if "timestamp" not in result:
                    result["timestamp"] = datetime.now().isoformat()
                
                logger.info("Successfully extracted nutrition data using LangGraph (via adapter)")
                return result
            
            logger.error("Failed to extract nutrition data from LangGraph processor")
            return None
                
        except Exception as e:
            logger.error(f"Error in LLM processing: {str(e)}")
            return None
            
    def analyze_missing_data(self, product_data):
        """
        Analyze what data is missing and generate suggestions for the user.
        
        Args:
            product_data: The product data structure with potentially missing fields
            
        Returns:
            dict: Analysis of missing data and suggestions
        """
        if not self.api_key:
            logger.warning("Cannot analyze missing data: No OpenAI API key available")
            return {"missing_fields": [], "suggestions": ""}
            
        try:
            logger.info("LLMProcessor adapter: Forwarding missing data analysis to LangGraphProcessor")
            return self.processor.analyze_missing_data(product_data)
                
        except Exception as e:
            logger.error(f"Error in LLM analysis of missing data: {str(e)}")
            return {"missing_fields": [], "suggestions": ""}
