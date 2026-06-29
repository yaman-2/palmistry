# Palmistry & YouTube Agent Portal

A multi-functional repository hosting:
1. **Cosmic Insights / YouTube & Video Agent API** (Root directory) — A FastAPI and HTML/CSS web application that allows you to query videos and manage customer inquiries.
2. **Samudrika Palm Reading MVP** (`/samudrika` subdirectory) — A premium mobile-first Vedic Palmistry analysis app using FastAPI and Gemini multimodal AI.

---

## 🚀 Getting Started

### 1. Run Cosmic Insights (Main Application)
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn api:app --reload
```
* **Local Web Interface:** [http://localhost:8000](http://localhost:8000)
* **Interactive API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Run Samudrika Palm Reading MVP
```bash
# Navigate to the subdirectory
cd samudrika

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server (on port 8001)
uvicorn app:app --reload --port 8001
```
* **Local Web Interface:** [http://localhost:8001](http://localhost:8001)

---

## 🛠️ Tech Stack
* **Backend:** FastAPI (Python)
* **Frontend:** Vanilla HTML, CSS, JavaScript (TailwindCSS in Samudrika)
* **AI Engine:** Gemini Multimodal API & SentenceTransformers
