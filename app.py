import streamlit as st
import json
import av
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import cv2
import numpy as np

from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY not found in environment variables.")


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

# --- Page Config ---
st.set_page_config(
    page_title="AI Food Health Analyzer", 
    page_icon="🥫", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Session State Initialization ---
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        "barcode": "",
        "result": None,
        "analysis_pending": False,
        "search_triggered": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- UI Functions ---
def display_health_metrics(parsed_result):
    """Display health score and rating metrics"""
    col1, col2 = st.columns(2)
    
    with col1:
        score = parsed_result.get("score", 0)
        delta_color = "normal" if score >= 70 else "inverse" if score >= 40 else "off"
        st.metric(
            "Health Score", 
            f"{score}/100", 
            help="0-40: Poor | 41-70: Medium | 71-100: Good"
        )
    
    with col2:
        band = parsed_result.get("band", "Unknown")
        band_colors = {"Good": "🟢", "Medium": "🟡", "Poor": "🔴"}
        band_color = band_colors.get(band, "⚫")
        st.metric("Health Rating", f"{band_color} {band}")

def display_health_drivers(drivers):
    """Display positive and negative health factors"""
    st.markdown("#### ⚡ Key Health Factors")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**✅ Positive Factors:**")
        positive_drivers = drivers.get("positive", [])
        if positive_drivers:
            for driver in positive_drivers:
                st.markdown(f"• {driver}")
        else:
            st.info("No significant positive factors identified.")
    
    with col2:
        st.markdown("**⚠️ Concerns:**")
        negative_drivers = drivers.get("negative", [])
        if negative_drivers:
            for driver in negative_drivers:
                st.markdown(f"• {driver}")
        else:
            st.info("No major concerns identified.")

def display_evidence_section(evidence):
    """Display detailed evidence and analysis"""
    with st.expander("📚 Evidence & Scientific Basis", expanded=False):
        
        # Ingredient Analysis
        if "ingredient_analysis" in evidence:
            st.markdown("**🔍 Ingredient Analysis**")
            ing_analysis = evidence["ingredient_analysis"]
            
            key_ingredients = ing_analysis.get("key_ingredients", [])
            if key_ingredients:
                st.write(f"**Key Ingredients:** {', '.join(key_ingredients)}")
            
            additives = ing_analysis.get("additives_of_concern", "None identified")
            st.write(f"**Additives of Concern:** {additives}")
            
            st.divider()
        
        # Nutritional Guidelines
        guidelines = evidence.get("nutritional_guidelines", [])
        if guidelines:
            st.markdown("**📊 Nutritional Analysis vs. Guidelines**")
            
            for item in guidelines:
                nutrient = item.get("nutrient", "N/A")
                product_value = item.get("product_value", "N/A")
                guideline = item.get("guideline", "N/A")
                rating = item.get("rating", "N/A")
                
                # Color coding for ratings
                color_map = {"Good": "🟢", "Medium": "🟡", "Poor": "🔴"}
                color_indicator = color_map.get(rating, "⚫")
                
                st.markdown(f"**{nutrient}**: {product_value} | *Guideline: {guideline}* | {color_indicator} {rating}")
            
            st.divider()
        
        # Citations
        citations = evidence.get("citations", [])
        if citations:
            st.markdown("**📖 Sources**")
            st.write(f"Analysis based on guidelines from: {', '.join(citations)}")

def display_results(parsed_result):
    """Main function to display all analysis results in markdown format"""
    try:
        st.divider()
        st.subheader("📊 Health Analysis Results")
        
        # Handle both string and dict inputs
        if isinstance(parsed_result, str):
            try:
                parsed_result = json.loads(parsed_result)
            except json.JSONDecodeError:
                # If it's not JSON, display as raw text
                st.markdown(parsed_result)
                return
        
        # Display summary
        summary = parsed_result.get("summary", "No summary available.")
        st.markdown(f"**Summary:** {summary}")
        st.markdown("")
        
        # Display metrics with proper error handling
        col1, col2 = st.columns(2)
        
        with col1:
            score = parsed_result.get("score", 0)
            # Ensure score is integer
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
        
        # Display health drivers
        st.markdown("#### ⚡ Key Health Factors")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**✅ Positive Factors:**")
            positive_drivers = parsed_result.get("drivers", {}).get("positive", [])
            if positive_drivers:
                for driver in positive_drivers:
                    st.markdown(f"• {driver}")
            else:
                st.info("No significant positive factors identified.")
        
        with col2:
            st.markdown("**⚠️ Concerns:**")
            negative_drivers = parsed_result.get("drivers", {}).get("negative", [])
            if negative_drivers:
                for driver in negative_drivers:
                    st.markdown(f"• {driver}")
            else:
                st.info("No major concerns identified.")
        
        # Display evidence section if available
        evidence = parsed_result.get("evidence", {})
        if evidence:
            with st.expander("📚 Detailed Analysis & Evidence", expanded=False):
                
                # Ingredient Analysis
                if "ingredient_analysis" in evidence:
                    st.markdown("**🔍 Ingredient Analysis**")
                    ing_analysis = evidence["ingredient_analysis"]
                    
                    key_ingredients = ing_analysis.get("key_ingredients", [])
                    if key_ingredients:
                        st.markdown(f"**Key Ingredients:** {', '.join(key_ingredients)}")
                    
                    additives = ing_analysis.get("additives_of_concern", "None identified")
                    st.markdown(f"**Additives of Concern:** {additives}")
                    
                    st.divider()
                
                # Nutritional Guidelines
                guidelines = evidence.get("nutritional_guidelines", [])
                if guidelines:
                    st.markdown("**📊 Nutritional Analysis vs. Guidelines**")
                    
                    for item in guidelines:
                        nutrient = item.get("nutrient", "N/A")
                        product_value = item.get("product_value", "N/A")
                        guideline = item.get("guideline", "N/A")
                        rating = item.get("rating", "N/A")
                        
                        # Color coding for ratings
                        color_map = {"Good": "🟢", "Medium": "🟡", "Poor": "🔴"}
                        color_indicator = color_map.get(rating, "⚫")
                        
                        st.markdown(f"**{nutrient}**: {product_value} | *Guideline: {guideline}* | {color_indicator} {rating}")
                    
                    st.divider()
                
                # Citations
                citations = evidence.get("citations", [])
                if citations:
                    st.markdown("**📖 Scientific Sources**")
                    st.markdown(f"Analysis based on guidelines from: {', '.join(citations)}")
        
        # Add reset button
        st.divider()
        if st.button("🔄 Analyze Another Product", type="primary", use_container_width=True):
            for key in ["result", "barcode", "analysis_pending"]:
                st.session_state[key] = "" if key == "barcode" else None if key == "result" else False
            st.rerun()
            
    except Exception as e:
        st.error("⚠️ Unable to display analysis results properly.")
        st.code(f"Raw output: {str(parsed_result)}")
        st.error(f"Error details: {str(e)}")

# --- Barcode Processing ---
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
            # Original
            lambda x: cv2.convertScaleAbs(x, alpha=1.5, beta=0),
            # Higher contrast
            lambda x: cv2.convertScaleAbs(x, alpha=2.0, beta=0),
            # Even higher contrast
            lambda x: cv2.convertScaleAbs(x, alpha=2.5, beta=0),
            # With blur
            lambda x: cv2.GaussianBlur(cv2.convertScaleAbs(x, alpha=1.5, beta=0), (5, 5), 0),
        ]
        
        for process_func in processing_techniques:
            processed_img = process_func(gray)
            barcodes = decode(processed_img)
            
            if barcodes:
                for barcode in barcodes:
                    barcode_data = barcode.data.decode("utf-8")
                    # Validate barcode format
                    if barcode_data.isdigit() and len(barcode_data) in [8, 12, 13, 14]:
                        return barcode_data
        
        return None
        
    except Exception as e:
        return None

# --- Analysis Functions ---
@st.cache_data(ttl=300)  # Cache for 5 minutes
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

# --- Main Application ---
def main():
    # Header
    st.title("🥫 AI-Powered Food Health Analyzer")
    st.markdown("Analyze packaged food products instantly using your camera, barcode, or product name.")
    
    # Input method selection
    input_methods = ["📸 Upload Barcode Photo", "📸 Upload Label Photo", "🔍 Search by Name"]
    if BARCODE_SCANNING_AVAILABLE:
        st.info("📵 Note: Live barcode scanning has been removed. Use photo upload or search instead.")
    else:
        st.warning("📵 Barcode scanning unavailable. Install zbar: `brew install zbar`")

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

def handle_photo_upload():
    """Handle photo upload interface"""
    st.subheader("📸 Upload Food Label Photo")
    
    uploaded_file = st.file_uploader(
        "Choose an image of the ingredients & nutrition panel",
        type=["jpg", "jpeg", "png"],
        help="For best results, ensure the text is clear and well-lit"
    )
    
    if uploaded_file:
        # Display uploaded image
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
        
        with col2:
            if st.button("🔍 Analyze Label", type="primary", use_container_width=True):
                try:
                    result = analyze_food_image(uploaded_file)
                    st.session_state.result = result
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Image analysis failed: {str(e)}")

def handle_name_search():
    """Handle product name search interface"""
    st.subheader("🔍 Search by Product Name")
    
    # Search input
    search_query = st.text_input(
        "Enter product name:",
        placeholder="e.g., Nutella, Coca Cola, Oreo cookies",
        help="Enter the brand name and product for better results"
    )
    
    if search_query and len(search_query.strip()) >= 3:
        # Trigger search
        st.session_state.search_triggered = True
        
        with st.spinner("🔍 Searching for products..."):
            search_results = cached_search_product_by_name(search_query.strip())
        
        if search_results:
            # Display search results
            st.success(f"Found {len(search_results)} products:")
            
            # Create selection options
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
            
            # Analyze button
            if st.button("📊 Analyze Selected Product", type="primary", use_container_width=True):
                barcode = product_options[selected_name]
                if barcode:
                    st.session_state.barcode = barcode
                    process_barcode_analysis(barcode)
                else:
                    st.error("❌ No barcode available for this product.")
        
        elif st.session_state.search_triggered:
            st.warning("🔍 No products found. Try different search terms.")
    
    elif search_query and len(search_query.strip()) < 3:
        st.info("💡 Enter at least 3 characters to search.")

def handle_barcode_photo_upload():
    """Handle barcode photo upload for scanning"""
    st.subheader("📸 Upload Barcode Photo")
    
    # Display scanning tips
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
        help="Make sure the barcode is clear and well-lit for better detection"
    )
    
    if uploaded_file:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Display the uploaded image
            st.image(uploaded_file, caption="Uploaded Barcode", use_column_width=True)
            
        with col2:
            if st.button("🔍 Scan Barcode from Photo", type="primary", use_container_width=True):
                try:
                    # Reset file pointer and process the image
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
                        ❌ No barcode found. Please try:
                        - Taking a clearer photo
                        - Better lighting
                        - Ensuring the barcode is straight
                        - Trying a different barcode
                        """)
                        
                except Exception as e:
                    st.error(f"❌ Error processing image: {str(e)}")

def display_product_info(product_data):
    """Display product information before analysis"""
    st.subheader("📦 Product Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if product_data.get("image_url"):
            st.image(product_data["image_url"], caption="Product Image", width=200)
        else:
            st.info("📷 No product image available")
    
    with col2:
        st.write(f"**Name:** {product_data.get('name', 'Unknown')}")
        st.write(f"**Brand:** {product_data.get('brand', 'Unknown')}")
        st.write(f"**Source:** {product_data.get('source', 'Unknown')}")
        
        if product_data.get("category"):
            st.write(f"**Category:** {product_data['category']}")
    
    # Show ingredients if available
    if product_data.get("ingredients"):
        with st.expander("📝 Ingredients", expanded=False):
            for i, ingredient in enumerate(product_data["ingredients"][:10]):  # Show first 10
                st.write(f"{i+1}. {ingredient}")
            if len(product_data["ingredients"]) > 10:
                st.info(f"... and {len(product_data['ingredients']) - 10} more ingredients")
    
    # Show nutrients if available
    if product_data.get("nutrients"):
        with st.expander("📊 Nutrients", expanded=False):
            for nutrient, value in product_data["nutrients"].items():
                st.write(f"**{nutrient.replace('_', ' ').title()}:** {value}")


def process_barcode_analysis(barcode):
    """Process barcode and analyze product"""
    with st.spinner(f"📦 Fetching product data for {barcode}..."):
        product_data = cached_fetch_product_by_barcode(barcode)
    
    if product_data and product_data.get("found"):
        product_name = product_data.get('name', 'Unknown Product')
        st.success(f"✅ Found: **{product_name}**")
        
        # Display product information
        display_product_info(product_data)
        
        st.divider()
        st.subheader("🤖 AI Health Analysis")
        
        # Analyze button
        if st.button("🔍 Analyze Health Impact", type="primary", use_container_width=True):
            # Analyze the product
            result = analyze_product_data(product_data)
            if result:
                st.session_state.result = result
                st.rerun()
    else:
        error_msg = product_data.get('error', 'Unknown error')
        st.error(f"❌ Product not found: {error_msg}")
        st.session_state.result = None

def display_analysis_results():
    """Display the final analysis results"""
    try:
        # Handle different result types
        result_data = st.session_state.result
        
        if hasattr(result_data, 'raw'):
            # CrewAI result object
            json_str = result_data.raw
        elif isinstance(result_data, str):
            # Direct string result
            json_str = result_data
        else:
            # Already parsed or other format
            json_str = str(result_data)
        
        # Parse JSON
        parsed_result = json.loads(json_str)
        
        # Display results
        display_results(parsed_result)
        
        # Add reset button
        if st.button("🔄 Analyze Another Product", use_container_width=True):
            for key in ["result", "barcode", "analysis_pending"]:
                st.session_state[key] = "" if key == "barcode" else None if key == "result" else False
            st.rerun()
            
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        st.error("⚠️ Unable to parse analysis results. Raw output:")
        st.code(str(st.session_state.result))
        st.error(f"Error details: {str(e)}")

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
    </style>
    """, unsafe_allow_html=True)
    
    main()

# Footer
st.divider()
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.9rem;'>"
    "Powered by CrewAI 🤖 | Data from OpenFoodFacts 📊"
    "</div>", 
    unsafe_allow_html=True
)