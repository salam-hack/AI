from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

app = FastAPI()

# تم التغيير لـ chat لضمان استقرار الذاكرة ومنع خطأ 500
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
                "messages": messages, # نرسل قائمة الرسائل مباشرة
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                }
            },
            timeout=100
        )
        response.raise_for_status()
        # استخراج المحتوى من هيكل الـ Chat API
        return response.json().get("message", {}).get("content", "")
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return "عذراً، واجهت مشكلة فنية في معالجة طلبك المالي حالياً. حاول مرة أخرى."

# =====================================================
# CHATBOT ENDPOINT
# =====================================================
@app.post("/chat")
def chat(req: ChatRequest):
    user_id = req.user_id
    user_message = req.message

    # بيانات المستخدم المالية الثابتة (الفيتشر الأولى)
    user_profile = {
        "income": 10000,
        "expenses": 7000,
        "subscriptions": 0,
        "debt": 0
    }
    net_savings = user_profile['income'] - (user_profile['expenses'] + user_profile['subscriptions'])

    # 1. تهيئة الذاكرة بنظام الـ Roles (أفضل للتركيز)
    if user_id not in messages_store:
        # رسالة النظام (System Prompt) لضبط الشخصية واللغة والعملة
        messages_store[user_id] = [
            {
                "role": "system",
                "content": f"""أنت "المستشار المالي الاستراتيجي" في السوق المصري.
- اللغة: العربية فقط (ممنوع الصينية والإنجليزية).
- العملة: الجنيه المصري (EGP).
- البيانات المالية الحالية للمستخدم: دخل {user_profile['income']} ج.م، فائض {net_savings} ج.م، ديون {user_profile['debt']} ج.م.
- الشخصية: حازم، عملي، تعتمد على الأرقام والنسب المئوية.
- القاعدة: وجه المستخدم دائماً للادخار والاستثمار وارفض الرفاهية غير الضرورية."""
            }
        ]

    # 2. إضافة رسالة المستخدم الجديدة للمخزن
    messages_store[user_id].append({"role": "user", "content": user_message})

    # 3. الحفاظ على سياق مركز (آخر 6 رسائل فقط + رسالة النظام) لتجنب Error 500
    # رسالة النظام دائماً في البداية [0] ثم آخر 6 رسائل
    if len(messages_store[user_id]) > 7:
        system_msg = messages_store[user_id][0]
        recent_history = messages_store[user_id][-6:]
        messages_store[user_id] = [system_msg] + recent_history

    # 4. طلب الرد من الموديل باستخدام قائمة الرسائل كاملة
    reply = call_llm(messages_store[user_id], CHAT_MODEL)

    # 5. إضافة رد المساعد للمخزن
    messages_store[user_id].append({"role": "assistant", "content": reply})

    return {
        "success": True,
        "reply": reply,
        "context_depth": len(messages_store[user_id]) // 2
    }

if __name__ == "__main__":
    import uvicorn
    print("--- المستشار المالي (نسخة المحادثة المستقرة) تعمل الآن ---")
    uvicorn.run(app, host="0.0.0.0", port=8000)