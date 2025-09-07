import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import base64
import io
import json
from PIL import Image
import logging

# Import our custom modules
from src.utils.barcode_detector import detect_barcode_from_image, has_barcode
from src.backend.nutri_score import NutriScoreCalculator
from src.backend.product_processor import ProductDataProcessor
from src.backend.langgraph_processor import LangGraphProcessor
from src.utils.enhanced_data import EnhancedHistoryManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize components
nutri_score_calculator = NutriScoreCalculator()
product_processor = ProductDataProcessor()
llm_processor = LangGraphProcessor()  # Using LangGraph processor instead of OpenAI
history_manager = EnhancedHistoryManager()  # Initialize history manager

# EU Reference values per Regulation 1169/2011
EU_REFERENCE_VALUES = {
    "energy_kcal": 2000,
    "energy_kj": 8400,
    "total_fat_g": 70,
    "saturated_fat_g": 20,
    "carbohydrates_g": 260,
    "sugars_g": 90,
    "protein_g": 50,
    "salt_g": 6,
    "fiber_g": 25  # Not in regulation but commonly used reference
}

# Define default settings
DEFAULT_SETTINGS = {
    'language': 'en',
    'unit_system': 'metric',
    'high_contrast': False,
    'large_text': False
}

# Initialize the Dash app
app = dash.Dash(__name__, 
               external_stylesheets=[
                   dbc.themes.BOOTSTRAP,
                   "https://use.fontawesome.com/releases/v5.15.4/css/all.css"
               ],
               suppress_callback_exceptions=True)  # Suppress exceptions for callbacks to components created dynamically
app.title = "Health Rater - Nutrition Score Calculator"

# Define the layout
app.layout = html.Div([
    # Navigation Bar
    dbc.Navbar(
        dbc.Container([
            dbc.NavbarBrand("Health Rater", className="ms-2"),
            dbc.NavbarToggler(id="navbar-toggler"),
            dbc.Collapse(
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink("Home", href="#")),
                    dbc.NavItem(dbc.NavLink("Compare Products", id="compare-nav-link", href="#")),
                    dbc.NavItem(dbc.NavLink("Search History", id="history-nav-link", href="#")),
                    dbc.DropdownMenu(
                        [
                            dbc.DropdownMenuItem("Settings", id="settings-button"),
                            dbc.DropdownMenuItem("Language", header=True),
                            dbc.DropdownMenuItem("English", id="lang-en"),
                            dbc.DropdownMenuItem("Français", id="lang-fr"),
                            dbc.DropdownMenuItem("Español", id="lang-es"),
                            dbc.DropdownMenuItem("Deutsch", id="lang-de"),
                        ],
                        nav=True,
                        label="Options",
                    ),
                ], className="ms-auto", navbar=True),
                id="navbar-collapse",
                navbar=True,
            ),
        ], fluid=True),
        color="primary",
        dark=True,
        className="mb-4",
    ),
    
    # Main container
    dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H1("Health Rater", className="text-center my-4"),
                html.P("Calculate the health score of food products using the Nutri-Score algorithm.", 
                       className="text-center lead mb-4"),
            ], width=12)
        ]),
    
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Input Methods"),
                    dbc.CardBody([
                        dbc.Tabs([
                            dbc.Tab(label="Barcode", tab_id="tab-barcode", children=[
                                html.Div([
                                    html.H5("Enter Barcode Number", className="mt-3"),
                                    dbc.Input(id="barcode-input", type="text", placeholder="Enter barcode number...", className="mb-3"),
                                    html.H5("Or Upload Barcode Image", className="mt-3"),
                                    dcc.Upload(
                                        id="upload-barcode-image",
                                        children=html.Div([
                                            'Drag and Drop or ',
                                            html.A('Select a File')
                                        ]),
                                        style={
                                            'width': '100%',
                                            'height': '60px',
                                            'lineHeight': '60px',
                                            'borderWidth': '1px',
                                            'borderStyle': 'dashed',
                                            'borderRadius': '5px',
                                            'textAlign': 'center',
                                            'margin': '10px 0'
                                        },
                                        multiple=False
                                    ),
                                    html.Div(id="barcode-image-preview", className="mt-3")
                                ])
                            ]),
                            dbc.Tab(label="Product Photo", tab_id="tab-photo", children=[
                                html.Div([
                                    html.H5("Upload Product Label Photo", className="mt-3"),
                                    dcc.Upload(
                                        id="upload-product-photo",
                                        children=html.Div([
                                            'Drag and Drop or ',
                                            html.A('Select a File')
                                        ]),
                                        style={
                                            'width': '100%',
                                            'height': '60px',
                                            'lineHeight': '60px',
                                            'borderWidth': '1px',
                                            'borderStyle': 'dashed',
                                            'borderRadius': '5px',
                                            'textAlign': 'center',
                                            'margin': '10px 0'
                                        },
                                        multiple=False
                                    ),
                                    html.Div(id="photo-preview", className="mt-3")
                                ])
                            ]),
                            dbc.Tab(label="Text Input", tab_id="tab-text", children=[
                                html.Div([
                                    html.H5("Enter Product Information", className="mt-3"),
                                    dbc.Textarea(id="text-input", 
                                        placeholder="Enter product information (e.g., nutrition facts, ingredients)...",
                                        style={"height": "200px"},
                                        className="mb-3"
                                    )
                                ])
                            ])
                        ], id="tabs", active_tab="tab-barcode"),
                        dbc.Button("Calculate Health Score", id="submit-button", color="primary", className="w-100 mt-3")
                    ])
                ], className="mb-4")
            ], width=12, md=6),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Results"),
                    dbc.CardBody([
                        html.Div(id="results-container", children=[
                            html.P("Enter product information and click 'Calculate Health Score' to see results.", className="text-center text-muted")
                        ])
                    ])
                ], className="mb-4 h-100")
            ], width=12, md=6)
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        dbc.Row([
                            dbc.Col(html.H5("Evidence & Detailed Analysis"), width="auto"),
                            dbc.Col(
                                dbc.Button(
                                    "Show/Hide",
                                    id="toggle-evidence",
                                    color="link",
                                    size="sm",
                                    className="float-right"
                                ),
                                width="auto",
                                className="ml-auto"
                            ),
                        ], justify="between", align="center"),
                    ]),
                    dbc.Collapse(
                        dbc.CardBody([
                            html.Div(id="evidence-container", children=[
                                html.P("Detailed analysis will appear here after calculation.", className="text-center text-muted")
                            ])
                        ]),
                        id="evidence-collapse",
                        is_open=True,
                    )
                ], className="mb-4")
            ], width=12)
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Search History"),
                    dbc.CardBody([
                        html.Div(id="history-container", children=[
                            html.P("Your search history will appear here.", className="text-center text-muted")
                        ])
                    ])
                ], className="mb-4")
            ], width=12)
        ])
    ], fluid=True, className="py-3"),
    
    # Store components for intermediate data
    dcc.Store(id="current-product-data"),
    dcc.Store(id="current-score-data"),
    dcc.Store(id="detected-barcode-data"),
    dcc.Store(id="processing-log"),
    dcc.Store(id="app-settings", data=DEFAULT_SETTINGS),
])

# Define callbacks
@app.callback(
    [Output("barcode-image-preview", "children"), 
     Output("detected-barcode-data", "data"),
     Output("barcode-input", "value")],  # Added output for barcode input field
    [Input("upload-barcode-image", "contents")],
    [State("upload-barcode-image", "filename")]
)
def update_barcode_preview(contents, filename):
    """Process uploaded barcode image and detect barcode."""
    if contents is None:
        return None, None, None
    
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
        
        # Return detected barcode value for the input field
        barcode_value = barcode_data['data'] if barcode_data else ""
        
        return preview, barcode_data, barcode_value
    except Exception as e:
        logger.error(f"Error processing barcode image: {str(e)}")
        return html.Div(f"Error processing image: {str(e)}"), None, None

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

# Use a dictionary to cache results instead of lru_cache to avoid issues with mutable objects
_barcode_cache = {}

def process_barcode(barcode):
    """Process barcode data with caching to avoid repeated API calls."""
    if barcode in _barcode_cache:
        return _barcode_cache[barcode]
    result = product_processor.process_barcode_data(barcode)
    _barcode_cache[barcode] = result
    return result

@app.callback(
    [Output("current-product-data", "data"),
     Output("current-score-data", "data"),
     Output("processing-log", "data")],
    [Input("submit-button", "n_clicks")],
    [State("tabs", "active_tab"),
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
    product_data = None
    
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
            
            # Process barcode data with caching
            product_data = process_barcode(barcode)
            if not product_data:
                processing_log.append(f"No product found for barcode: {barcode}")
                return None, None, processing_log
            
            processing_log.append(f"Successfully retrieved product data for barcode: {barcode}")
            
        elif active_tab == "tab-photo":
            if not photo_contents:
                processing_log.append("No photo uploaded")
                return None, None, processing_log
            
            try:
                # Decode the base64 image
                content_type, content_string = photo_contents.split(',')
                decoded = base64.b64decode(content_string)
                
                # Process the image
                with Image.open(io.BytesIO(decoded)) as image:
                    # Check if image contains barcode
                    if has_barcode(image):
                        # Detect and process barcode
                        barcode_data = detect_barcode_from_image(image)
                        if barcode_data and "data" in barcode_data:
                            barcode = barcode_data.get("data")
                            processing_log.append(f"Detected barcode in image: {barcode}")
                            
                            # Process barcode data with caching
                            product_data = process_barcode(barcode)
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
            except Exception as img_error:
                logger.error(f"Error processing image: {str(img_error)}")
                processing_log.append(f"Error processing image: {str(img_error)}")
                return None, None, processing_log
        
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
            try:
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
                
                # Save to history if enabled
                try:
                    history_manager.add_to_history(product_data, score_data)
                    processing_log.append("Product added to history")
                except Exception as hist_error:
                    logger.error(f"Error adding to history: {str(hist_error)}")
                    processing_log.append(f"Note: Could not add to history: {str(hist_error)}")
                
                return product_data, score_data, processing_log
            except Exception as score_error:
                logger.error(f"Error calculating score: {str(score_error)}")
                processing_log.append(f"Error calculating score: {str(score_error)}")
                return product_data, None, processing_log
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
        return html.P("No results to display. Please submit product information.", className="text-center text-muted")
    
    try:
        # Color mapping for Nutri-Score grades - moved outside function for better performance
        color_map = {
            "A": "#038141",  # Dark Green
            "B": "#85BB2F",  # Light Green
            "C": "#FECB02",  # Yellow
            "D": "#EE8100",  # Orange
            "E": "#E63E11"   # Red
        }
        
        grade = score_data.get("grade", "E")
        score = score_data.get("normalized_score", 0)
        
        # Create results display with optimized structure
        return [
            html.H4(product_data.get("product_name", "Unknown Product"), className="mb-3"),
            
            # Product information - simplified
            html.Div([
                html.P([html.Strong("Brand: "), product_data.get("brand", "Unknown")]),
                html.P([html.Strong("Source: "), product_data.get("source", "Unknown")]),
                html.P([html.Strong("Confidence: "), product_data.get("confidence", "Unknown")])
            ], className="mb-4"),
            
            # Nutri-Score display
            html.Div([
                html.H3("Nutri-Score", className="text-center mb-3"),
                
                # Score badge
                html.Div([
                    html.Div([
                        html.Div(grade, className="display-4 text-center text-white font-weight-bold"),
                        html.Div("Score", className="text-center text-white")
                    ], style={
                        "backgroundColor": color_map.get(grade, "#777"),
                        "borderRadius": "50%",
                        "width": "120px",
                        "height": "120px",
                        "display": "flex",
                        "flexDirection": "column",
                        "justifyContent": "center",
                        "margin": "0 auto"
                    })
                ], className="mb-4"),
                
                # Score gauge - Simplified for better performance
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
                
                # Brief explanation - take only first paragraph for performance
                html.Div([
                    html.P(score_data.get("explanation", "").split("\n\n")[0] if score_data.get("explanation") else "", 
                           className="mt-3")
                ])
            ])
        ]
    except Exception as e:
        logger.error(f"Error updating results: {str(e)}")
        return html.P(f"Error displaying results: {str(e)}", className="text-danger")

@app.callback(
    Output("evidence-container", "children"),
    [Input("current-product-data", "data"),
     Input("current-score-data", "data"),
     Input("processing-log", "data")]
)
def update_evidence(product_data, score_data, processing_log):
    """Update the evidence panel with detailed analysis."""
    if not product_data or not score_data:
        return html.P("No evidence to display. Please submit product information.", className="text-center text-muted")
    
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
                html.H4("Explanation", className="mb-3"),
                html.Div([html.P(line, className="mb-1") for line in explanation.split("\n") if line])
            ], className="mb-4"),
            
            # Enhanced Nutrition Data with EU Standards and Ratings
            html.Div([
                html.H4("Nutrition Data (per 100g/ml)", className="mb-3"),
                html.P("Based on EU Regulation 1169/2011 standards", className="text-muted mb-3"),
                dbc.Table([
                    html.Thead([
                        html.Tr([
                            html.Th("Nutrient"),
                            html.Th("Value"),
                            html.Th("EU Reference"),
                            html.Th("% of Reference"),
                            html.Th("Points"),
                            html.Th("Rating"),
                            html.Th("Impact")
                        ])
                    ]),
                    html.Tbody([
                        # Energy - Negative component
                        html.Tr([
                            html.Td("Energy"),
                            html.Td(f"{nutrition_data.get('energy_kcal', 0)} kcal ({round(nutrition_data.get('energy_kcal', 0) * 4.184)} kJ)"),
                            html.Td("2000 kcal"),
                            html.Td(f"{round((nutrition_data.get('energy_kcal', 0) / 2000) * 100, 1)}%"),
                            html.Td(
                                next((str(c["points"]) for c in calculation_log if c["component"] == "energy_calories"), "0"),
                                className="font-weight-bold text-danger"
                            ),
                            html.Td(
                                dbc.Badge(
                                    "HIGH" if nutrition_data.get('energy_kcal', 0) > 400 else 
                                    "MEDIUM" if nutrition_data.get('energy_kcal', 0) > 240 else "LOW", 
                                    color="danger" if nutrition_data.get('energy_kcal', 0) > 400 else 
                                    "warning" if nutrition_data.get('energy_kcal', 0) > 240 else "success"
                                )
                            ),
                            html.Td(html.I(className="fas fa-arrow-down text-danger"))
                        ], style={"backgroundColor": "#fff8f8" if nutrition_data.get('energy_kcal', 0) > 240 else ""}),
                        
                        # Sugars - Negative component
                        html.Tr([
                            html.Td("Sugars"),
                            html.Td(f"{nutrition_data.get('sugars_g', 0)} g"),
                            html.Td("90 g"),
                            html.Td(f"{round((nutrition_data.get('sugars_g', 0) / 90) * 100, 1)}%"),
                            html.Td(
                                next((str(c["points"]) for c in calculation_log if c["component"] == "sugars"), "0"),
                                className="font-weight-bold text-danger"
                            ),
                            html.Td(
                                dbc.Badge(
                                    "HIGH" if nutrition_data.get('sugars_g', 0) > 22.5 else 
                                    "MEDIUM" if nutrition_data.get('sugars_g', 0) > 13.5 else "LOW", 
                                    color="danger" if nutrition_data.get('sugars_g', 0) > 22.5 else 
                                    "warning" if nutrition_data.get('sugars_g', 0) > 13.5 else "success"
                                )
                            ),
                            html.Td(html.I(className="fas fa-arrow-down text-danger"))
                        ], style={"backgroundColor": "#fff8f8" if nutrition_data.get('sugars_g', 0) > 13.5 else ""}),
                        
                        # Saturated Fat - Negative component
                        html.Tr([
                            html.Td("Saturated Fat"),
                            html.Td(f"{nutrition_data.get('saturated_fat_g', 0)} g"),
                            html.Td("20 g"),
                            html.Td(f"{round((nutrition_data.get('saturated_fat_g', 0) / 20) * 100, 1)}%"),
                            html.Td(
                                next((str(c["points"]) for c in calculation_log if c["component"] == "saturated_fatty_acids"), "0"),
                                className="font-weight-bold text-danger"
                            ),
                            html.Td(
                                dbc.Badge(
                                    "HIGH" if nutrition_data.get('saturated_fat_g', 0) > 5 else 
                                    "MEDIUM" if nutrition_data.get('saturated_fat_g', 0) > 3 else "LOW", 
                                    color="danger" if nutrition_data.get('saturated_fat_g', 0) > 5 else 
                                    "warning" if nutrition_data.get('saturated_fat_g', 0) > 3 else "success"
                                )
                            ),
                            html.Td(html.I(className="fas fa-arrow-down text-danger"))
                        ], style={"backgroundColor": "#fff8f8" if nutrition_data.get('saturated_fat_g', 0) > 3 else ""}),
                        
                        # Salt - Negative component
                        html.Tr([
                            html.Td("Salt"),
                            html.Td(f"{nutrition_data.get('salt_g', 0)} g ({round(nutrition_data.get('salt_g', 0) * 400)} mg sodium)"),
                            html.Td("6 g"),
                            html.Td(f"{round((nutrition_data.get('salt_g', 0) / 6) * 100, 1)}%"),
                            html.Td(
                                next((str(c["points"]) for c in calculation_log if c["component"] == "salt_sodium"), "0"),
                                className="font-weight-bold text-danger"
                            ),
                            html.Td(
                                dbc.Badge(
                                    "HIGH" if nutrition_data.get('salt_g', 0) > 1.5 else 
                                    "MEDIUM" if nutrition_data.get('salt_g', 0) > 0.9 else "LOW", 
                                    color="danger" if nutrition_data.get('salt_g', 0) > 1.5 else 
                                    "warning" if nutrition_data.get('salt_g', 0) > 0.9 else "success"
                                )
                            ),
                            html.Td(html.I(className="fas fa-arrow-down text-danger"))
                        ], style={"backgroundColor": "#fff8f8" if nutrition_data.get('salt_g', 0) > 0.9 else ""}),
                        
                        # Fiber - Positive component
                        html.Tr([
                            html.Td("Fiber"),
                            html.Td(f"{nutrition_data.get('fiber_g', 0)} g"),
                            html.Td("25 g"),
                            html.Td(f"{round((nutrition_data.get('fiber_g', 0) / 25) * 100, 1)}%"),
                            html.Td(
                                next((str(c["points"]) for c in calculation_log if c["component"] == "fiber"), "0"),
                                className="font-weight-bold text-success"
                            ),
                            html.Td(
                                dbc.Badge(
                                    "HIGH" if nutrition_data.get('fiber_g', 0) > 3.7 else 
                                    "MEDIUM" if nutrition_data.get('fiber_g', 0) > 1.9 else "LOW", 
                                    color="success" if nutrition_data.get('fiber_g', 0) > 1.9 else 
                                    "warning" if nutrition_data.get('fiber_g', 0) > 0.9 else "danger"
                                )
                            ),
                            html.Td(html.I(className="fas fa-arrow-up text-success"))
                        ], style={"backgroundColor": "#f8fff8" if nutrition_data.get('fiber_g', 0) > 1.9 else ""}),
                        
                        # Protein - Positive component
                        html.Tr([
                            html.Td("Protein"),
                            html.Td(f"{nutrition_data.get('protein_g', 0)} g"),
                            html.Td("50 g"),
                            html.Td(f"{round((nutrition_data.get('protein_g', 0) / 50) * 100, 1)}%"),
                            html.Td(
                                next((str(c["points"]) for c in calculation_log if c["component"] == "protein"), "0"),
                                className="font-weight-bold text-success"
                            ),
                            html.Td(
                                dbc.Badge(
                                    "HIGH" if nutrition_data.get('protein_g', 0) > 8.0 else 
                                    "MEDIUM" if nutrition_data.get('protein_g', 0) > 4.8 else "LOW", 
                                    color="success" if nutrition_data.get('protein_g', 0) > 4.8 else 
                                    "warning" if nutrition_data.get('protein_g', 0) > 1.6 else "danger"
                                )
                            ),
                            html.Td(html.I(className="fas fa-arrow-up text-success"))
                        ], style={"backgroundColor": "#f8fff8" if nutrition_data.get('protein_g', 0) > 4.8 else ""}),
                        
                        # Fruits/Veg/Nuts - Positive component
                        html.Tr([
                            html.Td("Fruits/Veg/Nuts"),
                            html.Td(f"{nutrition_data.get('fruits_veg_nuts_percent', 0)} %"),
                            html.Td("N/A"),
                            html.Td("N/A"),
                            html.Td(
                                next((str(c["points"]) for c in calculation_log if c["component"] == "fruits_vegetables_legumes_nuts"), "0"),
                                className="font-weight-bold text-success"
                            ),
                            html.Td(
                                dbc.Badge(
                                    "HIGH" if nutrition_data.get('fruits_veg_nuts_percent', 0) > 80 else 
                                    "MEDIUM" if nutrition_data.get('fruits_veg_nuts_percent', 0) > 60 else "LOW", 
                                    color="success" if nutrition_data.get('fruits_veg_nuts_percent', 0) > 60 else 
                                    "warning" if nutrition_data.get('fruits_veg_nuts_percent', 0) > 40 else "danger"
                                )
                            ),
                            html.Td(html.I(className="fas fa-arrow-up text-success"))
                        ], style={"backgroundColor": "#f8fff8" if nutrition_data.get('fruits_veg_nuts_percent', 0) > 60 else ""})
                    ])
                ], bordered=True, hover=True, responsive=True, striped=True),
                html.Div([
                    html.P([
                        html.I(className="fas fa-arrow-down text-danger mr-2"),
                        "Negative components: Lower is better (adds to score)"
                    ], className="small mt-2"),
                    html.P([
                        html.I(className="fas fa-arrow-up text-success mr-2"),
                        "Positive components: Higher is better (subtracts from score)"
                    ], className="small")
                ])
            ], className="mb-4"),
            
            # Sources and references
            html.Div([
                html.H4("Sources & References", className="mb-3"),
                html.Ul([html.Li(source) for source in sources]),
                html.P("The Nutri-Score is based on the 2024 algorithm, which evaluates both negative components (calories, sugars, saturated fat, salt) and positive components (fiber, protein, fruits/vegetables/nuts).", className="mt-3")
            ], className="mb-4"),
            
            # Processing log (for transparency)
            dbc.Collapse([
                html.H4("Processing Log", className="mb-3"),
                html.Pre(
                    "\n".join(processing_log) if processing_log else "No processing log available",
                    style={"backgroundColor": "#f8f9fa", "padding": "15px", "borderRadius": "5px"}
                )
            ], id="processing-log-collapse", is_open=False),
            dbc.Button(
                "Show Processing Log", 
                id="toggle-processing-log", 
                color="secondary",
                size="sm",
                className="mt-2"
            )
        ]
        
        return evidence
    except Exception as e:
        logger.error(f"Error updating evidence: {str(e)}")
        return html.P(f"Error displaying evidence: {str(e)}", className="text-danger")

@app.callback(
    Output("evidence-collapse", "is_open"),
    [Input("toggle-evidence", "n_clicks")],
    [State("evidence-collapse", "is_open")]
)
def toggle_evidence(n_clicks, is_open):
    """Toggle the evidence collapse."""
    if n_clicks:
        return not is_open
    return is_open

@app.callback(
    Output("processing-log-collapse", "is_open"),
    [Input("toggle-processing-log", "n_clicks")],
    [State("processing-log-collapse", "is_open")]
)
def toggle_processing_log(n_clicks, is_open):
    """Toggle the processing log collapse."""
    if n_clicks:
        return not is_open
    return is_open

@app.callback(
    Output("history-container", "children"),
    [Input("current-product-data", "data")]  # Trigger update when new product is processed
)
def update_history(_):
    """Update the history display with past searches."""
    try:
        history = product_processor.get_history(limit=5)
        
        if not history:
            return html.P("No search history available.", className="text-center text-muted")
        
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
            history_item = dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div(grade, className="text-center text-white font-weight-bold", style={
                                "backgroundColor": color_map.get(grade, "#777"),
                                "borderRadius": "50%",
                                "width": "40px",
                                "height": "40px",
                                "lineHeight": "40px"
                            })
                        ], width=2),
                        dbc.Col([
                            html.H5(item.get("product_name", "Unknown Product"), className="mb-1"),
                            html.P([
                                html.Small(f"Source: {item.get('source', 'Unknown')} | "),
                                html.Small(f"Confidence: {item.get('confidence', 'Unknown')}")
                            ], className="text-muted mb-0")
                        ], width=8),
                        dbc.Col([
                            html.Button(
                                html.I(className="fas fa-trash text-danger"),
                                id={"type": "delete-history", "index": history.index(item)},
                                className="btn btn-outline-light border-0",
                                title="Delete from history"
                            )
                        ], width=2, className="d-flex justify-content-end align-items-center")
                    ])
                ])
            ], className="mb-2")
            
            history_items.append(history_item)
        
        return html.Div(history_items)
    except Exception as e:
        logger.error(f"Error updating history: {str(e)}")
        return html.P(f"Error loading history: {str(e)}", className="text-danger")

# Add the entry point back
# Entry point
if __name__ == "__main__":
    app.run_server(debug=True)

# Callback for deleting history items
@app.callback(
    Output("history-container", "children", allow_duplicate=True),
    [Input({"type": "delete-history", "index": dash.dependencies.ALL}, "n_clicks")],
    [State({"type": "delete-history", "index": dash.dependencies.ALL}, "id")],
    prevent_initial_call=True
)
def delete_history_item(n_clicks, ids):
    """Delete an item from the search history."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    
    # Get the ID of the button that was clicked
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    try:
        # Parse the JSON string to get the index
        parsed_id = json.loads(button_id)
        index = parsed_id.get('index')
        
        # Delete the entry
        if product_processor.delete_history_entry(index):
            # Return updated history
            return update_history(None)
        else:
            return dash.no_update
    except Exception as e:
        logger.error(f"Error deleting history item: {str(e)}")
        return dash.no_update
