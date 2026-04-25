from fastapi import FastAPI
from pydantic import BaseModel
import requests
import json
from datetime import datetime

app = FastAPI()

class Transaction(BaseModel):
    text: str

def call_model(text: str):
    prompt = f"""
You are a strict financial transaction parser.

Return ONLY valid JSON.
IMPORTANT:
- Today's date is 2026-04-25
- You must calculate relative dates based ONLY on today's date
- "yesterday" = 2026-04-24
- Never guess random or old dates
Rules:
- No explanations
- No comments
- No markdown
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

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }
    )

    raw = response.json()["response"]

    try:
        return json.loads(raw)
    except:
        return {
            "amount": None,
            "merchant": "Unknown",
            "category": "Other",
            "date": datetime.today().strftime("%Y-%m-%d")
        }

@app.post("/parse")
def parse(tx: Transaction):
    return {
        "success": True,
        "data": call_model(tx.text)
    }