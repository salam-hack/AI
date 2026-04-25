from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

app = FastAPI()

# الرابط الخاص بـ Chat API
OLLAMA_URL = "http://localhost:11434/api/chat"
CHAT_MODEL = "qwen2.5"

# مخزن الرسائل
messages_store = {}

class ChatRequest(BaseModel):
    user_id: int
    message: str

def call_llm(messages, model_name):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # ضروري جداً لضمان عدم الاجتهاد أو الإجابة خارج النص
                    "top_p": 0.1,
                }
            },
            timeout=100
        )
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "")
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return "عذراً، واجهت مشكلة فنية. حاول مرة أخرى."

# =====================================================
# CHATBOT ENDPOINT
# =====================================================
@app.post("/chat")
def chat(req: ChatRequest):
    user_id = req.user_id
    user_message = req.message

    user_profile = {
        "income": 10000,
        "expenses": 7000,
        "subscriptions": 0,
        "debt": 0
    }
    net_savings = user_profile['income'] - (user_profile['expenses'] + user_profile['subscriptions'])

    if user_id not in messages_store:
        messages_store[user_id] = [
            {
                "role": "system",
                "content": f"""أنت "المستشار المالي الاستراتيجي" في مصر. وظيفتك الإجابة عن المال فقط.

[بروتوكول الرفض الصارم - حظر التجول]:
1. ممنوع منعاً باتاً تقديم أي معلومات أو شروحات عن: الأديان، السياسة، العلوم، الطبخ، التكنولوجيا، أو أي مجال غير مالي.
2. إذا سألك المستخدم عن أي موضوع غير مالي، رد **فقط** بهذه الجملة ولا تضف عليها حرفاً واحداً: "عذراً، أنا مستشار مالي متخصص فقط في إدارة أموالك واستثماراتك. لا يمكنني تقديم معلومات خارج هذا النطاق. كيف يمكنني مساعدتك مالياً اليوم؟".
3. **تحذير**: لا تقدم "نبذة" أو "ملخص" أو "مقدمة" عن الموضوع غير المالي قبل الاعتذار. ارفض مباشرة وبشكل قاطع.

[البيانات المالية]:
- الدخل: {user_profile['income']} ج.م.
- الفائض: {net_savings} ج.م."""
            }
        ]

    # إضافة رسالة المستخدم
    messages_store[user_id].append({"role": "user", "content": user_message})

    # الحفاظ على الذاكرة (آخر 6 رسائل + نظام)
    if len(messages_store[user_id]) > 7:
        system_msg = messages_store[user_id][0]
        recent_history = messages_store[user_id][-6:]
        messages_store[user_id] = [system_msg] + recent_history

    # طلب الرد
    reply = call_llm(messages_store[user_id], CHAT_MODEL)

    # حفظ الرد
    messages_store[user_id].append({"role": "assistant", "content": reply})

    return {
        "success": True,
        "reply": reply,
        "context_depth": len(messages_store[user_id]) // 2
    }

if __name__ == "__main__":
    import uvicorn
    print("--- المستشار المالي (وضع الحماية القصوى) يعمل الآن ---")
    uvicorn.run(app, host="0.0.0.0", port=8000)