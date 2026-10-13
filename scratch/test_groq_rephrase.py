import os
import requests
from dotenv import load_dotenv

load_dotenv()

groq_key = os.getenv("GROQ_API_KEY")
draft = "and why need to show all thes things in the island that look messy isalnd,"

headers = {
    "Authorization": f"Bearer {groq_key}",
    "Content-Type": "application/json"
}

prompt = f"""
You are an executive communication assistant.
Rephrase this user draft into clear, articulate, natural, polished English:
"{draft}"

Return ONLY a JSON object:
{{
  "original": "{draft}",
  "reply": "Polished rephrased text ready to copy-paste",
  "explanation": "Brief 1-sentence explanation"
}}
"""

payload = {
    "model": "qwen/qwen3.8-27b",
    "messages": [{"role": "user", "content": prompt}],
    "response_format": {"type": "json_object"}
}

resp = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=5)
print("STATUS:", resp.status_code)
print("GROQ RESULT:", resp.json()["choices"][0]["message"]["content"])
