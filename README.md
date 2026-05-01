<img width="7680" height="4096" alt="Portfolio Cover" src="https://github.com/user-attachments/assets/231e7f80-008e-475f-8a56-2cfd71f2ff87" />
# 🤖 Modabber AI Backend

An intelligent AI-powered backend system for **Modabber**, designed to process natural language financial inputs, analyze user behavior, and generate smart insights using local LLMs.

---

## 💡 Overview

This AI service acts as the brain of the Modabber application.

It allows users to:
- Convert natural language into structured financial transactions
- Analyze spending behavior
- Ask financial questions in chat format
- Generate smart financial insights using AI
- Support voice/text/image-based inputs (via preprocessing layer)

---

## 🧠 AI Capabilities

- 🧾 Transaction extraction from free text
- 💬 Financial chatbot assistant
- 📊 Spending behavior analysis
- ⚠️ Smart alerts (overspending / unusual activity)
- 🎯 Personalized financial insights
- 🧠 Context-aware conversation memory

---

## ⚙️ Tech Stack

### 🧠 AI Layer
- Ollama (Local LLM runtime)
- llama3.1 LLM

### 🐍 Backend
- Python
- FastAPI

### 📦 Data & Validation
- Pydantic

### 🌐 Networking
- Requests

---

## 🏗️ Architecture

The system is built as a modular AI service:

User Input → FastAPI Endpoint → Prompt Processing → Ollama (Qwen2.5) → Response Parsing → JSON Output

---

## 🚀 Features

- ⚡ Fast API responses
- 🔒 Fully local LLM execution (via Ollama)
- 🧠 Structured output using Pydantic models
- 💬 Chat-based financial assistant
- 📊 Smart transaction classification
- 🔌 Easy integration with mobile backend

---

## 📡 API Endpoints

### 🔹 Chat with AI
```
POST /chat
```

**Request:**
```json
{
  "message": "I spent 200 on food and 50 on transport today"
}
```

**Response:**
```json
{
  "transactions": [
    {
      "amount": 200,
      "category": "Food",
      "type": "expense"
    },
    {
      "amount": 50,
      "category": "Transport",
      "type": "expense"
    }
  ],
  "summary": "You spent 250 today mostly on food."
}
```

---

## 🧪 Example Use Cases

- "I bought groceries for 300 EGP"
- "How much did I spend this week?"
- "Analyze my spending habits"
- "Did I overspend this month?"

---

## 📦 Installation

```bash
git clone https://github.com/your-repo/modabber-ai.git
cd modabber-ai
pip install -r requirements.txt
```

---

## 🧠 Run Ollama Model

Make sure Ollama is installed and run:

```bash
ollama run llama3.1
```

---

## ▶️ Start Server

```bash
uvicorn main:app --reload
```

---

## 📁 Project Structure

```
modabber-ai/
│
├── app/
│   ├── main.py
│   ├── routes/
│   ├── services/
│   ├── models/
│   └── prompts/
│
├── requirements.txt
└── README.md
```

---

## 🔐 Future Improvements

- Voice-to-text integration
- Image receipt processing
- Advanced financial forecasting
- Multi-language support
- User-specific memory system

---

## 👨‍💻 Developed by

- **Bilal_Weshah

**

---

## 📄 License

This project is for educational and development purposes.
