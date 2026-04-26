from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import json
from datetime import datetime

app = FastAPI()

# =====================================================
# CONFIGURATION - Unified Model (Optimized)
# =====================================================
OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"

SHARED_MODEL = "qwen2.5"

messages_store = {}

class Transaction(BaseModel):
    text: str

class ChatRequest(BaseModel):
    user_id: int
    message: str

# =====================================================
# FEATURE 1: TRANSACTION PARSER
# =====================================================
def call_parser_model(text: str):
    prompt = f"""
Task: Strict Financial Transaction Parser.
Return ONLY valid JSON.
IMPORTANT: Today is 2026-04-25. Yesterday is 2026-04-24.
Output format: {{"amount": number, "merchant": string, "category": string, "date": string}}
Text: "{text}"
"""
    try:
        response = requests.post(
            OLLAMA_GENERATE_URL,
            json={
                "model": SHARED_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0}
            },
            timeout=60
        )
        raw = response.json()["response"]
        start = raw.find('{')
        end = raw.rfind('}') + 1
        return json.loads(raw[start:end])
    except:
        return {"amount": None, "merchant": "Unknown", "category": "Other", "date": "2026-04-25"}

@app.post("/parse")
def parse(tx: Transaction):
    return {"success": True, "data": call_parser_model(tx.text)}

# =====================================================
# FEATURE 2: FINANCIAL ADVISOR CHAT (With Sharia Compliance)
# =====================================================
def call_advisor_llm(messages):
    try:
        response = requests.post(
            OLLAMA_CHAT_URL,
            json={
                "model": SHARED_MODEL,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "top_p": 0.1,
                    "num_ctx": 2048, # تقليل المساحة لـ 2048 لمنع الـ Error 500 تماماً
                    "num_predict": 500 # تحديد طول الرد للحفاظ على ثبات الرامات
                }
            },
            timeout=100
        )
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "")
    except Exception as e:
        print(f"Error calling Advisor LLM: {e}")
        return "عذراً، واجهت مشكلة فنية. يرجى المحاولة لاحقاً."

@app.post("/chat")
def chat(req: ChatRequest):
    user_id = req.user_id
    user_message = req.message

    user_profile = {"income": 10000, "expenses": 7000, "subscriptions": 0, "debt": 0}
    net_savings = user_profile['income'] - (user_profile['expenses'] + user_profile['subscriptions'])

    if user_id not in messages_store:
        messages_store[user_id] = [
            {
                "role": "system",
                "content": f"""أنت "المستشار المالي الاستراتيجي" في مصر. وظيفتك الإجابة عن المال فقط.

[الالتزام بالشريعة الإسلامية]:
- يجب أن تكون كافة نصائحك المالية متوافقة مع أحكام الشريعة الإسلامية.
- ابتعد تماماً عن اقتراح القروض الربوية (الربا) أو الفوائد البنكية التقليدية.
- شجع على الاستثمارات الحلال، الصدقة، والادخار بعيداً عن المعاملات المحرمة.

[بروتوكول الرفض الصارم]:
1. ممنوع تقديم أي معلومات خارج المال (أديان، سياسة، طبخ، إلخ).
2. إذا سُئلت عن موضوع غير مالي، رد بـ: "عذراً، أنا مستشار مالي متخصص فقط في إدارة أموالك واستثماراتك. لا يمكنني تقديم معلومات خارج هذا النطاق. كيف يمكنني مساعدتك مالياً اليوم؟".
رد باللغة العربية فقط
اياك تقترح لينك لأي موقع من عندك 
[البيانات المالية الحالية]: دخل {user_profile['income']} ج.م، فائض {net_savings} ج.م."""
            }
        ]

    # إضافة رسالة المستخدم
    messages_store[user_id].append({"role": "user", "content": user_message})

    # --- الحل الجذري لمشكلة الـ Error 500 ---
    # نحتفظ برسالة النظام (0) ثم آخر 3 رسائل فقط (سؤال وجواب قديم + سؤال جديد)
    if len(messages_store[user_id]) > 4:
        system_msg = messages_store[user_id][0]
        recent_history = messages_store[user_id][-3:]
        messages_store[user_id] = [system_msg] + recent_history

    reply = call_advisor_llm(messages_store[user_id])
    messages_store[user_id].append({"role": "assistant", "content": reply})

    return {
        "success": True,
        "reply": reply,
        "context_depth": len(messages_store[user_id]) // 2
    }

if __name__ == "__main__":
    import uvicorn
    print(f"--- المستشار الإسلامي والـ Parser يعملان الآن على موديل: {SHARED_MODEL} ---")
    uvicorn.run(app, host="0.0.0.0", port=8000)