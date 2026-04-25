from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import json
import re
from datetime import datetime, timedelta

app = FastAPI()

OLLAMA_URL = "http://localhost:11434/api/generate"

# =====================================================
# MODELS CONFIGURATION
# =====================================================
PARSE_MODEL = "llama3"       # للفيتشر الأولى
CHAT_MODEL = "qwen2.5"       # للشات بوت الذكي

# =====================================================
# MEMORY
# =====================================================
messages_store = {}
summary_store = {}

class Transaction(BaseModel):
    text: str

class ChatRequest(BaseModel):
    user_id: int
    message: str

# =====================================================
# LLM CALL (يدعم اختيار الموديل)
# =====================================================
def call_llm(prompt, model_name):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1
                }
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        print(f"Error calling Ollama ({model_name}): {e}")
        return None

# =====================================================
# SAFE JSON PARSER
# =====================================================
def extract_json(text):
    if not text: return None
    try:
        text = re.sub(r"```json|```", "", text)
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            json_str = text[start_idx:end_idx+1]
            return json.loads(json_str)
    except Exception as e:
        print(f"JSON Parsing Error: {e} | Text: {text}")
        return None
    return None

# =====================================================
# TRANSACTION PARSER (/parse)
# =====================================================
def parse_transaction(text: str):
    today = datetime(2026, 4, 25)
    prompt = f"""
You are a STRICT financial transaction parser. Return ONLY valid JSON.
Format: {{"amount": number, "merchant": string, "category": string, "date": string}}
TEXT: "{text}"
"""
    raw = call_llm(prompt, PARSE_MODEL)
    return extract_json(raw) or {"amount": 0, "merchant": "Unknown", "category": "Other", "date": today.strftime("%Y-%m-%d")}

@app.post("/parse")
def parse(tx: Transaction):
    return {"success": True, "data": parse_transaction(tx.text)}

# =====================================================
# CHATBOT (/chat)
# =====================================================
@app.post("/chat")
def chat(req: ChatRequest):
    user_id = req.user_id
    message = req.message

    user_profile = {
        "income": 10000,
        "expenses": 7000,
        "subscriptions": 500,
        "debt": 2000
    }
    net_savings = user_profile['income'] - (user_profile['expenses'] + user_profile['subscriptions'])

    if user_id not in messages_store:
        messages_store[user_id] = []

    history = messages_store[user_id][-8:]
    history_text = "\n".join([f"{m['role']}: {m['text']}" for m in history])

    # البرومبت المطور لضمان ردود ذكية ومتحفظة مالياً
    prompt = f"""You are a High-Level Financial Advisor. Output ONLY valid JSON. Arabic Language only.

USER PROFILE:
- Income: {user_profile['income']} EGP
- Net Monthly Savings: {net_savings} EGP
- Current Debt: {user_profile['debt']} EGP

CONSTRAINTS:
1. Decision Logic: 
   - If User wants to buy something > Net Savings, and has Debt > 0, the Decision MUST be "لا" or "ربما".
   - Always suggest paying off Debt first if it exists.
2. Expert_Insight: 
   - Provide a deep analysis using numbers/percentages. 
   - Example: "Your debt is 20% of your income, paying it off saves you X".
3. Off-Topic: If asked about non-financial things, refuse politely.

EXPECTED JSON FORMAT:
{{
  "Decision": "نعم/لا/ربما/غير قابل للتطبيق",
  "Reason": "تحليل رقمي بناءً على الفائض والديون",
  "Advice": "خطوة عملية واضحة",
  "Expert_Insight": "رؤية تحليلية عميقة مبنية على الأرقام والنسب"
}}

CHAT HISTORY:
{history_text}

USER MESSAGE:
{message}

OUTPUT JSON ONLY:
{{"""

    raw_reply = call_llm(prompt, CHAT_MODEL)
    if raw_reply and not raw_reply.strip().startswith('{'):
        raw_reply = '{' + raw_reply

    structured = extract_json(raw_reply)

    if not structured:
        structured = {
            "Decision": "غير متوفر",
            "Reason": "خطأ في التحليل",
            "Advice": "يرجى المحاولة ثانية",
            "Expert_Insight": "لا يمكن تقديم رؤية حالياً"
        }

    messages_store[user_id].append({"role": "user", "text": message})
    messages_store[user_id].append({"role": "assistant", "text": json.dumps(structured, ensure_ascii=False)})

    return {"success": True, "reply": structured}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)