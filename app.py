import streamlit as st
import json
import cv2
import numpy as np
import sqlite3
from datetime import datetime
import pandas as pd
from pathlib import Path

from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("⚠ OPENAI_API_KEY not found in environment variables.")

# Import with error handling for zbar
try:
    from pyzbar.pyzbar import decode
    BARCODE_SCANNING_AVAILABLE = True
except ImportError as e:
    st.error("⚠️ Barcode scanning not available. Install zbar library: `brew install zbar` (macOS) or `sudo apt-get install libzbar0` (Ubuntu)")
    BARCODE_SCANNING_AVAILABLE = False
    decode = None

from crew_setup import analyze_food_data, analyze_food_image
from barcode_utils import fetch_product_by_barcode, search_product_by_name
from normalization import normalize_product_data, format_ingredients_display, convert_units
from history_manager import HistoryManager

# --- Page Config ---
st.set_page_config(
    page_title="AI Food Health Analyzer", 
    page_icon="🥫", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize history manager
history_manager = HistoryManager()

# --- Session State Initialization ---
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        "barcode": "",
        "result": None,
        "analysis_pending": False,
        "search_triggered": False,
        "current_product": None,
        "comparison_products": [],
        "missing_info_requested": {},
        "pack_size": None,
        "current_page": "analyze"
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- Sidebar Navigation ---
def render_sidebar():
    """Render sidebar with navigation and features"""
    st.sidebar.title("🥫 Food Analyzer")
    
    # Navigation
    page = st.sidebar.radio(
        "Navigate",
        ["🔍 Analyze Product", "📊 History", "⚖️ Compare Products", "🌐 Settings"],
        key="navigation"
    )
    
    # Map radio selection to page state
    page_mapping = {
        "🔍 Analyze Product": "analyze",
        "📊 History": "history", 
        "⚖️ Compare Products": "compare",
        "🌐 Settings": "settings"
    }
    
    st.session_state.current_page = page_mapping[page]
    
    # Quick stats
    if st.sidebar.button("📈 Quick Stats"):
        stats = history_manager.get_summary_stats()
        st.sidebar.metric("Total Products Analyzed", stats.get("total_products", 0))
        st.sidebar.metric("Average Health Score", f"{stats.get('avg_score', 0):.1f}")
        st.sidebar.metric("Products This Week", stats.get("products_this_week", 0))
    
    # Export options
    st.sidebar.markdown("---")
    if st.sidebar.button("📤 Export History"):
        export_history()

def export_history():
    """Export analysis history as CSV"""
    try:
        df = history_manager.get_history_dataframe()
        if not df.empty:
            csv = df.to_csv(index=False)
            st.sidebar.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"food_analysis_history_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.sidebar.info("No history to export")
    except Exception as e:
        st.sidebar.error(f"Export failed: {str(e)}")

# --- Main Pages ---
def render_analyze_page():
    """Main analysis page"""
    st.title("🥫 AI-Powered Food Health Analyzer")
    st.markdown("Analyze packaged food products instantly using your camera, barcode, or product name.")
    
    # Input method selection
    input_methods = ["📸 Upload Barcode Photo", "📸 Upload Label Photo", "🔍 Search by Name"]
    if BARCODE_SCANNING_AVAILABLE:
        st.info("🔵 Note: Live barcode scanning has been removed. Use photo upload or search instead.")
    else:
        st.warning("🔵 Barcode scanning unavailable. Install zbar: `brew install zbar`")

    input_method = st.radio(
        "Choose an input method:",
        input_methods,
        horizontal=True
    )
    
    st.divider()
    
    # --- Input Method Handlers ---
    if input_method == "📸 Upload Barcode Photo":
        handle_barcode_photo_upload()
    elif input_method == "📸 Upload Label Photo":
        handle_photo_upload()
    elif input_method == "🔍 Search by Name":
        handle_name_search()
        
    # --- Display Results ---
    if st.session_state.result:
        display_analysis_results()

def render_history_page():
    """History page with search and filtering"""
    st.title("📊 Analysis History")
    
    # Get history data
    history_df = history_manager.get_history_dataframe()
    
    if history_df.empty:
        st.info("No analysis history found. Start analyzing products to build your history!")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        date_filter = st.date_input("Filter by date (from)", value=None)
    
    with col2:
        score_filter = st.select_slider(
            "Minimum health score",
            options=list(range(0, 101, 10)),
            value=0
        )
    
    with col3:
        search_term = st.text_input("Search products", placeholder="Enter product name or brand")
    
    # Apply filters
    filtered_df = history_df.copy()
    
    if date_filter:
        filtered_df = filtered_df[pd.to_datetime(filtered_df['analyzed_at']).dt.date >= date_filter]
    
    if score_filter > 0:
        filtered_df = filtered_df[filtered_df['health_score'] >= score_filter]
    
    if search_term:
        mask = (filtered_df['product_name'].str.contains(search_term, case=False, na=False) |
                filtered_df['brand'].str.contains(search_term, case=False, na=False))
        filtered_df = filtered_df[mask]
    
    # Display results
    st.markdown(f"**{len(filtered_df)} products found**")
    
    if not filtered_df.empty:
        # Display as cards
        for idx, row in filtered_df.iterrows():
            with st.expander(f"{row['product_name']} ({row['brand']}) - Score: {row['health_score']}/100"):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**Analyzed:** {row['analyzed_at']}")
                    st.write(f"**Health Band:** {row['health_band']}")
                    if row['summary']:
                        st.write(f"**Summary:** {row['summary']}")
                
                with col2:
                    if st.button(f"View Details", key=f"view_{idx}"):
                        st.session_state.result = row['analysis_result']
                        st.session_state.current_page = "analyze"
                        st.rerun()
                
                with col3:
                    if st.button(f"Add to Compare", key=f"compare_{idx}"):
                        if row['product_name'] not in [p.get('name', '') for p in st.session_state.comparison_products]:
                            st.session_state.comparison_products.append({
                                'name': row['product_name'],
                                'brand': row['brand'],
                                'score': row['health_score'],
                                'band': row['health_band'],
                                'result': row['analysis_result']
                            })
                            st.success(f"Added {row['product_name']} to comparison")
                        else:
                            st.warning("Product already in comparison")

def render_compare_page():
    """Product comparison page"""
    st.title("⚖️ Compare Products")
    
    if len(st.session_state.comparison_products) < 2:
        st.info("Add at least 2 products from history to compare them.")
        
        # Quick add from recent history
        recent = history_manager.get_recent_products(limit=10)
        if recent:
            st.subheader("Recent Products")
            for product in recent:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"{product['product_name']} ({product['brand']}) - {product['health_score']}/100")
                with col2:
                    if st.button(f"Add", key=f"add_{product['id']}"):
                        if product['product_name'] not in [p.get('name', '') for p in st.session_state.comparison_products]:
                            st.session_state.comparison_products.append({
                                'name': product['product_name'],
                                'brand': product['brand'],
                                'score': product['health_score'],
                                'band': product['health_band'],
                                'result': product['analysis_result']
                            })
                            st.rerun()
        return
    
    # Display comparison
    st.subheader(f"Comparing {len(st.session_state.comparison_products)} Products")
    
    # Create comparison table
    comparison_data = []
    for product in st.session_state.comparison_products:
        try:
            result = json.loads(product['result']) if isinstance(product['result'], str) else product['result']
            comparison_data.append({
                'Product': f"{product['name']}\n({product['brand']})",
                'Health Score': product['score'],
                'Health Band': product['band'],
                'Sugar Content': extract_nutrient_value(result, 'sugar'),
                'Sodium Content': extract_nutrient_value(result, 'sodium'),
                'Fiber Content': extract_nutrient_value(result, 'fiber'),
            })
        except:
            comparison_data.append({
                'Product': f"{product['name']}\n({product['brand']})",
                'Health Score': product['score'],
                'Health Band': product['band'],
                'Sugar Content': 'N/A',
                'Sodium Content': 'N/A', 
                'Fiber Content': 'N/A',
            })
    
    # Display table
    df = pd.DataFrame(comparison_data)
    st.dataframe(df, use_container_width=True)
    
    # Clear comparison
    if st.button("Clear Comparison"):
        st.session_state.comparison_products = []
        st.rerun()

def extract_nutrient_value(result_data, nutrient):
    """Extract nutrient value from analysis result"""
    try:
        evidence = result_data.get('evidence', {})
        nutritional_analysis = evidence.get('nutritional_analysis', [])
        
        for item in nutritional_analysis:
            if nutrient.lower() in item.get('nutrient', '').lower():
                return item.get('product_value', 'N/A')
        return 'N/A'
    except:
        return 'N/A'

def render_settings_page():
    """Settings and preferences page"""
    st.title("🌐 Settings")
    
    st.subheader("Regional Preferences")
    region = st.selectbox(
        "Select your region for localized guidelines:",
        ["India (FSSAI)", "United States (FDA)", "Europe (EFSA)", "Australia (FSANZ)", "Global (WHO)"],
        index=0
    )
    
    st.subheader("Unit Preferences")
    col1, col2 = st.columns(2)
    with col1:
        weight_unit = st.selectbox("Weight", ["grams", "ounces"], index=0)
    with col2:
        volume_unit = st.selectbox("Volume", ["ml", "fl oz"], index=0)
    
    st.subheader("Analysis Preferences")
    strictness = st.slider(
        "Analysis Strictness",
        min_value=1,
        max_value=5,
        value=3,
        help="Higher values apply stricter health criteria"
    )
    
    include_additives = st.checkbox("Include detailed additive analysis", value=True)
    show_evidence = st.checkbox("Show evidence panel by default", value=True)
    
    if st.button("Save Settings"):
        # In a real app, you'd save these to a config file or database
        st.success("Settings saved!")

# --- Enhanced UI Functions ---
def display_missing_info_panel(product_data):
    """Display panel for missing information with user input"""
    st.subheader("🔍 Missing Information")
    
    missing_items = identify_missing_info(product_data)
    
    if not missing_items:
        st.success("✅ All key information is available!")
        return product_data
    
    st.warning(f"⚠️ {len(missing_items)} pieces of information are missing or unclear:")
    
    updated_data = product_data.copy()
    
    for item in missing_items:
        st.markdown(f"**{item['field']}**: {item['description']}")
        
        if item['type'] == 'pack_size':
            pack_size = st.text_input(
                f"Enter pack size for {product_data.get('name', 'this product')}:",
                placeholder="e.g., 500g, 1L, 250ml",
                key=f"pack_size_{item['field']}"
            )
            if pack_size:
                updated_data['pack_size'] = pack_size
                st.session_state.pack_size = pack_size
        
        elif item['type'] == 'nutrient':
            nutrient_value = st.text_input(
                f"Enter {item['field']} content per 100g:",
                placeholder=f"e.g., 15.2g",
                key=f"nutrient_{item['field']}"
            )
            if nutrient_value:
                if 'nutrients' not in updated_data:
                    updated_data['nutrients'] = {}
                updated_data['nutrients'][item['field']] = nutrient_value
    
    if st.button("Update Analysis with New Information"):
        return updated_data
    
    return product_data

def identify_missing_info(product_data):
    """Identify what information is missing from the product"""
    missing = []
    
    # Check for pack size
    if not product_data.get('pack_size') and not st.session_state.pack_size:
        missing.append({
            'field': 'Pack Size',
            'type': 'pack_size',
            'description': 'Pack size helps calculate per-serving nutritional values'
        })
    
    # Check for key nutrients
    nutrients = product_data.get('nutrients', {})
    key_nutrients = ['sugar', 'sodium', 'saturated_fat', 'fiber', 'protein']
    
    for nutrient in key_nutrients:
        if nutrient not in nutrients:
            missing.append({
                'field': nutrient.replace('_', ' ').title(),
                'type': 'nutrient',
                'description': f'{nutrient.replace("_", " ").title()} content is important for health assessment'
            })
    
    # Check for ingredients
    if not product_data.get('ingredients'):
        missing.append({
            'field': 'Ingredients List',
            'type': 'ingredients',
            'description': 'Complete ingredients list needed for additive analysis'
        })
    
    return missing

def display_normalized_view(product_data):
    """Display clean, normalized product information"""
    st.subheader("📋 Normalized Product Information")
    
    # Normalize the data
    normalized = normalize_product_data(product_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Product Details**")
        st.write(f"**Name:** {normalized.get('name', 'Unknown')}")
        st.write(f"**Brand:** {normalized.get('brand', 'Unknown')}")
        st.write(f"**Category:** {normalized.get('category', 'Unknown')}")
        if normalized.get('pack_size'):
            st.write(f"**Pack Size:** {normalized['pack_size']}")
    
    with col2:
        if normalized.get('image_url'):
            st.image(normalized['image_url'], caption="Product Image", width=200)
        else:
            st.info("📷 No product image available")
    
    # Display ingredients with formatting
    if normalized.get('ingredients'):
        with st.expander("🧪 Ingredients (Normalized)", expanded=False):
            formatted_ingredients = format_ingredients_display(normalized['ingredients'])
            st.markdown(formatted_ingredients)
    
    # Display nutritional information with unit conversion
    if normalized.get('nutrients'):
        with st.expander("📊 Nutritional Information", expanded=True):
            nutrients_df = pd.DataFrame([
                {
                    'Nutrient': nutrient.replace('_', ' ').title(),
                    'Per 100g': value,
                    'Per Serving': convert_units(value, normalized.get('pack_size', '100g'), 'serving') if normalized.get('pack_size') else 'N/A'
                }
                for nutrient, value in normalized['nutrients'].items()
            ])
            st.dataframe(nutrients_df, hide_index=True)
    
    return normalized

def display_enhanced_results(parsed_result):
    """Enhanced results display with evidence and sources"""
    try:
        st.divider()
        st.subheader("📊 Health Analysis Results")
        
        # Handle both string and dict inputs
        if isinstance(parsed_result, str):
            try:
                parsed_result = json.loads(parsed_result)
            except json.JSONDecodeError:
                st.markdown(parsed_result)
                return
        
        # Main metrics with enhanced styling
        col1, col2, col3 = st.columns(3)
        
        with col1:
            score = parsed_result.get("score", 0)
            if isinstance(score, str):
                try:
                    score = int(score)
                except (ValueError, TypeError):
                    score = 0
            
            score_color = "🟢" if score >= 70 else "🟡" if score >= 40 else "🔴"
            st.metric(
                "Health Score", 
                f"{score_color} {score}/100",
                help="0-40: Poor | 41-70: Medium | 71-100: Good"
            )
        
        with col2:
            band = parsed_result.get("band", "Unknown")
            band_colors = {"Good": "🟢", "Medium": "🟡", "Poor": "🔴"}
            band_color = band_colors.get(band, "⚫")
            st.metric("Health Rating", f"{band_color} {band}")
        
        with col3:
            # Add confidence score if available
            confidence = parsed_result.get("confidence", "N/A")
            st.metric("Analysis Confidence", confidence if confidence != "N/A" else "Standard")
        
        # Summary with enhanced formatting
        summary = parsed_result.get("summary", "No summary available.")
        st.markdown(f"**📝 Summary:** {summary}")
        st.markdown("")
        
        # Enhanced health drivers
        display_enhanced_health_drivers(parsed_result)
        
        # Evidence panel with sources
        display_evidence_panel_enhanced(parsed_result)
        
        # Save to history
        save_analysis_to_history(parsed_result)
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔄 Analyze Another Product", type="primary", use_container_width=True):
                reset_analysis()
        with col2:
            if st.button("📊 Add to Compare", use_container_width=True):
                add_to_comparison(parsed_result)
        with col3:
            if st.button("🔗 Share Analysis", use_container_width=True):
                generate_share_link(parsed_result)
                
    except Exception as e:
        st.error("⚠️ Unable to display analysis results properly.")
        st.code(f"Raw output: {str(parsed_result)}")
        st.error(f"Error details: {str(e)}")

def display_enhanced_health_drivers(parsed_result):
    """Enhanced health drivers display with icons and context"""
    st.markdown("#### ⚡ Key Health Factors")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**✅ Positive Factors:**")
        positive_drivers = parsed_result.get("drivers", {}).get("positive", [])
        if positive_drivers:
            for i, driver in enumerate(positive_drivers, 1):
                st.markdown(f"{i}. {driver}")
        else:
            st.info("No significant positive factors identified.")
    
    with col2:
        st.markdown("**⚠️ Concerns:**")
        negative_drivers = parsed_result.get("drivers", {}).get("negative", [])
        if negative_drivers:
            for i, driver in enumerate(negative_drivers, 1):
                st.markdown(f"{i}. {driver}")
        else:
            st.info("No major concerns identified.")

def display_evidence_panel_enhanced(parsed_result):
    """Enhanced evidence panel with detailed sources and thresholds"""
    evidence = parsed_result.get("evidence", {})
    if not evidence:
        return
    
    with st.expander("📚 Detailed Analysis & Evidence", expanded=False):
        
        # Nutritional analysis with thresholds
        if "nutritional_analysis" in evidence:
            st.markdown("**📊 Nutritional Threshold Analysis**")
            
            nutritional_data = []
            for item in evidence["nutritional_analysis"]:
                nutritional_data.append({
                    'Nutrient': item.get('nutrient', 'N/A'),
                    'Product Value': item.get('product_value', 'N/A'),
                    'Guideline': item.get('guideline', 'N/A'),
                    'Rating': f"{get_rating_icon(item.get('rating', 'N/A'))} {item.get('rating', 'N/A')}"
                })
            
            if nutritional_data:
                df = pd.DataFrame(nutritional_data)
                st.dataframe(df, hide_index=True)
            
            st.divider()
        
        # Ingredient analysis
        if "ingredient_analysis" in evidence:
            st.markdown("**🔬 Ingredient Analysis**")
            ing_analysis = evidence["ingredient_analysis"]
            
            key_ingredients = ing_analysis.get("key_ingredients", [])
            if key_ingredients:
                st.markdown(f"**Key Ingredients:** {', '.join(key_ingredients)}")
            
            additives = ing_analysis.get("additives_of_concern", "None identified")
            st.markdown(f"**Additives of Concern:** {additives}")
            
            st.divider()
        
        # Authoritative sources with links where possible
        sources = evidence.get("authoritative_sources", [])
        if sources:
            st.markdown("**📖 Scientific Sources & Guidelines**")
            for i, source in enumerate(sources, 1):
                st.markdown(f"{i}. {source}")

def get_rating_icon(rating):
    """Get appropriate icon for rating"""
    icons = {"Good": "🟢", "Medium": "🟡", "Poor": "🔴"}
    return icons.get(rating, "⚫")

def save_analysis_to_history(result_data):
    """Save analysis result to history"""
    try:
        product_name = st.session_state.get('current_product', {}).get('name', 'Unknown Product')
        brand = st.session_state.get('current_product', {}).get('brand', 'Unknown Brand')
        
        if isinstance(result_data, str):
            parsed_result = json.loads(result_data)
        else:
            parsed_result = result_data
        
        history_manager.save_analysis(
            product_name=product_name,
            brand=brand,
            barcode=st.session_state.get('barcode', ''),
            health_score=parsed_result.get('score', 0),
            health_band=parsed_result.get('band', 'Unknown'),
            summary=parsed_result.get('summary', ''),
            analysis_result=json.dumps(parsed_result) if isinstance(parsed_result, dict) else result_data
        )
    except Exception as e:
        st.error(f"Failed to save to history: {str(e)}")

def add_to_comparison(result_data):
    """Add current product to comparison"""
    try:
        product_name = st.session_state.get('current_product', {}).get('name', 'Unknown Product')
        brand = st.session_state.get('current_product', {}).get('brand', 'Unknown Brand')
        
        if product_name not in [p.get('name', '') for p in st.session_state.comparison_products]:
            st.session_state.comparison_products.append({
                'name': product_name,
                'brand': brand,
                'score': result_data.get('score', 0),
                'band': result_data.get('band', 'Unknown'),
                'result': json.dumps(result_data) if isinstance(result_data, dict) else result_data
            })
            st.success(f"Added {product_name} to comparison!")
        else:
            st.warning("Product already in comparison")
    except Exception as e:
        st.error(f"Failed to add to comparison: {str(e)}")

def generate_share_link(result_data):
    """Generate shareable analysis summary"""
    try:
        product_name = st.session_state.get('current_product', {}).get('name', 'Unknown Product')
        score = result_data.get('score', 0)
        band = result_data.get('band', 'Unknown')
        summary = result_data.get('summary', '')
        
        share_text = f"""
🥫 Food Health Analysis: {product_name}
📊 Health Score: {score}/100 ({band})
📝 Summary: {summary}

Generated by AI Food Health Analyzer
        """
        
        st.text_area("Share this analysis:", share_text, height=150)
        st.info("Copy the text above to share your analysis!")
    except Exception as e:
        st.error(f"Failed to generate share link: {str(e)}")

def reset_analysis():
    """Reset analysis state"""
    for key in ["result", "barcode", "analysis_pending", "current_product"]:
        if key == "barcode":
            st.session_state[key] = ""
        elif key in ["result", "current_product"]:
            st.session_state[key] = None
        else:
            st.session_state[key] = False
    st.rerun()

# --- Barcode Processing (unchanged) ---
def process_barcode_detection(img):
    """Process image for barcode detection with multiple attempts"""
    if not BARCODE_SCANNING_AVAILABLE:
        return None
    
    try:
        # Convert to grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        
        # Try multiple image processing techniques
        processing_techniques = [
            lambda x: cv2.convertScaleAbs(x, alpha=1.5, beta=0),
            lambda x: cv2.convertScaleAbs(x, alpha=2.0, beta=0),
            lambda x: cv2.convertScaleAbs(x, alpha=2.5, beta=0),
            lambda x: cv2.GaussianBlur(cv2.convertScaleAbs(x, alpha=1.5, beta=0), (5, 5), 0),
        ]
        
        for process_func in processing_techniques:
            processed_img = process_func(gray)
            barcodes = decode(processed_img)
            
            if barcodes:
                for barcode in barcodes:
                    barcode_data = barcode.data.decode("utf-8")
                    if barcode_data.isdigit() and len(barcode_data) in [8, 12, 13, 14]:
                        return barcode_data
        
        return None
        
    except Exception as e:
        return None

# --- Analysis Functions (with caching) ---
@st.cache_data(ttl=300)
def cached_fetch_product_by_barcode(barcode):
    """Cached version of barcode lookup to avoid repeated API calls"""
    return fetch_product_by_barcode(barcode)

@st.cache_data(ttl=300)
def cached_search_product_by_name(product_name):
    """Cached version of product search"""
    return search_product_by_name(product_name)

def analyze_product_data(product_data):
    """Analyze product data and handle errors"""
    try:
        with st.spinner("🤖 AI is analyzing health impact..."):
            result = analyze_food_data(product_data)
        return result
    except Exception as e:
        st.error(f"Analysis failed: {str(e)}")
        return None

# --- Input Handlers (mostly unchanged but using new display functions) ---
def handle_photo_upload():
    """Handle photo upload interface"""
    st.subheader("📸 Upload Food Label Photo")
    
    uploaded_file = st.file_uploader(
        "Choose an image of the ingredients & nutrition panel",
        type=["jpg", "jpeg", "png"],
        help="For best results, ensure the text is clear and well-lit"
    )
    
    if uploaded_file:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
        
        with col2:
            if st.button("🔍 Analyze Label", type="primary", use_container_width=True):
                try:
                    result = analyze_food_image(uploaded_file)
                    st.session_state.result = result
                    st.session_state.current_product = {"name": "Label Image Analysis", "brand": "Unknown"}
                    st.rerun()
                except Exception as e:
                    st.error(f"⚠ Image analysis failed: {str(e)}")

def handle_name_search():
    """Handle product name search interface"""
    st.subheader("🔍 Search by Product Name")
    
    search_query = st.text_input(
        "Enter product name:",
        placeholder="e.g., Nutella, Coca Cola, Oreo cookies",
        help="Enter the brand name and product for better results"
    )
    
    if search_query and len(search_query.strip()) >= 3:
        st.session_state.search_triggered = True
        
        with st.spinner("🔍 Searching for products..."):
            search_results = cached_search_product_by_name(search_query.strip())
        
        if search_results:
            st.success(f"Found {len(search_results)} products:")
            
            product_options = {}
            for i, product in enumerate(search_results):
                name = product.get('name', 'Unknown Product')
                brand = product.get('brand', 'Unknown Brand')
                display_name = f"{name} ({brand})"
                product_options[display_name] = product.get('barcode', '')
            
            selected_name = st.selectbox(
                "Select the correct product:",
                options=list(product_options.keys()),
                index=0
            )
            
            if st.button("📊 Analyze Selected Product", type="primary", use_container_width=True):
                barcode = product_options[selected_name]
                if barcode:
                    st.session_state.barcode = barcode
                    process_barcode_analysis(barcode)
                else:
                    st.error("⚠ No barcode available for this product.")
        
        elif st.session_state.search_triggered:
            st.warning("🔍 No products found. Try different search terms.")
    
    elif search_query and len(search_query.strip()) < 3:
        st.info("💡 Enter at least 3 characters to search.")

def handle_barcode_photo_upload():
    """Handle barcode photo upload for scanning"""
    st.subheader("📸 Upload Barcode Photo")
    
    with st.expander("💡 Barcode Scanning Tips", expanded=True):
        st.markdown("""
        **For best results:**
        - ✅ Ensure good lighting on the barcode
        - ✅ Hold the camera steady
        - ✅ Capture the entire barcode
        - ✅ Avoid glare and reflections
        - ✅ Make sure barcode is in focus
        - ✅ Use a plain background if possible
        """)
    
    uploaded_file = st.file_uploader(
        "Upload a clear photo of the barcode",
        type=["jpg", "jpeg", "png"],
        help="Make sure the barcode is clear and well-lit for better detection",
        key="barcode_uploader"
    )
    
    if uploaded_file:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image(uploaded_file, caption="Uploaded Barcode", use_container_width=True)
            
        with col2:
            if st.button("🔍 Scan Barcode from Photo", type="primary", use_container_width=True, key="scan_barcode_btn"):
                try:
                    uploaded_file.seek(0)
                    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    
                    barcode_data = process_barcode_detection(image)
                    
                    if barcode_data:
                        st.success(f"✅ Barcode detected: **{barcode_data}**")
                        st.session_state.barcode = barcode_data
                        process_barcode_analysis(barcode_data)
                    else:
                        st.error("""
                        ⚠ No barcode found. Please try:
                        - Taking a clearer photo
                        - Better lighting
                        - Ensuring the barcode is straight
                        - Trying a different barcode
                        """)
                        
                except Exception as e:
                    st.error(f"⚠ Error processing image: {str(e)}")

def process_barcode_analysis(barcode):
    """Process barcode and analyze product"""
    with st.spinner(f"📦 Fetching product data for {barcode}..."):
        product_data = cached_fetch_product_by_barcode(barcode)
    
    if product_data and product_data.get("found"):
        product_name = product_data.get('name', 'Unknown Product')
        st.success(f"✅ Found: **{product_name}**")
        
        # Store current product for history
        st.session_state.current_product = {
            'name': product_name,
            'brand': product_data.get('brand', 'Unknown Brand'),
            'barcode': barcode
        }
        
        # Display normalized view
        normalized_data = display_normalized_view(product_data)
        
        # Check for missing information
        updated_data = display_missing_info_panel(normalized_data)
        
        st.divider()
        st.subheader("🤖 AI Health Analysis")
        
        # Analyze the product
        result = analyze_product_data(updated_data)
        if result:
            st.session_state.result = result
            st.rerun()
    else:
        error_msg = product_data.get('error', 'Unknown error')
        st.error(f"⚠ Product not found: {error_msg}")
        st.session_state.result = None

def display_analysis_results():
    """Display the final analysis results using enhanced display"""
    display_enhanced_results(st.session_state.result)

# --- Main Application ---
def main():
    render_sidebar()
    
    # Route to appropriate page
    if st.session_state.current_page == "analyze":
        render_analyze_page()
    elif st.session_state.current_page == "history":
        render_history_page()
    elif st.session_state.current_page == "compare":
        render_compare_page()
    elif st.session_state.current_page == "settings":
        render_settings_page()

if __name__ == "__main__":
    # Add custom CSS for better styling
    st.markdown("""
    <style>
    .stMetric > label {
        font-size: 1rem !important;
        font-weight: 600 !important;
    }
    .stButton > button {
        width: 100%;
    }
    .comparison-table {
        font-size: 0.9rem;
    }
    .health-score-good {
        color: #28a745 !important;
    }
    .health-score-medium {
        color: #ffc107 !important;
    }
    .health-score-poor {
        color: #dc3545 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    main()

# Footer
st.divider()
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.9rem;'>"
    "Powered by CrewAI 🤖 | Data from OpenFoodFacts 📊 | Evidence-based Analysis 🔬"
    "</div>", 
    unsafe_allow_html=True
)