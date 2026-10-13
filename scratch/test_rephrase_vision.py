import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()
from google import genai
from google.genai import types

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

img_path = r"C:\Users\Paperchase\.gemini\antigravity\brain\4d717899-6fb0-420c-87c5-2d3653bd9a76\.user_uploaded\media_1791710711978_ba297741.png"
with open(img_path, "rb") as f:
    img_bytes = f.read()

part = types.Part.from_bytes(data=img_bytes, mime_type="image/png")
prompt = """
You are Mochi's Vision & Rephrasing engine.
The user looked at their screen and said: "rephrase it" or "rephrase this line".
Instructions:
1. Locate the text the user wants rephrased:
   - Priority 1: Look for any text HIGHLIGHTED or SELECTED (e.g. blue selection box at the bottom, or in an editor/chat window).
   - Priority 2: Look for active draft input text in a prompt box, Teams chat, email composer, or document.
2. Extract the exact original text.
3. Rephrase it into clear, articulate, natural, polished English.
4. Return ONLY valid JSON:
{
  "original_text": "extracted text",
  "rephrased": "polished and rephrased text ready to copy-paste",
  "explanation": "Brief 1-sentence explanation of the improvement"
}
"""

models_to_try = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
for m in models_to_try:
    try:
        print(f"Trying model: {m}...")
        cfg = types.GenerateContentConfig(response_mime_type="application/json")
        res = client.models.generate_content(model=m, contents=[prompt, part], config=cfg)
        print(f"Result from {m}:")
        print(res.text)
        break
    except Exception as e:
        print(f"Error with {m}: {e}")
