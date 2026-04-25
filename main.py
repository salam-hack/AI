from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from datetime import datetime

app = FastAPI()

OLLAMA_URL = "http://localhost:11434/api/generate"

# =====================================================
# MODELS CONFIGURATION
# =====================================================
CHAT_MODEL = "qwen2.5"

# تخزين الرسائل
messages_store = {}

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
                "options": {
                    "temperature": 0.2,  # تقليل الحرارة يمنع الهلوسة واللغات الغريبة
                    "top_p": 0.9
                }
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return "عذراً، حصلت مشكلة فنية بسيطة.. ممكن تسأل تاني؟"

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

    # جلب التاريخ وتحويله لنص
    history = messages_store[user_id][-6:]
    history_text = "".join([f"{m['role']}: {m['text']}\n" for m in history])

    # البرومبت النهائي: حازم، متخصص، وبالعربي فقط
    prompt = f"""
    [تعليمات النظام - حظر لغوي صارم]:
    أنت "المستشار المالي الاستراتيجي"، خبير رفيع المستوى في السوق المصري والإدارة المالية الشخصية.
    - الرد يجب أن يكون باللغة العربية فقط (اللغة البيضاء أو الفصحى البسيطة).
    - مسموح فقط باستخدام الحروف العربية والأرقام.
    - يُمنع منعاً باتاً (STRICTLY FORBIDDEN) استخدام أي حروف صينية أو إنجليزية. إذا خالفت ذلك، سيعتبر الرد فشلاً تقنياً.

    [هوية المستشار]:
    شخصيتك هي "الخبير الحازم". أنت لا تجامل المستخدم على حساب مصلحته المالية. هدفك هو تعظيم ثروته وحمايته من التضخم ومن الاندفاع الاستهلاكي.

    [البيانات المالية الأساسية]:
    - الدخل الشهري: {user_profile['income']} جنيه مصري.
    - الفائض المتاح حالياً: {net_savings} جنيه مصري.
    - الديون/الالتزامات: {user_profile['debt']} جنيه مصري.

    [قواعد تحليل المحتوى]:
    1. التخصص المالي: أجب فقط على الأسئلة المتعلقة بالمال، الميزانية، الاستثمار، والديون. اعتذر بذكاء عن أي موضوع آخر.
    2. التحليل الرقمي: لا تتحدث بالإنشاء. استخدم لغة الأرقام والنسب المئوية (مثلاً: "هذا المصروف يمثل 10% من دخلك").
    3. ترتيب الأولويات المالي: 
       - أولاً: سداد الديون (خاصة عالية الفائدة).
       - ثانياً: بناء صندوق طوارئ (يغطي مصاريف 3-6 شهور).
       - ثالثاً: الاستثمار (ذهب، بورصة، صناديق استثمار، شهادات، عقار) حسب المبلغ المتاح.
       - رابعاً: الرفاهية والكماليات (تُرفض تماماً إذا كان هناك ديون أو الفائض ضئيل).
    4. الوعي بالسوق المصري: كن واعياً أن القوة الشرائية للجنيه تتأثر بالتضخم، لذا شجع دائماً على تحويل الفائض لأصول بدلاً من الكاش السائل.

    [هيكلة الرد]:
    يجب أن يتبع ردك هذا الترتيب:
    - **تحليل الوضع**: (تقييم مالي سريع بالأرقام لرسالة المستخدم).
    - **التوصية الاستراتيجية**: (القرار الذي يجب على المستخدم اتخاذه فوراً).
    - **خطة العمل**: (خطوات 1، 2، 3 ينفذها المستخدم الآن).

    [تاريخ المحادثة]:
    {history_text}

    [رسالة المستخدم الحالية]:
    {message}

    [رد المستشار المالي (باللغة العربية فقط)]:
    """

    reply = call_llm(prompt, CHAT_MODEL)

    # تخزين الرسائل (user and assistant)
    messages_store[user_id].append({"role": "user", "text": message})
    messages_store[user_id].append({"role": "assistant", "text": reply})

    return {"success": True, "reply": reply}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)