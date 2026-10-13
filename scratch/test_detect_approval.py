import os
import json
import re
from dotenv import load_dotenv

load_dotenv()
from google import genai
from google.genai import types

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

img_path = r"C:\Users\Paperchase\.gemini\antigravity\brain\4d717899-6fb0-420c-87c5-2d3653bd9a76\.user_uploaded\media_1791710923346_098f09b7.png"
with open(img_path, "rb") as f:
    img_bytes = f.read()

part = types.Part.from_bytes(data=img_bytes, mime_type="image/png")
prompt = """
You are Mochi's On-Screen Approval & Safety Inspector.
Look at this screen capture:
1. Is there an active approval dialog, confirmation prompt, or permission modal visible on the screen? (e.g. "Allow running ...", "Confirm", "Do you want to run", "Yes/No", "[Submit (Enter)]")
2. What action or command is requesting approval?
3. Is it safe to auto-approve? (e.g. safe dev tests, builds, Python scripts vs destructive commands like format disk/rm -rf)
4. What is the recommended approval method? (e.g. "press_enter" or click "Submit" button)
5. Locate the exact normalized coordinates of the "Submit" or "Yes" button (box_2d: [ymin, xmin, ymax, xmax] on scale 0 to 1000).

Return ONLY a JSON object:
{
  "has_approval_dialog": true,
  "dialog_title": "Allow running rephrase vision test?",
  "command": "python scratch/test_rephrase_vision.py",
  "is_safe": true,
  "safety_reason": "Harmless local Python test script for vision testing",
  "approval_method": "press_enter",
  "button_box_2d": [ymin, xmin, ymax, xmax]
}
"""

cfg = types.GenerateContentConfig(response_mime_type="application/json")
for m in ["gemini-3.1-flash-lite", "gemini-3.8-flash"]:
    try:
        print(f"Testing model: {m}...")
        res = client.models.generate_content(model=m, contents=[prompt, part], config=cfg)
        print("RESULT:")
        print(res.text)
        break
    except Exception as e:
        print(f"Error {m}: {e}")
