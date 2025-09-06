import streamlit as st
import json
from crew_setup import analyze_input, analyze_input_with_image

# --- Streamlit Page Config ---
st.set_page_config(page_title="CrewAI Packaged Food Rating App", layout="wide")
st.title("🥫 CrewAI Packaged Food Rating App")

# --- Input Method Selection ---
input_method = st.radio("Choose input method", ["Paste text", "Upload photo"])

ingredients_text = ""
result = None

# --- Text input branch ---
if input_method == "Paste text":
    ingredients_text = st.text_area("Paste Ingredients / Nutrition info here:")

    if st.button("Analyze"):
        if ingredients_text.strip() == "":
            st.warning("Please paste text first.")
        else:
            with st.spinner("Analyzing text with CrewAI..."):
                result = analyze_input(ingredients_text)

# --- Image input branch ---
elif input_method == "Upload photo":
    uploaded_file = st.file_uploader(
        "Upload a food label image",
        type=["jpg", "jpeg", "png"]
    )
    if uploaded_file is not None and st.button("Analyze"):
        with st.spinner("Analyzing image with CrewAI..."):
            result = analyze_input_with_image(uploaded_file)

# --- Show results ---
if result:
    try:
        # Parse JSON output from CrewAI
        parsed = json.loads(result.raw)
    except Exception:
        st.error("⚠️ Could not parse CrewAI output as JSON")
        st.write(result.raw)
        parsed = {}

    # Use parsed dict instead of result.get()
    st.subheader("📊 Health Score")
    st.metric("Score (0–100)", parsed.get("score", "N/A"))
    st.write(f"**Band:** {parsed.get('band', 'Unknown')}")

    st.subheader("📝 Summary")
    st.write(parsed.get("summary", "No summary available"))

    st.subheader("⚡ Key Drivers")
    for d in parsed.get("drivers", []):
        st.markdown(f"- {d}")

    st.subheader("📚 Evidence & Rules")
    st.json(parsed.get("evidence", {}))
