# 🥫 AI-Powered Food Health Analyzer

An intelligent web application that instantly analyzes packaged food products to provide clear health scores, insights, and evidence-based nutritional feedback. This tool leverages AI agents built with **CrewAI** and **Google's Gemini** model to demystify complex food labels.

---

## ✨ Key Features

- **🤖 Smart Input Methods**: Analyze products in three convenient ways:
  - **Live Barcode Scanning**: Use your camera to scan a product's barcode for instant analysis.
  - **Label Image Upload**: Take a photo of the nutrition label and ingredients list for AI-powered OCR and analysis.
  - **Search by Name**: Find products by typing their name and selecting from a list of results.
- **🧠 AI-Powered Analysis**: Utilizes a sophisticated AI agent to evaluate products based on their ingredients, nutritional values, and processing levels.
- **📊 Clear Health Scoring**: Get a simple **Health Score (0-100)** and a rating **Band (Good, Medium, Poor)** to quickly assess a product's healthiness.
- **⚡ Plain-Language Insights**: Understand the "why" behind the score with a list of key **Health Drivers**—both positive and negative.
- **📚 Evidence-Based Breakdown**: Dig deeper with an evidence panel that shows how the product's nutritional values stack up against established guidelines from health organizations like the WHO and FDA.

---

## ⚙️ How It Works (My Thought Process)

This project started with a simple goal: use the power of modern LLMs, specifically through the CrewAI framework, to make nutritional information easy to understand. The process breaks down into four main steps.

### 1. Input & Data Extraction

The first challenge was to get product data into the system. I decided on three user-friendly methods:

- For barcodes (scanned or from a name search), the app queries the extensive **OpenFoodFacts database** via an API to fetch structured data like ingredients and a complete nutrition panel.
- For a photo of the label, the image is sent directly to the **Gemini multimodal model**. Its powerful OCR capabilities extract the text from the image, turning a picture of ingredients and a nutrition table into machine-readable text.

### 2. AI Analysis with CrewAI

This is the core of the project. Instead of just parsing text, I created an **"Expert Food Analyst"** agent using CrewAI.

- **The Agent**: This AI agent is given a specific role and goal: "Analyze food products for health impact and provide evidence-based scores." Its backstory primes it to act like an expert nutritionist.
- **The Task**: The agent is assigned a detailed task with a strict prompt. This prompt, loaded from the `/prompts` directory, instructs the AI on exactly how to evaluate the food data. It tells the agent to check for processed ingredients, compare sugar/sodium/fat levels against WHO/FDA guidelines, and consider fiber and protein content.
- **The Output**: The most crucial part is forcing the AI to return its analysis in a standardized **JSON format**. This ensures the output is consistent and predictable, making it easy for the user interface to handle.

### 3. Scoring via LLM

The LLM doesn't just extract data; it performs the scoring itself. Based on the rules and guidelines in its prompt, it calculates a single **Health Score** from 0 to 100. This score is a holistic measure of the product's healthiness. It then categorizes this score into a simple **Band (Good, Medium, Poor)** for an at-a-glance understanding.

### 4. UI Display in Streamlit

Finally, the structured JSON output from the AI agent is passed to the **Streamlit** front end. I parsed this JSON to create a clean and intuitive interface:

- The score and band are displayed prominently using `st.metric`.
- The drivers (positive and negative points) are shown in columns with clear icons (✅ and ⚠️).
- The evidence section is formatted into readable tables and lists, showing the specific nutritional data and how it was rated against health guidelines, providing transparency and trust in the analysis.

---

## 🛠️ Tech Stack

- **Backend Framework**: CrewAI
- **LLM**: Google Gemini 2.0 Flash
- **Frontend**: Streamlit
- **Data Source**: OpenFoodFacts API
- **Barcode Reading**: `pyzbar`, `opencv-python-headless`
- **Camera Streaming**: `streamlit-webrtc`

---

## 🚀 Setup and Installation

Follow these steps to get the Food Health Analyzer running on your local machine.

### Prerequisites

- Python 3.9+
- A Google API Key with the "Generative Language API" enabled. You can get one from the [Google AI Studio](https://aistudio.google.com/app/apikey).

### Installation Steps

#### 1. Clone the Repository

```bash
git clone [https://github.com/your-username/food-health-analyzer.git](https://github.com/your-username/food-health-analyzer.git)
cd food-health-analyzer
2. Create a Virtual Environment
Bash

python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
3. Install Dependencies
The project uses uv for fast package management, but pip works perfectly too.

Bash

pip install -r requirements.txt
4. Set Up Environment Variables
Create a file named .env in the root of the project directory and add your Google API Key:

GOOGLE_API_KEY="YOUR_API_KEY_HERE"
The application will automatically load this key.

5. Run the Streamlit App
Bash

streamlit run app.py
The application should now be open and running in your web browser!
```
