import os
import sys
import json
import re
from dotenv import load_dotenv

load_dotenv()
from google import genai
from google.genai import types

api_key = os.getenv('GEMINI_API_KEY')
img_path = r'C:\Users\Paperchase\.gemini\antigravity\brain\4d717899-6fb0-420c-87c5-2d3653bd9a76\.user_uploaded\media_1792401956745_e5eea4dc.png'

if not os.path.exists(img_path):
    print("Image not found:", img_path)
    sys.exit(1)

with open(img_path, 'rb') as f:
    img_bytes = f.read()

client = genai.Client(api_key=api_key)
part = types.Part.from_bytes(data=img_bytes, mime_type='image/png')
prompt = """
You are an executive AI assistant for Dhiraj (Senior AI Engineer).
Look at this Microsoft Teams screenshot and extract ALL tasks/action items specifically assigned to Dhiraj (or Dhiraj / Bhumit Bhai Team, or where Dhiraj is asked to collaborate/act).
Ignore tasks belonging exclusively to other colleagues (e.g., Ayush, Malvi) unless Dhiraj is mentioned.

Return ONLY a JSON list of tasks in this format:
[
  {
    "title": "Actionable Title in English",
    "project": "Project Name",
    "description": "Detailed description of deliverable and scope",
    "priority": "High",
    "source": "teams_screen"
  }
]
"""
resp = client.models.generate_content(
    model='gemini-3.1-flash-lite',
    contents=[prompt, part]
)
clean = re.sub(r'^```(?:json)?\s*', '', resp.text.strip())
clean = re.sub(r'\s*```$', '', clean)
print("Extracted from image:")
print(clean)
