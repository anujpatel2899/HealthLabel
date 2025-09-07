"""
Enhanced UI components for Health Rater application.
"""

from dash import html
import dash_bootstrap_components as dbc

# Create the settings modal
def create_settings_modal():
    """Create the settings modal component."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Settings")),
            dbc.ModalBody([
                # Language Settings
                html.Div([
                    html.H5("Language", className="mb-3"),
                    dbc.RadioItems(
                        options=[
                            {"label": "English", "value": "en"},
                            {"label": "Français", "value": "fr"},
                            {"label": "Español", "value": "es"},
                            {"label": "Deutsch", "value": "de"},
                        ],
                        value="en",
                        id="language-setting",
                        inline=True,
                        className="mb-4"
                    ),
                ]),
                
                # Unit System Settings
                html.Div([
                    html.H5("Unit System", className="mb-3"),
                    dbc.RadioItems(
                        options=[
                            {"label": "Metric (g, ml)", "value": "metric"},
                            {"label": "Imperial (oz, fl oz)", "value": "imperial"},
                        ],
                        value="metric",
                        id="unit-system-setting",
                        inline=True,
                        className="mb-4"
                    ),
                ]),
                
                # Accessibility Settings
                html.Div([
                    html.H5("Accessibility", className="mb-3"),
                    dbc.Checklist(
                        options=[
                            {"label": "High Contrast Mode", "value": "high-contrast"},
                            {"label": "Large Text", "value": "large-text"},
                        ],
                        value=[],
                        id="accessibility-settings",
                        className="mb-4",
                        switch=True,
                    ),
                ]),
            ]),
            dbc.ModalFooter([
                dbc.Button("Close", id="close-settings", className="ms-auto"),
                dbc.Button("Save", id="save-settings", color="primary")
            ]),
        ],
        id="settings-modal",
        size="lg",
        is_open=False,
    )

# Create the compare products modal
def create_compare_modal():
    """Create the compare products modal component."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Compare Products")),
            dbc.ModalBody([
                html.Div([
                    html.P("Select products from your history to compare side by side.", className="mb-3"),
                    html.Div(id="compare-products-container", className="mb-3"),
                    html.Div(id="comparison-results", className="mt-4"),
                ]),
            ]),
            dbc.ModalFooter([
                dbc.Button("Close", id="close-compare", className="ms-auto"),
                dbc.Button("Export Comparison", id="export-comparison", color="primary", disabled=True)
            ]),
        ],
        id="compare-modal",
        size="xl",
        is_open=False,
    )

# Create the export/share modal
def create_export_modal():
    """Create the export/share modal component."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Export/Share Results")),
            dbc.ModalBody([
                html.Div([
                    html.P("Choose how you'd like to export or share your results:", className="mb-3"),
                    dbc.ListGroup([
                        dbc.ListGroupItem([
                            html.Div([
                                html.I(className="fas fa-file-pdf me-2"),
                                "Export as PDF"
                            ]),
                            dbc.Button("Export", id="export-pdf", color="primary", size="sm", className="ms-auto")
                        ], className="d-flex justify-content-between align-items-center"),
                        dbc.ListGroupItem([
                            html.Div([
                                html.I(className="fas fa-image me-2"),
                                "Export as Image"
                            ]),
                            dbc.Button("Export", id="export-image", color="primary", size="sm", className="ms-auto")
                        ], className="d-flex justify-content-between align-items-center"),
                        dbc.ListGroupItem([
                            html.Div([
                                html.I(className="fas fa-file-csv me-2"),
                                "Export Data as CSV"
                            ]),
                            dbc.Button("Export", id="export-csv", color="primary", size="sm", className="ms-auto")
                        ], className="d-flex justify-content-between align-items-center"),
                        dbc.ListGroupItem([
                            html.Div([
                                html.I(className="fas fa-share-alt me-2"),
                                "Share Link"
                            ]),
                            dbc.Button("Copy Link", id="copy-link", color="primary", size="sm", className="ms-auto")
                        ], className="d-flex justify-content-between align-items-center"),
                    ], className="mb-3"),
                    html.Div(id="export-status", className="mt-3")
                ]),
            ]),
            dbc.ModalFooter([
                dbc.Button("Close", id="close-export", className="ms-auto"),
            ]),
        ],
        id="export-modal",
        size="md",
        is_open=False,
    )

# Create the search history modal
def create_history_modal():
    """Create the search history modal component."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Search History")),
            dbc.ModalBody([
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            dbc.Input(
                                id="history-search-input",
                                placeholder="Search history...",
                                type="text",
                                className="mb-3"
                            ),
                        ], width=9),
                        dbc.Col([
                            dbc.Button(
                                "Search",
                                id="history-search-button",
                                color="primary",
                                className="w-100"
                            ),
                        ], width=3),
                    ]),
                    html.Div(id="history-search-results", className="mt-3"),
                    dbc.Button(
                        "Clear History",
                        id="clear-history-button",
                        color="danger",
                        size="sm",
                        className="mt-3"
                    ),
                ]),
            ]),
            dbc.ModalFooter([
                dbc.Button("Close", id="close-history", className="ms-auto"),
            ]),
        ],
        id="history-modal",
        size="lg",
        is_open=False,
    )

# Create a product card for comparison
def create_product_card(product_data, score_data):
    """Create a product card for the comparison view."""
    if not product_data or not score_data:
        return html.Div("No product data available")
    
    # Color mapping for Nutri-Score grades
    color_map = {
        "A": "#038141",  # Dark Green
        "B": "#85BB2F",  # Light Green
        "C": "#FECB02",  # Yellow
        "D": "#EE8100",  # Orange
        "E": "#E63E11"   # Red
    }
    
    grade = score_data.get("grade", "E")
    
    return dbc.Card([
        dbc.CardHeader([
            html.H5(product_data.get("product_name", "Unknown Product"), className="mb-0"),
            html.Div([
                html.Span(
                    grade,
                    style={
                        "backgroundColor": color_map.get(grade, "#777"),
                        "color": "white",
                        "borderRadius": "50%",
                        "width": "30px",
                        "height": "30px",
                        "display": "inline-flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "fontWeight": "bold",
                    }
                )
            ], className="ms-auto")
        ], className="d-flex justify-content-between align-items-center"),
        dbc.CardBody([
            # Product information
            html.Div([
                html.P([
                    html.Strong("Brand: "), 
                    product_data.get("brand", "Unknown")
                ], className="mb-1"),
                html.P([
                    html.Strong("Source: "), 
                    product_data.get("source", "Unknown")
                ], className="mb-1"),
                
                # Brief nutritional highlights
                html.H6("Nutrition Highlights:", className="mt-3 mb-2"),
                dbc.Table([
                    html.Tbody([
                        html.Tr([
                            html.Td("Energy"),
                            html.Td(f"{product_data.get('nutrition_data', {}).get('energy_kcal', 0)} kcal")
                        ]),
                        html.Tr([
                            html.Td("Sugars"),
                            html.Td(f"{product_data.get('nutrition_data', {}).get('sugars_g', 0)} g")
                        ]),
                        html.Tr([
                            html.Td("Sat. Fat"),
                            html.Td(f"{product_data.get('nutrition_data', {}).get('saturated_fat_g', 0)} g")
                        ]),
                        html.Tr([
                            html.Td("Salt"),
                            html.Td(f"{product_data.get('nutrition_data', {}).get('salt_g', 0)} g")
                        ]),
                    ])
                ], bordered=True, size="sm", className="mb-3"),
                
                # Score value
                html.Div([
                    html.Strong("Health Score: "),
                    f"{score_data.get('normalized_score', 0)}/100"
                ], className="mb-3"),
                
                # Action buttons
                html.Div([
                    dbc.Button("View Details", color="primary", size="sm", className="me-2"),
                    dbc.Button("Remove", color="danger", size="sm", outline=True),
                ], className="d-flex justify-content-between")
            ])
        ])
    ], className="h-100")

# Function to create a history item with actions
def create_history_item(item, index):
    """Create a history item with action buttons."""
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
    
    return dbc.ListGroupItem([
        # Left side - grade indicator and product info
        html.Div([
            html.Div([
                html.Div(
                    grade,
                    style={
                        "backgroundColor": color_map.get(grade, "#777"),
                        "color": "white",
                        "borderRadius": "50%",
                        "width": "40px",
                        "height": "40px",
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "fontWeight": "bold",
                    }
                )
            ], className="me-3"),
            html.Div([
                html.H6(item.get("product_name", "Unknown Product"), className="mb-0"),
                html.Small([
                    f"Source: {item.get('source', 'Unknown')} | ",
                    f"Confidence: {item.get('confidence', 'Unknown')}"
                ], className="text-muted")
            ])
        ], className="d-flex align-items-center"),
        
        # Right side - action buttons
        html.Div([
            dbc.Button(
                html.I(className="fas fa-info-circle"),
                color="link",
                id={"type": "view-history-item", "index": index},
                className="me-2 p-0",
                title="View Details"
            ),
            dbc.Button(
                html.I(className="fas fa-exchange-alt"),
                color="link",
                id={"type": "compare-history-item", "index": index},
                className="me-2 p-0",
                title="Add to Comparison"
            ),
            dbc.Button(
                html.I(className="fas fa-share-alt"),
                color="link",
                id={"type": "share-history-item", "index": index},
                className="me-2 p-0",
                title="Share"
            ),
            dbc.Button(
                html.I(className="fas fa-trash-alt"),
                color="link",
                id={"type": "delete-history-item", "index": index},
                className="p-0 text-danger",
                title="Delete"
            ),
        ], className="d-flex align-items-center")
    ], className="d-flex justify-content-between align-items-center", action=True)
