from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import json
import os
from dotenv import load_dotenv
app = FastAPI()

# =====================================================
# CONFIG
# =====================================================
load_dotenv()

OLLAMA_GENERATE_URL = os.getenv("OLLAMA_GENERATE_URL")
OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL")

SHARED_MODEL = os.getenv("SHARED_MODEL")

BASE_BACKEND_URL = os.getenv("BASE_BACKEND_URL")

USER_PROFILE_API = f"{BASE_BACKEND_URL}/internal/ai-tools/user-profile"
CONVERSATION_TURNS_API = f"{BASE_BACKEND_URL}/internal/ai-tools/conversation-turns"
CHAT_SUMMARY_API = f"{BASE_BACKEND_URL}/internal/ai-tools/conversation-summary"
CURRENT_DATE_API = f"{BASE_BACKEND_URL}/internal/ai-tools/current-date"

# =====================================================
# REQUEST MODELS
# =====================================================

class Transaction(BaseModel):
    text: str


class ChatRequest(BaseModel):
    user_id: str
    conversation_id: str
    message: str


# =====================================================
# BACKEND FUNCTIONS
# =====================================================

def get_user_profile(user_id):

    res = requests.get(
        f"{USER_PROFILE_API}/{user_id}",
        timeout=5
    )

    if res.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch user profile"
        )

    return res.json()


def get_recent_turns(conversation_id, user_id, limit=3):

    try:

        res = requests.get(
            f"{CONVERSATION_TURNS_API}/{conversation_id}",
            params={
                "userId": user_id,
                "limit": limit
            },
            timeout=5
        )

        if res.status_code != 200:
            return []

        data = res.json()

        turns = data.get("turns", [])

        messages = []

        for turn in turns:

            user_msg = turn.get("user")
            assistant_msg = turn.get("assistant")

            if user_msg:
                messages.append({
                    "role": "user",
                    "content": user_msg
                })

            if assistant_msg:
                messages.append({
                    "role": "assistant",
                    "content": assistant_msg
                })

        return messages

    except Exception as e:
        print(f"Error fetching turns: {e}")
        return []


def get_chat_summary(conversation_id, user_id):

    try:

        res = requests.get(
            f"{CHAT_SUMMARY_API}/{conversation_id}",
            params={
                "userId": user_id
            },
            timeout=5
        )

        if res.status_code != 200:
            return ""

        data = res.json()

        return data.get("summary", "")

    except Exception as e:
        print(f"Error fetching summary: {e}")
        return ""


def update_chat_summary(conversation_id, user_id, summary):

    try:

        requests.patch(
            f"{CHAT_SUMMARY_API}/{conversation_id}",
            params={
                "userId": user_id
            },
            json={
                "summary": summary
            },
            timeout=5
        )

    except Exception as e:
        print(f"Error updating summary: {e}")


def get_current_date():

    try:

        res = requests.get(
            CURRENT_DATE_API,
            timeout=5
        )

        if res.status_code != 200:
            return "Unknown Date"

        return res.text.strip()

    except Exception as e:
        print(f"Error fetching current date: {e}")
        return "Unknown Date"


# =====================================================
# SUMMARY PATCHING
# =====================================================

def patch_chat_summary(
    old_summary,
    user_message,
    ai_reply
):

    prompt = f"""
You are an arabic conversation memory manager.

Your task:
Update the old conversation summary using:
1. Previous arabic summary
2. New user arabic message
3. Assistant arabic response

Rules:
- Keep only important long-term financial context
- Keep goals, habits, preferences, risks
- Remove temporary details
- Remove repetition
- Keep summary compact
- Maximum 120 words
- Return plain text only
-only replay with arabic language
-never reply with any language but arabic language

OLD SUMMARY:
{old_summary}

NEW USER MESSAGE:
{user_message}

ASSISTANT RESPONSE:
{ai_reply}

UPDATED SUMMARY:
"""

    try:

        response = requests.post(
            OLLAMA_GENERATE_URL,
            json={
                "model": SHARED_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0
                }
            },
            timeout=60
        )

        return response.json()["response"].strip()

    except Exception as e:
        print(f"Summary patching error: {e}")
        return old_summary


# =====================================================
# TRANSACTION PARSER
# =====================================================

def call_parser_model(text: str):

    current_date = get_current_date()

    prompt = f"""
Task: Strict Financial Transaction Parser.

Return ONLY valid JSON.

IMPORTANT:
- Today is "{current_date}"
- Input may be Arabic or English

Output format:
{{
  "amount": number,
  "Product": string,
  "merchant": string,
  "category": string,
  "date": string
}}

Rules:
- Extract only the purchased product
- Ignore quantities
- No explanation
- Return valid JSON only
-Food items and groceries must always be categorized as "Food & Drinks"

Allowed categories:
- Food & Drinks
- Transportation
- Bills & Subscriptions
- Shopping
- Entertainment
- Healthcare
- Education
- Gifts & Donations
- Other

Text:
"{text}"
"""

    try:

        response = requests.post(
            OLLAMA_GENERATE_URL,
            json={
                "model": SHARED_MODEL,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": 0.0
                }
            },
            timeout=60
        )

        return json.loads(response.json()["response"])

    except Exception as e:

        print(f"Parser error: {e}")

        return {
            "amount": None,
            "Product": "Unknown",
            "merchant": "Unknown",
            "category": "Other",
            "date": current_date
        }


@app.post("/parse")
def parse(tx: Transaction):

    parsed = call_parser_model(tx.text)

    return {
        "success": True,
        "data": parsed
    }


# =====================================================
# FINANCIAL ADVISOR CHAT
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
                    "num_ctx": 4096,
                    "num_predict": 500
                }
            },
            timeout=120
        )

        response.raise_for_status()

        return response.json()["message"]["content"]

    except Exception as e:

        print(f"Advisor model error: {e}")

        return "حصلت مشكلة تقنية، حاول مرة تانية."


@app.post("/chat")
def chat(req: ChatRequest):

    # =========================================
    # FETCH CONTEXT
    # =========================================

    user_profile = get_user_profile(req.user_id)

    recent_messages = get_recent_turns(
        req.conversation_id,
        req.user_id,
        limit=3
    )

    summary = get_chat_summary(
        req.conversation_id,
        req.user_id
    )

    current_date = get_current_date()

    # =========================================
    # EXTRACT IMPORTANT DATA
    # =========================================

    financial_profile = user_profile.get("financial_profile", {})

    income = financial_profile.get("income", 0)

    expenses = financial_profile.get("expenses", 0)

    savings = financial_profile.get("savings", 0)

    savings_rate = financial_profile.get("savings_rate", 0)

    behavior = user_profile.get("behavior_summary", {})

    goals = user_profile.get("goals", {})

    active_goals = goals.get("active", [])

    # =========================================
    # SYSTEM PROMPT
    # =========================================

    system_prompt = f"""
أنت "رشيد" مساعد مالي ذكي داخل تطبيق "مدبر".
تطبيق مدبر هو تطبيق لمتابعة النفقات المالية وتسجيل أهداف الادخار.

شخصيتك:
- ودود وعملي
- تشرح ببساطة
- إجاباتك مختصرة ومباشرة
-تتحدث اللغة العربية فقط

قواعد مهمة:
- تتحدث فقط عن المال والإدارة المالية
- ممنوع أي مواضيع خارج المال ولو تحدث المستخدم عن شيىء اخر اعتذر له بطريقة مهذبة
- ممنوع اقتراح قروض ربوية أو فوائد محرمة
- لا تخترع معلومات غير موجودة
- الرد يكون باللغة العربية فقط
- ممنوع ترد بأي لغة غير العربية

التاريخ الحالي:
{current_date}

الوضع المالي:
- الدخل: {income}
- المصروفات: {expenses}
- الادخار: {savings}
- نسبة الادخار: {savings_rate}%

السلوك المالي:
- ملتزم ماليًا: {behavior.get("is_disciplined")}
- يصرف أكثر من اللازم: {behavior.get("is_overspending")}
- مهتم بالأهداف: {behavior.get("is_goal_oriented")}

الأهداف النشطة:
{json.dumps(active_goals, ensure_ascii=False)}

ملخص المحادثة:
{summary}
"""

    # =========================================
    # BUILD FINAL MESSAGES
    # =========================================

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    messages.extend(recent_messages)

    messages.append({
        "role": "user",
        "content": req.message
    })

    # =========================================
    # GENERATE AI RESPONSE
    # =========================================

    reply = call_advisor_llm(messages)

    # =========================================
    # UPDATE SUMMARY MEMORY
    # =========================================

    updated_summary = patch_chat_summary(
        old_summary=summary,
        user_message=req.message,
        ai_reply=reply
    )

    # =========================================
    # SAVE UPDATED SUMMARY
    # =========================================

    update_chat_summary(
        conversation_id=req.conversation_id,
        user_id=req.user_id,
        summary=updated_summary
    )

    return {
        "success": True,
        "reply": reply,
        "memory_updated": True,
        "conversation_id": req.conversation_id
    }


# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    import uvicorn

    print(f"Running AI Service using model: {SHARED_MODEL}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )