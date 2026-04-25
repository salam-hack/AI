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
PARSE_MODEL = "llama3"       # للفيتشر الأولى (متقربلهاش)
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
                    "temperature": 0.1 # تقليل العشوائية جداً للالتزام بالـ JSON
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
        # تنظيف النص من أي Markdown
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
# TRANSACTION PARSER (/parse) - ثابتة على Llama 3
# =====================================================
def parse_transaction(text: str):
    today = datetime(2026, 4, 25)
    prompt = f"""
You are a STRICT financial transaction parser.
Return ONLY valid JSON.
RULES: No text outside JSON. No explanation. No markdown. date format YYYY-MM-DD. currency EGP. categories: Food, Transport, Bills, Shopping, Other.

TODAY: {today.strftime('%Y-%m-%d')}
OUTPUT FORMAT: {{"amount": number, "merchant": string, "category": string, "date": string}}

TEXT: "{text}"
"""
    raw = call_llm(prompt, PARSE_MODEL)
    data = extract_json(raw)

    return data if data else {
        "amount": 0,
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
# SUMMARY MEMORY
# =====================================================
def update_summary(history_text):
    prompt = f"قم بتلخيص هذا السلوك المالي باختصار شديد باللغة العربية. النص:\n{history_text}"
    res = call_llm(prompt, CHAT_MODEL)
    return res if res else "لا يوجد ملخص."

# =====================================================
# CHATBOT (/chat) - شغال على Qwen 2.5
# =====================================================
@app.post("/chat")
def chat(req: ChatRequest):
    user_id = req.user_id
    message = req.message

    # =====================================================
    # MOCK PROFILE (الخلفية المالية لليوزر من الباك إيند)
    # =====================================================
    user_profile = {
        "income": 10000,
        "expenses": 7000,
        "subscriptions": 500,
        "debt": 2000
    }
    net_savings = user_profile['income'] - (user_profile['expenses'] + user_profile['subscriptions'])

    if user_id not in messages_store:
        messages_store[user_id] = []

    history = messages_store[user_id][-8:] # آخر 8 رسائل
    history_text = "\n".join([f"{m['role']}: {m['text']}" for m in history])
    summary = summary_store.get(user_id, "لا يوجد ملخص سابق.")

    # =====================================================
    # SMART SYSTEM PROMPT FOR QWEN 2.5
    # =====================================================
    prompt = f"""You are an Expert Financial Advisor AI.
You ONLY output valid JSON. No markdown, no greetings, no extra text.

USER FINANCIAL PROFILE:
- الدخل الشهري (Income): {user_profile['income']} جنيه
- المصروفات (Expenses): {user_profile['expenses']} جنيه
- الاشتراكات (Subscriptions): {user_profile['subscriptions']} جنيه
- الديون (Debt): {user_profile['debt']} جنيه
- الفائض الشهري (Net Savings): {net_savings} جنيه

RULES:
1. Answer the user based on their FINANCIAL PROFILE. If they ask "how much did I spend", use the profile data.
2. STRICT TOPIC BOUNDARY: You ONLY answer questions related to finance, budget, purchasing decisions, and savings.
3. IF OFF-TOPIC: If the user asks about history, coding, general knowledge, or anything non-financial, you MUST set "Decision" to "غير قابل للتطبيق" and reply in "Advice" politely like: "عذراً، أنا هنا لمساعدتك في أمورك المالية وإدارة ميزانيتك فقط. يرجى سؤالي في ما يخص ذلك."
4. Language: Arabic ONLY.

EXPECTED JSON FORMAT:
{{
  "Decision": "نعم/لا/ربما/غير قابل للتطبيق",
  "Reason": "تحليل دقيق بناءً على الأرقام، أو سبب الرفض لو الموضوع خارج التخصص",
  "Advice": "نصيحة مالية مفيدة، أو توجيه للمستخدم"
  "Expert_Insight": "معلومة إضافية بناءً على وضعك الحالي"
}}

CHAT HISTORY:
{history_text}

USER: {message}

OUTPUT JSON ONLY:
{{"""

    raw_reply = call_llm(prompt, CHAT_MODEL)

    # معالجة النص لضمان بداية الـ JSON
    if raw_reply and not raw_reply.strip().startswith('{'):
        raw_reply = '{' + raw_reply

    structured = extract_json(raw_reply)

    if not structured:
        structured = {
            "Decision": "غير متوفر",
            "Reason": "حدث خطأ في استيعاب الرد",
            "Advice": "يرجى توضيح سؤالك المالي مرة أخرى."
        }

    # إضافة الرسائل للذاكرة
    messages_store[user_id].append({"role": "user", "text": message})
    messages_store[user_id].append({"role": "assistant", "text": json.dumps(structured, ensure_ascii=False)})

    if len(messages_store[user_id]) % 5 == 0:
        full_history = "\n".join([f"{m['role']}: {m['text']}" for m in messages_store[user_id]])
        summary_store[user_id] = update_summary(full_history)

    return {
        "success": True,
        "reply": structured
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)