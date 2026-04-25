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
PARSE_MODEL = "llama3"
CHAT_MODEL = "qwen2.5"

# تخزين الرسائل
messages_store = {}


class Transaction(BaseModel):
    text: str


class ChatRequest(BaseModel):
    user_id: int
    message: str


def call_llm(prompt, model_name):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return None


# =====================================================
# SAFE JSON PARSER (المحسن والمطور)
# =====================================================
def extract_json(text):
    if not text: return None
    try:
        # تنظيف علامات المارك داون لو وجدت
        text = re.sub(r"```json|```", "", text).strip()

        # البحث عن حدود الـ JSON
        start_idx = text.find('{')
        end_idx = text.rfind('}')

        if start_idx != -1 and end_idx != -1:
            json_str = text[start_idx:end_idx + 1]
            return json.loads(json_str)

        # محاولة أخيرة لو النص عبارة عن JSON خام بدون أقواس خارجية (نادرة)
        return json.loads(text)
    except Exception as e:
        print(f"JSON Parsing Error: {e}")
    return None


# =====================================================
# CHATBOT (/chat)
# =====================================================
@app.post("/chat")
def chat(req: ChatRequest):
    user_id = req.user_id
    message = req.message

    # بيانات المستخدم الثابتة
    user_profile = {
        "income": 10000,
        "expenses": 7000,
        "subscriptions": 0,
        "debt": 0
    }
    net_savings = user_profile['income'] - (user_profile['expenses'] + user_profile['subscriptions'])

    if user_id not in messages_store:
        messages_store[user_id] = []

    # جلب التاريخ وتحويله لنص نظيف للموديل
    history = messages_store[user_id][-6:]  # تقليل العدد لـ 6 لضمان استقرار أطول
    history_text = ""
    for m in history:
        history_text += f"{m['role']}: {m['text']}\n"

    # البرومبت المطور بالحزم والذكاء المالي
    prompt = f"""You are a High-Level Financial Advisor. Output ONLY valid JSON. Arabic Language ONLY.

USER PROFILE:
- Income: {user_profile['income']} EGP
- Net Monthly Savings: {net_savings} EGP
- Current Debt: {user_profile['debt']} EGP

STRICT RULES:
1. Decision Logic: If (Price > {net_savings}) AND (Debt > 0), Decision MUST be "لا" or "ربما".
2. Financial Logic:  كن مستشاراً حكيماً ولكن حازم قليلا من ناحية الصرف على اشياء لا تنفع.
3. Expert_Insight: استخدم الأرقام والنسب المئوية دائماً (مثلاً: "هذا يمثل X% من دخلك").
4. Response Format: JSON ONLY. No conversational text before or after the JSON.

EXPECTED JSON FORMAT:
{{
  "Decision": "نعم/لا/ربما",
  "Reason": "تحليل مالي مفصل بناءً على الأرقام",
  "Advice": "نصيحة عملية واضحة ومباشرة ومفصلة",
  "Expert_Insight": "رؤية تحليلية عميقة تربط بين القرار ومستقبل المستخدم المالي وتكون مفصلة وواضحة مع الأسباب لماذا اتخاذ هذا القرار مهم"
}}

CHAT HISTORY:
{history_text}

USER MESSAGE:
{message}

OUTPUT JSON:"""

    raw_reply = call_llm(prompt, CHAT_MODEL)

    # محاولة الاستخراج الأولى
    structured = extract_json(raw_reply)

    # محاولة الاستخراج الثانية بإضافة قوس لو الموديل نسيه
    if not structured and raw_reply:
        structured = extract_json("{" + raw_reply)

    # لو كل المحاولات فشلت
    if not structured:
        structured = {
            "Decision": "غير متوفر",
            "Reason": "حدث خطأ في معالجة البيانات",
            "Advice": "يا بطل، حصل ضغط عندي، ممكن تعيد سؤالك بوضوح؟",
            "Expert_Insight": "لا يمكن تقديم رؤية حالياً"
        }

    # تخزين الرسائل (بنخزن الـ Advice بس عشان نوفر مساحة الذاكرة للمرات الجاية)
    messages_store[user_id].append({"role": "user", "text": message})
    clean_reply = f"{structured.get('Decision', '')} - {structured.get('Advice', '')}"
    messages_store[user_id].append({"role": "assistant", "text": clean_reply})

    return {"success": True, "reply": structured}


if __name__ == "__main__":
    import uvicorn

    # تشغيل السيرفر
    uvicorn.run(app, host="0.0.0.0", port=8000)