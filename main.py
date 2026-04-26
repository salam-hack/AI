from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import json

app = FastAPI()

# =====================================================
# CONFIGURATION
# =====================================================
OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"

SHARED_MODEL = "qwen2.5"

USER_PROFILE_API = "http://backend/api/user-profile"
CHAT_HISTORY_API = "http://backend/api/chat-history"
SAVE_MESSAGE_API = "http://backend/api/save-message"
CURRENT_DATE_API = "http://backend/api/current-date"

messages_store = {}

class Transaction(BaseModel):
    text: str

class ChatRequest(BaseModel):
    user_id: int
    message: str

# =====================================================
# BACKEND FUNCTIONS
# =====================================================
def get_user_profile(user_id):
    res = requests.get(f"{USER_PROFILE_API}/{user_id}", timeout=5)
    if res.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch user profile")
    return res.json()

def get_chat_history(user_id):
    res = requests.get(f"{CHAT_HISTORY_API}/{user_id}", timeout=5)
    if res.status_code != 200:
        return []
    return res.json()

def save_message(user_id, role, content):
    try:
        requests.post(
            SAVE_MESSAGE_API,
            json={
                "user_id": user_id,
                "role": role,
                "content": content
            },
            timeout=5
        )
    except:
        pass

def get_current_dates():
    res = requests.get(CURRENT_DATE_API, timeout=5)
    if res.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch current date")
    return res.json()

# =====================================================
# FEATURE 1: TRANSACTION PARSER
# =====================================================
def call_parser_model(text: str):
    dates = get_current_dates()

    prompt = f"""
Task: Strict Financial Transaction Parser.
Return ONLY valid JSON.
IMPORTANT: Today is {dates['today']}. Yesterday is {dates['yesterday']}.
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
        return {"amount": None, "merchant": "Unknown", "category": "Other", "date": dates['today']}

@app.post("/parse")
def parse(tx: Transaction):
    return {"success": True, "data": call_parser_model(tx.text)}

# =====================================================
# FEATURE 2: FINANCIAL ADVISOR CHAT
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
                    "num_ctx": 2048,
                    "num_predict": 500
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

    user_profile = get_user_profile(user_id)
    net_savings = user_profile['income'] - (user_profile['expenses'] + user_profile['subscriptions'])

    if user_id not in messages_store:
        history = get_chat_history(user_id)

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
        ] + history[-3:]

    messages_store[user_id].append({"role": "user", "content": user_message})
    save_message(user_id, "user", user_message)

    if len(messages_store[user_id]) > 4:
        system_msg = messages_store[user_id][0]
        recent_history = messages_store[user_id][-3:]
        messages_store[user_id] = [system_msg] + recent_history

    reply = call_advisor_llm(messages_store[user_id])

    messages_store[user_id].append({"role": "assistant", "content": reply})
    save_message(user_id, "assistant", reply)

    return {
        "success": True,
        "reply": reply,
        "context_depth": len(messages_store[user_id]) // 2
    }

if __name__ == "__main__":
    import uvicorn
    print(f"--- المستشار الإسلامي والـ Parser يعملان الآن على موديل: {SHARED_MODEL} ---")
    uvicorn.run(app, host="0.0.0.0", port=8000)