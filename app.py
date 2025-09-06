import streamlit as st
import json
from crew_setup import analyze_food_data, analyze_food_image
from barcode_utils import fetch_product_by_barcode

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="AI Food Health Analyzer", 
    page_icon="🥫",
    layout="wide"
)

# --- Header ---
st.title("🥫 AI-Powered Food Health Analyzer")
st.markdown("Analyze packaged food products instantly using AI to get health scores and insights")

# --- Input Method Selection ---
col1, col2 = st.columns([1, 2])

with col1:
    input_method = st.radio(
        "Choose input method:", 
        ["📸 Upload Photo", "🔢 Scan Barcode"],
        help="Select how you want to input the food product information"
    )

with col2:
    st.info("💡 **How it works:**\n"
            "- **Photo**: Upload a picture of the food label\n"
            "- **Barcode**: Enter the barcode number to fetch product details")

st.divider()

result = None
product_data = None

# --- Photo Upload Branch ---
if input_method == "📸 Upload Photo":
    st.subheader("Upload Food Label Photo")
    
    uploaded_file = st.file_uploader(
        "Choose an image of the food label (ingredients & nutrition panel)",
        type=["jpg", "jpeg", "png"],
        help="Make sure the text is clear and readable"
    )
    
    if uploaded_file is not None:
        # Display the uploaded image
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(uploaded_file, caption="Uploaded Label", use_container_width=True)
        
        with col2:
            if st.button("🔍 Analyze Label", type="primary", use_container_width=True):
                with st.spinner("🤖 AI is reading and analyzing the label..."):
                    try:
                        result = analyze_food_image(uploaded_file)
                    except Exception as e:
                        st.error(f"Error analyzing image: {str(e)}")

# --- Barcode Input Branch ---
elif input_method == "🔢 Scan Barcode":
    st.subheader("Enter Product Barcode")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        barcode = st.text_input(
            "Enter barcode number:",
            placeholder="e.g., 3017620422003",
            help="Usually found below the barcode lines on the package"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_button = st.button("🔍 Fetch & Analyze", type="primary", use_container_width=True)
    
    if barcode and analyze_button:
        # Step 1: Fetch product data
        with st.spinner("📡 Fetching product information..."):
            product_data = fetch_product_by_barcode(barcode)
        
        if product_data and product_data.get("found"):
            # Display fetched product info
            st.success(f"✅ Found: **{product_data.get('name', 'Unknown Product')}**")
            
            with st.expander("📋 Product Details", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Ingredients:**")
                    ingredients = product_data.get("ingredients", [])
                    if ingredients:
                        for ing in ingredients[:10]:  # Show first 10
                            st.write(f"• {ing}")
                        if len(ingredients) > 10:
                            st.write(f"*...and {len(ingredients)-10} more*")
                    else:
                        st.write("No ingredients found")
                
                with col2:
                    st.markdown("**Key Nutrients:**")
                    nutrients = product_data.get("nutrients", {})
                    if nutrients:
                        for nutrient, value in list(nutrients.items())[:8]:
                            st.write(f"• {nutrient}: {value}")
                    else:
                        st.write("No nutrition data found")
            
            # Step 2: Analyze with CrewAI
            with st.spinner("🧠 AI is analyzing health impact..."):
                try:
                    result = analyze_food_data(product_data)
                except Exception as e:
                    st.error(f"Error during analysis: {str(e)}")
        else:
            st.error("❌ Product not found. Please check the barcode or try uploading a photo instead.")

# --- Display Results ---
if result:
    st.divider()
    st.subheader("📊 Health Analysis Results")
    
    try:
        # Parse the CrewAI output
        if hasattr(result, 'raw'):
            parsed = json.loads(result.raw)
        else:
            parsed = json.loads(str(result))
    except json.JSONDecodeError:
        st.error("⚠️ Could not parse analysis results")
        st.code(str(result))
        parsed = {}
    
    if parsed:
        # Score and Band Display
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            score = parsed.get("score", 0)
            st.metric(
                "Health Score", 
                f"{score}/100",
                delta=None,
                help="0-40: Poor | 41-70: Medium | 71-100: Good"
            )
        
        with col2:
            band = parsed.get("band", "Unknown")
            band_color = {
                "Good": "🟢",
                "Medium": "🟡", 
                "Poor": "🔴"
            }.get(band, "⚫")
            st.metric("Rating", f"{band_color} {band}")
        
        with col3:
            st.markdown("### 📝 Summary")
            st.write(parsed.get("summary", "No summary available"))
        
        # Key Health Drivers
        st.markdown("### ⚡ Key Health Drivers")
        drivers = parsed.get("drivers", [])
        if drivers:
            col1, col2 = st.columns(2)
            positive = [d for d in drivers if "✅" in d or any(word in d.lower() for word in ["good", "healthy", "beneficial", "high protein", "vitamins"])]
            negative = [d for d in drivers if "⚠️" in d or any(word in d.lower() for word in ["high", "excessive", "sugar", "sodium", "processed", "artificial"])]
            
            with col1:
                st.markdown("**Positive Factors:**")
                for driver in positive:
                    st.markdown(f"✅ {driver.replace('✅', '').strip()}")
                if not positive:
                    st.write("No significant positive factors found")
            
            with col2:
                st.markdown("**Concerns:**")
                for driver in negative:
                    st.markdown(f"⚠️ {driver.replace('⚠️', '').strip()}")
                if not negative:
                    st.write("No major concerns found")
        else:
            st.info("No specific health drivers identified")
        
        # Evidence & Citations
        with st.expander("📚 Evidence & Scientific Basis"):
            evidence = parsed.get("evidence", {})
            if evidence:
                st.json(evidence)
            else:
                st.write("No specific evidence citations available")

# --- Footer ---
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 0.9em;'>
    ⚠️ <b>Disclaimer:</b> This tool provides general health information and should not replace professional dietary advice.<br>
    Powered by CrewAI 🤖 | Data from OpenFoodFacts 📊
    </div>
    """,
    unsafe_allow_html=True
)