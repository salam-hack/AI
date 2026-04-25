from fastapi import FastAPI
from pydantic import BaseModel
import requests
import json
import re
from datetime import datetime, timedelta

app = FastAPI()

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

# =====================================================
# MEMORY (replace with DB later)
# =====================================================
messages_store = {}
summary_store = {}

# =====================================================
# REQUEST MODELS
# =====================================================
class Transaction(BaseModel):
    text: str

class ChatRequest(BaseModel):
    user_id: int
    message: str


# =====================================================
# CALL OLLAMA
# =====================================================
def call_llm(prompt):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
    )
    return response.json()["response"]


# =====================================================
# SAFE JSON PARSER
# =====================================================
def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return None


# =====================================================
# 1. TRANSACTION PARSER (/parse)
# =====================================================
def parse_transaction(text: str):

    today = datetime(2026, 4, 25)

    prompt = f"""
You are a strict financial transaction parser.

Return ONLY valid JSON.

IMPORTANT:
- Today is {today.strftime('%Y-%m-%d')}
- "yesterday" = {(today - timedelta(days=1)).strftime('%Y-%m-%d')}

Rules:
- No explanations
- No markdown
- No comments
- date must be YYYY-MM-DD
- currency is EGP
- categories: Food, Transport, Bills, Shopping, Other

Output:
{{
  "amount": number,
  "merchant": string,
  "category": string,
  "date": string
}}

Text:
"{text}"
"""

    raw = call_llm(prompt)
    data = extract_json(raw)

    return data if data else {
        "amount": None,
        "merchant": "Unknown",
        "category": "Other",
        "date": today.strftime("%Y-%m-%d")
    }


@app.post("/parse")
def parse(tx: Transaction):
    return {
        "success": True,
        "data": parse_transaction(tx.text)
    }


# =====================================================
# 2. MEMORY SUMMARY
# =====================================================
def update_summary(history_text):
    prompt = f"""
You are a financial memory compressor.

Summarize ONLY financial behavior:
- income
- spending
- debt
- subscriptions

Return short paragraph only.

Text:
{history_text}
"""
    return call_llm(prompt)


# =====================================================
# 3. CHATBOT (/chat)
# =====================================================
@app.post("/chat")
def chat(req: ChatRequest):

    user_id = req.user_id
    message = req.message

    # =====================================================
    # BACKEND NOTE:
    # Replace with real DB user profile
    # =====================================================
    user_profile = {
        "income": 10000,
        "expenses": 7000,
        "subscriptions": 500,
        "debt": 2000
    }

    if user_id not in messages_store:
        messages_store[user_id] = []

    messages_store[user_id].append({
        "role": "user",
        "text": message
    })

    history = messages_store[user_id][-10:]

    history_text = "\n".join(
        [f"{m['role']}: {m['text']}" for m in history]
    )

    summary = summary_store.get(user_id, "No summary yet")

    prompt = f"""
You are a STRICT financial assistant.

RULE:
- Only answer finance-related questions
You MUST respond ONLY in Arabic.
Do not use any English words under any condition.
- If not finance → refuse politely

USER PROFILE:
Income: {user_profile['income']}
Expenses: {user_profile['expenses']}
Subscriptions: {user_profile['subscriptions']}
Debt: {user_profile['debt']}

MEMORY:
{summary}

CHAT HISTORY:
{history_text}

USER MESSAGE:
{message}
Respond ONLY in clean Arabic.
No English words.
No mixed languages.
No extra commentary.
Return ONLY in this format:

Decision: (Yes / No / Maybe)
Reason: short explanation
Advice: actionable advice

Rules:
- Arabic only
- No slang
- No extra text
- No emojis
"""

    reply = call_llm(prompt)

    messages_store[user_id].append({
        "role": "assistant",
        "text": reply
    })

    # update summary every 5 messages
    if len(history) % 5 == 0:
        full_history = "\n".join(
            [f"{m['role']}: {m['text']}" for m in messages_store[user_id]]
        )
        summary_store[user_id] = update_summary(full_history)

    return {
        "success": True,
        "reply": reply
    }