# 🍏 Health Rater Project Overview

## 🎯 Goal

Analyze food products for **healthiness** using **AI, Nutri-Score, and barcode/label data**.

---

## 📥 1. Input Methods

Users can provide product info in three ways:

- **Barcode Scan**: Scan a product’s barcode using the camera.
- **Label Photo Upload**: Upload a photo of the nutrition label/ingredients.
- **Text Search**: Type the product name to search.

---

## 📊 2. Data Extraction

- **Barcode**:  
  The app sends the barcode to the **Open Food Facts API** to fetch product details (ingredients, nutrition).

- **Label Photo**:  
  The image is **preprocessed** (contrast, denoising, sharpening) and sent to an **AI model (LLM/Gemini/GPT-4o)** for **OCR and text extraction**.

- **Text Search**:  
  The app queries the **database/API** for matching products.

---

## 🤖 3. AI-Powered Analysis

Extracted data (**ingredients, nutrition**) is processed by an **AI agent**.  
The agent evaluates the product for healthiness, considering:

- Nutritional values (**calories, sugar, fat, salt, etc.**)
- Ingredients (**presence of sweeteners, additives, etc.**)
- Product type (**beverage, cheese, etc.**)

---

## 🧮 4. Health Scoring

- The **Nutri-Score algorithm** calculates a **health score (0–100)** and a **rating band (Good, Medium, Poor)**.
- The score is based on **nutrition facts** and **product type**.

---

## 💡 5. Insights & Feedback

The app displays:

- ✅ Health Score and Band
- ✅ Key health drivers (positive/negative)
- ✅ Plain-language explanation of the score
- ✅ Suggestions for missing data or improvements

---

## 🕒 6. History & User Experience

- Each analyzed product is **saved to a history file**.
- Users can review **past searches and scores**.

---

## 🔄 Step-by-Step Flow

1. User opens the app.
2. Chooses input method: **barcode, photo, or text**.
3. App extracts product data:
   - Barcode → API call
   - Photo → AI OCR
   - Text → API/database search
4. AI agent analyzes the product.
5. Nutri-Score is calculated.
6. Results and insights are displayed.
7. Product is saved to history.

## 📚 Learning Points

- How to use **APIs** for product data.
- How to **preprocess images** for OCR.
- How to use **AI models** for text extraction and analysis.
- How to implement **health scoring algorithms**.
- How to build a **user-friendly frontend** and maintain search history.

---

# ⚙️ Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/anujpatel2899/HealthLabel
cd HealthLabel
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

### 3. Install Dependencies

The project uses **uv** for fast package management, but **pip** works perfectly too.

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a file named **.env** in the root of the project directory and add your API key:

```bash
OPENAI_API_KEY="YOUR_API_KEY_HERE"
```

The application will automatically load this key.

### 5. Run the Plotly App

```bash
python main.py
```

The application should now be open and running in your **web browser**! 🚀
