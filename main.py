#!/usr/bin/env python3
"""
Health Rater - Main Application Entry Point

This application provides a web interface for calculating the health rating
of food products using the Nutri-Score algorithm.
"""

import os
import logging
from src.frontend.app import app
from src.utils.i18n import set_language_locale

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("health_rater.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Run the Health Rater application."""
    try:
        # Set default locale
        set_language_locale('en')
        
        # Log startup information
        logger.info("Starting Health Rater application")
        
        # Create necessary directories
        os.makedirs("data", exist_ok=True)
        
        # Get port from environment or use default
        port = int(os.environ.get("PORT", 8050))
        
        # Start the server
        app.run(
            debug=True,
            host='0.0.0.0',
            port=port
        )
    except Exception as e:
        logger.error(f"Error starting application: {str(e)}")

if __name__ == "__main__":
    main()
