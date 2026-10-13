# ==============================================================================
# UNLIMITED-OCR & DOCUMENT EXTRACTION ENGINE (unlimited_ocr.py)
# Based on Baidu Unlimited-OCR (https://github.com/baidu/Unlimited-OCR)
# Extracts multi-page PDFs, images, tables, scanned receipts, and docs.
# ==============================================================================

import os
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional
import requests

class BaiduUnlimitedOCR:
    """Client wrapper for Baidu Unlimited-OCR long-context document parsing."""
    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = endpoint_url or os.getenv("UNLIMITED_OCR_URL", "http://127.0.0.1:8000/v1/ocr")

    def parse_document(self, file_bytes: bytes, filename: str = "document.pdf") -> str:
        """Parses multi-page documents using Unlimited-OCR with fallback to Multimodal Vision OCR."""
        # 1. Try Unlimited-OCR endpoint
        if self.endpoint_url:
            try:
                files = {"file": (filename, file_bytes, "application/octet-stream")}
                resp = requests.post(self.endpoint_url, files=files, timeout=6.0)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data.get("text") or data.get("content") or ""
                    if text.strip():
                        return text.strip()
            except Exception:
                pass

        # 2. Multimodal Vision OCR fallback (Gemini or local vision)
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=gemini_key)
                part = types.Part.from_bytes(data=file_bytes, mime_type="image/png" if filename.endswith(('.png', '.jpg')) else "application/pdf")
                prompt = (
                    "Extract all text, headers, numbers, and tabular data from this document. "
                    "Maintain exact reading order and output clean markdown text."
                )
                res = client.models.generate_content(model="gemini-flash-latest", contents=[prompt, part])
                if res and res.text:
                    return res.text.strip()
            except Exception:
                pass

        return ""

def extract_file_content(filename: str, file_bytes: bytes) -> str:
    """Extracts text from PDF, DOCX, TXT, MD, CSV, JSON, and Images."""
    ext = os.path.splitext(filename)[1].lower()
    
    # Text / Code
    if ext in [".txt", ".md", ".json", ".csv", ".py", ".js", ".ts", ".html", ".xml", ".log"]:
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1", errors="ignore")

    # Word .docx
    if ext == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                xml = z.read("word/document.xml")
                tree = ET.fromstring(xml)
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                paragraphs = []
                for p in tree.iterfind('.//w:p', ns):
                    texts = [n.text for n in p.iterfind('.//w:t', ns) if n.text]
                    if texts:
                        paragraphs.append("".join(texts))
                return "\n\n".join(paragraphs)
        except Exception:
            pass

    # PDF via pypdf with Unlimited-OCR fallback
    if ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages = [p.extract_text() or "" for p in reader.pages]
            text = "\n\n".join(pages).strip()
            if len(text) > 40:
                return text
        except Exception:
            pass

    # Run Baidu Unlimited-OCR on scanned PDFs or Images
    ocr = BaiduUnlimitedOCR()
    return ocr.parse_document(file_bytes, filename)
