"""
This file contains the main implementation of the Health Rater app.
It is imported by app.py to avoid circular imports.
"""

from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
import base64
import io
from PIL import Image
import logging
import pandas as pd

# Import our custom modules
from src.utils.barcode_detector import detect_barcode_from_image, has_barcode
from src.backend.nutri_score import NutriScoreCalculator
from src.backend.product_processor import ProductDataProcessor
from src.backend.langgraph_processor import LangGraphProcessor

# Set up logging
logger = logging.getLogger(__name__)

# Initialize components
nutri_score_calculator = NutriScoreCalculator()
product_processor = ProductDataProcessor()
llm_processor = LangGraphProcessor()  # This will use OPENAI_API_KEY from environment if available

def setup_app(app):
    """Set up the app with layout and callbacks."""
    
    # Define the layout
    app.layout = html.Div([
        html.Div([
            html.H1("Health Rater", className="header-title"),
            html.P("Calculate the health score of food products using the Nutri-Score algorithm.", 
                className="header-description"),
        ], className="header"),
        
        html.Div([
            html.Div([
                html.Div([
                    html.H3("Input Methods", className="card-header"),
                    html.Div([
                        dcc.Tabs([
                            dcc.Tab(label="Barcode", value="tab-barcode", children=[
                                html.Div([
                                    html.H5("Enter Barcode Number", className="mt-3"),
                                    dcc.Input(id="barcode-input", type="text", placeholder="Enter barcode number...", className="input-field"),
                                    html.H5("Or Upload Barcode Image", className="mt-3"),
                                    dcc.Upload(
                                        id="upload-barcode-image",
                                        children=html.Div([
                                            'Drag and Drop or ',
                                            html.A('Select a File')
                                        ]),
                                        className="upload-area",
                                        multiple=False
                                    ),
                                    html.Div(id="barcode-image-preview", className="preview-area")
                                ], className="tab-content")
                            ]),
                            dcc.Tab(label="Product Photo", value="tab-photo", children=[
                                html.Div([
                                    html.H5("Upload Product Label Photo", className="mt-3"),
                                    dcc.Upload(
                                        id="upload-product-photo",
                                        children=html.Div([
                                            'Drag and Drop or ',
                                            html.A('Select a File')
                                        ]),
                                        className="upload-area",
                                        multiple=False
                                    ),
                                    html.Div(id="photo-preview", className="preview-area")
                                ], className="tab-content")
                            ]),
                            dcc.Tab(label="Text Input", value="tab-text", children=[
                                html.Div([
                                    html.H5("Enter Product Information", className="mt-3"),
                                    dcc.Textarea(id="text-input", 
                                        placeholder="Enter product information (e.g., nutrition facts, ingredients)...",
                                        className="text-input-area"
                                    )
                                ], className="tab-content")
                            ])
                        ], id="tabs", value="tab-barcode"),
                        html.Button("Calculate Health Score", id="submit-button", className="submit-button")
                    ], className="card-body")
                ], className="card input-card")
            ], className="column"),
            
            html.Div([
                html.Div([
                    html.H3("Results", className="card-header"),
                    html.Div([
                        html.Div(id="results-container", children=[
                            html.P("Enter product information and click 'Calculate Health Score' to see results.", className="placeholder-text")
                        ])
                    ], className="card-body")
                ], className="card results-card")
            ], className="column")
        ], className="row"),
        
        html.Div([
            html.Div([
                html.H3("Evidence & Detailed Analysis", className="card-header"),
                html.Div([
                    html.Div(id="evidence-container", children=[
                        html.P("Detailed analysis will appear here after calculation.", className="placeholder-text")
                    ])
                ], className="card-body")
            ], className="card evidence-card")
        ], className="row"),
        
        html.Div([
            html.Div([
                html.H3("Search History", className="card-header"),
                html.Div([
                    html.Div(id="history-container", children=[
                        html.P("Your search history will appear here.", className="placeholder-text")
                    ])
                ], className="card-body")
            ], className="card history-card")
        ], className="row"),
        
        # Store components for intermediate data
        dcc.Store(id="current-product-data"),
        dcc.Store(id="current-score-data"),
        dcc.Store(id="detected-barcode-data"),
        dcc.Store(id="processing-log")
    ], className="container")

    # Define callbacks
    @app.callback(
        [Output("barcode-image-preview", "children"),
        Output("detected-barcode-data", "data")],
        [Input("upload-barcode-image", "contents")],
        [State("upload-barcode-image", "filename")]
    )
    def update_barcode_preview(contents, filename):
        """Process uploaded barcode image and detect barcode."""
        if contents is None:
            return None, None
        
        try:
            # Decode the base64 image
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            
            # Process the image
            image = Image.open(io.BytesIO(decoded))
            
            # Detect barcode
            barcode_data = detect_barcode_from_image(image)
            
            # Create preview
            preview = html.Div([
                html.H6(f"Uploaded: {filename}"),
                html.Img(src=contents, style={"maxWidth": "100%", "maxHeight": "300px"}),
                html.Hr(),
                html.Div(f"Detected Barcode: {barcode_data['data'] if barcode_data else 'None'}", 
                        style={"color": "green" if barcode_data else "red"})
            ])
            
            return preview, barcode_data
        except Exception as e:
            logger.error(f"Error processing barcode image: {str(e)}")
            return html.Div(f"Error processing image: {str(e)}"), None

    @app.callback(
        Output("photo-preview", "children"),
        [Input("upload-product-photo", "contents")],
        [State("upload-product-photo", "filename")]
    )
    def update_photo_preview(contents, filename):
        """Display preview of uploaded product photo."""
        if contents is None:
            return None
        
        try:
            # Create preview
            preview = html.Div([
                html.H6(f"Uploaded: {filename}"),
                html.Img(src=contents, style={"maxWidth": "100%", "maxHeight": "300px"})
            ])
            
            return preview
        except Exception as e:
            logger.error(f"Error processing product photo: {str(e)}")
            return html.Div(f"Error processing image: {str(e)}")

    @app.callback(
        [Output("current-product-data", "data"),
        Output("current-score-data", "data"),
        Output("processing-log", "data")],
        [Input("submit-button", "n_clicks")],
        [State("tabs", "value"),
        State("barcode-input", "value"),
        State("detected-barcode-data", "data"),
        State("upload-product-photo", "contents"),
        State("text-input", "value")]
    )
    def process_input(n_clicks, active_tab, barcode_input, detected_barcode, photo_contents, text_input):
        """Process the input based on the active tab and calculate health score."""
        if n_clicks is None:
            return None, None, None
        
        # Initialize processing log
        processing_log = []
        
        try:
            # Process based on active tab
            if active_tab == "tab-barcode":
                # Get barcode either from input or detected from image
                barcode = None
                
                if barcode_input and barcode_input.strip():
                    barcode = barcode_input.strip()
                    processing_log.append(f"Using manually entered barcode: {barcode}")
                elif detected_barcode:
                    barcode = detected_barcode.get("data")
                    processing_log.append(f"Using detected barcode: {barcode}")
                
                if not barcode:
                    processing_log.append("No valid barcode provided")
                    return None, None, processing_log
                
                # Process barcode data
                product_data = product_processor.process_barcode_data(barcode)
                if not product_data:
                    processing_log.append(f"No product found for barcode: {barcode}")
                    return None, None, processing_log
                
                processing_log.append(f"Successfully retrieved product data for barcode: {barcode}")
                
            elif active_tab == "tab-photo":
                if not photo_contents:
                    processing_log.append("No photo uploaded")
                    return None, None, processing_log
                
                # Decode the base64 image
                content_type, content_string = photo_contents.split(',')
                decoded = base64.b64decode(content_string)
                
                # Process the image
                image = Image.open(io.BytesIO(decoded))
                
                # Check if image contains barcode
                if has_barcode(image):
                    # Detect and process barcode
                    barcode_data = detect_barcode_from_image(image)
                    if barcode_data and "data" in barcode_data:
                        barcode = barcode_data.get("data")
                        processing_log.append(f"Detected barcode in image: {barcode}")
                        
                        # Process barcode data
                        product_data = product_processor.process_barcode_data(barcode)
                        if product_data:
                            processing_log.append(f"Successfully retrieved product data for barcode: {barcode}")
                        else:
                            processing_log.append(f"No product found for barcode: {barcode}")
                            return None, None, processing_log
                    else:
                        processing_log.append("Failed to extract barcode from image")
                        return None, None, processing_log
                else:
                    # Use LLM for OCR processing if available
                    processing_log.append("No barcode detected in image. Attempting OCR processing.")
                    
                    if llm_processor.api_key:
                        # Extract text from the image using LLM-based OCR
                        extracted_text = llm_processor.process_image_with_ocr(image)
                        
                        if extracted_text:
                            processing_log.append("Successfully extracted text from image using LLM-based OCR")
                            
                            # Use LLM to extract structured data from the OCR text
                            product_data = product_processor.process_text_input(extracted_text, llm_processor)
                            
                            if product_data:
                                processing_log.append("Successfully extracted product data from image")
                                product_data["source"] = "Image OCR Analysis (LLM)"
                            else:
                                processing_log.append("Failed to extract product data from OCR text")
                                return None, None, processing_log
                        else:
                            processing_log.append("Failed to extract text from image")
                            return None, None, processing_log
                    else:
                        # Fallback for when no LLM is available
                        processing_log.append("LLM not available for OCR processing")
                        
                        # For the demo, we'll create a placeholder product
                        product_data = {
                            "product_name": "Unknown Product (from image)",
                            "nutrition_data": {
                                "energy_kcal": 250,
                                "sugars_g": 15,
                                "saturated_fat_g": 5,
                                "salt_g": 1.2,
                                "fiber_g": 2,
                                "protein_g": 10,
                                "fruits_veg_nuts_percent": 20
                            },
                            "product_type": {
                                "is_beverage": False,
                                "is_cheese": False,
                                "contains_sweeteners": False
                            },
                            "ingredients": ["Simulated ingredient 1", "Simulated ingredient 2"],
                            "source": "Image Analysis (simulated)",
                            "confidence": "Low"
                        }
                        processing_log.append("Created placeholder product data for demonstration purposes")
            
            elif active_tab == "tab-text":
                if not text_input or not text_input.strip():
                    processing_log.append("No text input provided")
                    return None, None, processing_log
                
                processing_log.append("Processing text input")
                
                # Use LLM to extract structured data if available
                if llm_processor.api_key:
                    product_data = product_processor.process_text_input(text_input, llm_processor)
                    if product_data:
                        processing_log.append("Successfully extracted product data from text using LLM")
                    else:
                        processing_log.append("Failed to extract product data from text")
                        return None, None, processing_log
                else:
                    # Basic fallback if no LLM is available
                    product_data = product_processor.process_text_input(text_input)
                    processing_log.append("Processed text input without LLM (limited capabilities)")
            
            # Calculate the Nutri-Score
            if product_data and "nutrition_data" in product_data:
                # Extract product type information
                product_type = product_data.get("product_type", {})
                is_beverage = product_type.get("is_beverage", False)
                is_cheese = product_type.get("is_cheese", False)
                contains_sweeteners = product_type.get("contains_sweeteners", False)
                
                # Calculate score
                score_data = nutri_score_calculator.calculate_score(
                    product_data["nutrition_data"],
                    is_beverage=is_beverage,
                    is_cheese=is_cheese,
                    contains_sweeteners=contains_sweeteners
                )
                
                processing_log.append(f"Calculated Nutri-Score: {score_data['grade']} (raw score: {score_data['raw_score']})")
                
                return product_data, score_data, processing_log
            else:
                processing_log.append("Failed to process product data")
                return None, None, processing_log
                
        except Exception as e:
            logger.error(f"Error processing input: {str(e)}")
            processing_log.append(f"Error: {str(e)}")
            return None, None, processing_log

    @app.callback(
        Output("results-container", "children"),
        [Input("current-product-data", "data"),
        Input("current-score-data", "data")]
    )
    def update_results(product_data, score_data):
        """Update the results display with product and score information."""
        if not product_data or not score_data:
            return html.P("No results to display. Please submit product information.", className="placeholder-text")
        
        try:
            # Color mapping for Nutri-Score grades
            color_map = {
                "A": "#038141",  # Dark Green
                "B": "#85BB2F",  # Light Green
                "C": "#FECB02",  # Yellow
                "D": "#EE8100",  # Orange
                "E": "#E63E11"   # Red
            }
            
            grade = score_data.get("grade", "E")
            score = score_data.get("normalized_score", 0)
            
            # Create results display
            results = [
                html.H4(product_data.get("product_name", "Unknown Product"), className="mb-3"),
                
                # Product information
                html.Div([
                    html.P([
                        html.Strong("Brand: "), 
                        product_data.get("brand", "Unknown")
                    ]),
                    html.P([
                        html.Strong("Source: "), 
                        product_data.get("source", "Unknown")
                    ]),
                    html.P([
                        html.Strong("Confidence: "), 
                        product_data.get("confidence", "Unknown")
                    ])
                ], className="product-info"),
                
                # Nutri-Score display
                html.Div([
                    html.H3("Nutri-Score", className="text-center"),
                    html.Div([
                        html.Div([
                            html.Div(grade, className="badge-grade"),
                            html.Div("Score", className="badge-label")
                        ], className="nutri-score-badge", style={"backgroundColor": color_map.get(grade, "#777")})
                    ]),
                    
                    # Score gauge
                    dcc.Graph(
                        figure=go.Figure(go.Indicator(
                            mode="gauge+number",
                            value=score,
                            title={"text": "Health Score (0-100)"},
                            gauge={
                                "axis": {"range": [0, 100]},
                                "bar": {"color": color_map.get(grade, "#777")},
                                "steps": [
                                    {"range": [0, 20], "color": color_map.get("E")},
                                    {"range": [20, 40], "color": color_map.get("D")},
                                    {"range": [40, 60], "color": color_map.get("C")},
                                    {"range": [60, 80], "color": color_map.get("B")},
                                    {"range": [80, 100], "color": color_map.get("A")}
                                ]
                            }
                        )),
                        config={"displayModeBar": False},
                        style={"height": "300px"}
                    ),
                    
                    # Brief explanation
                    html.Div([
                        html.P(score_data.get("explanation", "").split("\n\n")[0])
                    ])
                ])
            ]
            
            return results
        except Exception as e:
            logger.error(f"Error updating results: {str(e)}")
            return html.P(f"Error displaying results: {str(e)}", style={"color": "red"})

    @app.callback(
        Output("evidence-container", "children"),
        [Input("current-product-data", "data"),
        Input("current-score-data", "data"),
        Input("processing-log", "data")]
    )
    def update_evidence(product_data, score_data, processing_log):
        """Update the evidence panel with detailed analysis."""
        if not product_data or not score_data:
            return html.P("No evidence to display. Please submit product information.", className="placeholder-text")
        
        try:
            # Extract data
            nutrition_data = product_data.get("nutrition_data", {})
            calculation_log = score_data.get("calculation_log", [])
            explanation = score_data.get("explanation", "")
            sources = score_data.get("sources", [])
            
            # Create evidence display
            evidence = [
                # Detailed explanation
                html.Div([
                    html.H4("Explanation"),
                    html.Div([html.P(line) for line in explanation.split("\n") if line])
                ], className="evidence-section"),
                
                # Nutrition Data
                html.Div([
                    html.H4("Nutrition Data (per 100g/ml)"),
                    html.Table([
                        html.Thead([
                            html.Tr([
                                html.Th("Nutrient"),
                                html.Th("Value"),
                                html.Th("Unit")
                            ])
                        ]),
                        html.Tbody([
                            html.Tr([
                                html.Td("Energy"),
                                html.Td(f"{nutrition_data.get('energy_kcal', 0)}"),
                                html.Td("kcal")
                            ]),
                            html.Tr([
                                html.Td("Sugars"),
                                html.Td(f"{nutrition_data.get('sugars_g', 0)}"),
                                html.Td("g")
                            ]),
                            html.Tr([
                                html.Td("Saturated Fat"),
                                html.Td(f"{nutrition_data.get('saturated_fat_g', 0)}"),
                                html.Td("g")
                            ]),
                            html.Tr([
                                html.Td("Salt"),
                                html.Td(f"{nutrition_data.get('salt_g', 0)}"),
                                html.Td("g")
                            ]),
                            html.Tr([
                                html.Td("Fiber"),
                                html.Td(f"{nutrition_data.get('fiber_g', 0)}"),
                                html.Td("g")
                            ]),
                            html.Tr([
                                html.Td("Protein"),
                                html.Td(f"{nutrition_data.get('protein_g', 0)}"),
                                html.Td("g")
                            ]),
                            html.Tr([
                                html.Td("Fruits/Veg/Nuts"),
                                html.Td(f"{nutrition_data.get('fruits_veg_nuts_percent', 0)}"),
                                html.Td("%")
                            ])
                        ])
                    ], className="data-table")
                ], className="evidence-section"),
                
                # Calculation breakdown
                html.Div([
                    html.H4("Score Calculation Breakdown"),
                    
                    # Create bar chart for positive and negative components
                    dcc.Graph(
                        figure=px.bar(
                            data_frame=pd.DataFrame([
                                {
                                    "Component": c["component"].replace("_", " ").title(),
                                    "Points": c["points"],
                                    "Type": "Negative" if c["is_negative"] else "Positive"
                                }
                                for c in calculation_log
                            ]),
                            x="Component",
                            y="Points",
                            color="Type",
                            color_discrete_map={"Positive": "#4CAF50", "Negative": "#F44336"},
                            title="Component Contribution to Score"
                        ),
                        config={"displayModeBar": False},
                        style={"height": "400px"}
                    ),
                    
                    # Detailed calculation table
                    html.Table([
                        html.Thead([
                            html.Tr([
                                html.Th("Component"),
                                html.Th("Value"),
                                html.Th("Points"),
                                html.Th("Impact")
                            ])
                        ]),
                        html.Tbody([
                            html.Tr([
                                html.Td(c["component"].replace("_", " ").title()),
                                html.Td(f"{c['value']}"),
                                html.Td(f"{c['points']}"),
                                html.Td(
                                    "Negative" if c["is_negative"] else "Positive",
                                    style={"color": "#F44336" if c["is_negative"] else "#4CAF50"}
                                )
                            ])
                            for c in calculation_log
                        ])
                    ], className="data-table")
                ], className="evidence-section"),
                
                # Sources and references
                html.Div([
                    html.H4("Sources & References"),
                    html.Ul([html.Li(source) for source in sources]),
                    html.P("The Nutri-Score is based on the 2024 algorithm, which evaluates both negative components (calories, sugars, saturated fat, salt) and positive components (fiber, protein, fruits/vegetables/nuts).")
                ], className="evidence-section"),
                
                # Processing log (for transparency)
                html.Div([
                    html.Div([
                        html.H4("Processing Log"),
                        html.Pre(
                            "\n".join(processing_log) if processing_log else "No processing log available",
                            style={"backgroundColor": "#f8f9fa", "padding": "15px", "borderRadius": "5px"}
                        )
                    ], id="processing-log-content", style={"display": "none"}),
                    html.Button(
                        "Show Processing Log", 
                        id="toggle-processing-log", 
                        className="toggle-button"
                    )
                ], className="evidence-section")
            ]
            
            return evidence
        except Exception as e:
            logger.error(f"Error updating evidence: {str(e)}")
            return html.P(f"Error displaying evidence: {str(e)}", style={"color": "red"})

    @app.callback(
        Output("processing-log-content", "style"),
        [Input("toggle-processing-log", "n_clicks")]
    )
    def toggle_processing_log(n_clicks):
        """Toggle the processing log visibility."""
        if n_clicks and n_clicks % 2 == 1:
            return {"display": "block"}
        return {"display": "none"}

    @app.callback(
        Output("history-container", "children"),
        [Input("current-product-data", "data")]  # Trigger update when new product is processed
    )
    def update_history(_):
        """Update the history display with past searches."""
        try:
            history = product_processor.get_history(limit=5)
            
            if not history:
                return html.P("No search history available.", className="placeholder-text")
            
            # Create history display
            history_items = []
            
            for item in reversed(history):
                # Color for the grade indicator
                color_map = {
                    "A": "#038141",  # Dark Green
                    "B": "#85BB2F",  # Light Green
                    "C": "#FECB02",  # Yellow
                    "D": "#EE8100",  # Orange
                    "E": "#E63E11"   # Red
                }
                
                # Try to determine grade (if we have it in the history)
                grade = "?"
                if "score_data" in item and "grade" in item["score_data"]:
                    grade = item["score_data"]["grade"]
                
                # Create history item
                history_item = html.Div([
                    html.Div([
                        html.Div([
                            html.Div(grade, className="history-grade", 
                                style={"backgroundColor": color_map.get(grade, "#777")})
                        ], className="history-grade-container"),
                        html.Div([
                            html.H5(item.get("product_name", "Unknown Product")),
                            html.P([
                                html.Small(f"Source: {item.get('source', 'Unknown')} | "),
                                html.Small(f"Confidence: {item.get('confidence', 'Unknown')}")
                            ], className="history-meta")
                        ], className="history-details")
                    ], className="history-item-inner")
                ], className="history-item")
                
                history_items.append(history_item)
            
            return html.Div(history_items, className="history-list")
        except Exception as e:
            logger.error(f"Error updating history: {str(e)}")
            return html.P(f"Error loading history: {str(e)}", style={"color": "red"})
            
    # Add custom CSS
    app.index_string = '''
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%favicon%}
            {%css%}
            <style>
                /* Base styles */
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f7fa;
                    color: #333;
                }
                
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }
                
                /* Header */
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                }
                
                .header-title {
                    color: #2c3e50;
                    margin-bottom: 10px;
                }
                
                .header-description {
                    color: #7f8c8d;
                    font-size: 18px;
                }
                
                /* Card styles */
                .card {
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                    margin-bottom: 25px;
                    overflow: hidden;
                }
                
                .card-header {
                    background-color: #3498db;
                    color: white;
                    padding: 15px 20px;
                    margin: 0;
                }
                
                .card-body {
                    padding: 20px;
                }
                
                /* Row and column layout */
                .row {
                    display: flex;
                    flex-wrap: wrap;
                    margin: 0 -10px;
                }
                
                .column {
                    flex: 1;
                    padding: 0 10px;
                    min-width: 300px;
                }
                
                /* Form elements */
                .input-field {
                    width: 100%;
                    padding: 10px;
                    margin-bottom: 15px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
                
                .text-input-area {
                    width: 100%;
                    height: 200px;
                    padding: 10px;
                    margin-bottom: 15px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    resize: vertical;
                }
                
                .upload-area {
                    width: 100%;
                    height: 60px;
                    line-height: 60px;
                    border-width: 1px;
                    border-style: dashed;
                    border-radius: 5px;
                    text-align: center;
                    margin: 10px 0;
                    background-color: #f8f9fa;
                    cursor: pointer;
                }
                
                .preview-area {
                    margin-top: 15px;
                }
                
                .submit-button {
                    background-color: #2ecc71;
                    color: white;
                    border: none;
                    padding: 12px 20px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 16px;
                    width: 100%;
                    transition: background-color 0.3s;
                }
                
                .submit-button:hover {
                    background-color: #27ae60;
                }
                
                /* Tabs */
                .tab-content {
                    padding: 15px 0;
                }
                
                /* Placeholder text */
                .placeholder-text {
                    color: #95a5a6;
                    text-align: center;
                }
                
                /* Nutri-Score badge */
                .nutri-score-badge {
                    border-radius: 50%;
                    width: 120px;
                    height: 120px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    margin: 0 auto;
                    color: white;
                    text-align: center;
                }
                
                .badge-grade {
                    font-size: 48px;
                    font-weight: bold;
                }
                
                .badge-label {
                    font-size: 14px;
                }
                
                /* Tables */
                .data-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                }
                
                .data-table th, .data-table td {
                    padding: 10px;
                    border: 1px solid #ddd;
                }
                
                .data-table th {
                    background-color: #f2f2f2;
                    text-align: left;
                }
                
                /* History items */
                .history-list {
                    margin-top: 15px;
                }
                
                .history-item {
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    margin-bottom: 10px;
                    background-color: #fff;
                }
                
                .history-item-inner {
                    display: flex;
                    padding: 10px;
                }
                
                .history-grade-container {
                    margin-right: 15px;
                }
                
                .history-grade {
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                }
                
                .history-details {
                    flex: 1;
                }
                
                .history-details h5 {
                    margin: 0 0 5px 0;
                }
                
                .history-meta {
                    margin: 0;
                    color: #7f8c8d;
                }
                
                /* Evidence sections */
                .evidence-section {
                    margin-bottom: 30px;
                }
                
                /* Buttons */
                .toggle-button {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 14px;
                }
                
                /* Responsive adjustments */
                @media (max-width: 768px) {
                    .row {
                        flex-direction: column;
                    }
                    .column {
                        width: 100%;
                    }
                }
            </style>
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    '''
