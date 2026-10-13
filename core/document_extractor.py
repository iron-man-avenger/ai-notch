import os
import io
import re
import json
import base64
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List
import requests
from dotenv import load_dotenv
from core.db import get_setting

load_dotenv()

class BaiduUnlimitedOCR:
    """
    Interface for Baidu Unlimited-OCR (https://github.com/baidu/Unlimited-OCR).
    Handles long-context, multi-page document parsing and table retention.
    Supports local service endpoints and high-accuracy multimodal vision fallbacks.
    """
    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = endpoint_url or os.getenv("UNLIMITED_OCR_URL") or get_setting("unlimited_ocr_url") or "http://127.0.0.1:8000/v1/ocr"

    def extract_from_image(self, image_bytes: bytes, filename: str = "document.png") -> str:
        """Sends image or document page to Unlimited-OCR service or falls back to Gemini Vision OCR."""
        # 1. Check if Unlimited-OCR HTTP server is accessible
        if self.endpoint_url:
            try:
                files = {"file": (filename, image_bytes, "image/png")}
                resp = requests.post(self.endpoint_url, files=files, timeout=4.0)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data.get("text") or data.get("content") or ""
                    if text.strip():
                        print(f"[Unlimited-OCR] Successfully extracted {len(text)} chars from {filename}")
                        return text.strip()
            except Exception:
                pass  # Fall through to Multimodal Vision OCR

        # 2. Multimodal Vision OCR Fallback using Gemini (ultra-high accuracy on text, tables, receipts)
        gemini_key = get_setting("gemini_api_key") or os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=gemini_key)
                mime = "image/png"
                if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
                    mime = "image/jpeg"
                elif filename.lower().endswith(".webp"):
                    mime = "image/webp"

                part = types.Part.from_bytes(data=image_bytes, mime_type=mime)
                prompt = (
                    "You are an expert OCR and document digitization engine. "
                    "Extract all text, headers, lists, numbers, and tables from this document image with 100% precision. "
                    "Preserve reading order, formatting, and table columns. Output only the transcribed content in clean markdown."
                )
                resp = client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=[prompt, part]
                )
                if resp and resp.text:
                    print(f"[Gemini Vision OCR] Extracted {len(resp.text)} chars from {filename}")
                    return resp.text.strip()
            except Exception as e_v:
                print(f"[Vision OCR Warning] {e_v}")

        return f"[OCR text extraction unavailable for image: {filename}]"

class DocumentExtractor:
    """Universal multi-format document parser for RAG ingestion."""
    def __init__(self):
        self.ocr_engine = BaiduUnlimitedOCR()

    def extract(self, filename: str, file_bytes: bytes, file_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Extracts clean text, title, and metadata from an uploaded file.
        Supports: PDF, DOCX, TXT, MD, CSV, JSON, code, and images.
        """
        ext = os.path.splitext(filename)[1].lower()
        title = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()
        doc_ref = re.sub(r"[^a-zA-Z0-9_\-]", "_", filename).lower()[:40]

        extracted_text = ""
        page_count = 1

        # 1. Direct Text / Markdown / Code / JSON / CSV
        if ext in [".txt", ".md", ".json", ".csv", ".tsv", ".py", ".js", ".ts", ".html", ".css", ".xml", ".log", ".yaml", ".yml"]:
            if file_text:
                extracted_text = file_text
            else:
                try:
                    extracted_text = file_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    extracted_text = file_bytes.decode("latin-1", errors="ignore")

        # 2. PDF Documents
        elif ext == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                page_count = len(reader.pages)
                pages_text = []

                for idx, page in enumerate(reader.pages):
                    t = page.extract_text() or ""
                    if t.strip():
                        pages_text.append(f"--- Page {idx + 1} ---\n{t.strip()}")

                extracted_text = "\n\n".join(pages_text)

                # If PDF is scanned (very little or zero text extracted from text stream)
                if len(extracted_text.strip()) < 50 and page_count > 0:
                    print(f"[PDF Extraction] Scanned PDF detected for {filename}. Engaging OCR engine...")
                    # Extract images from PDF pages and run OCR
                    ocr_pages = []
                    for idx, page in enumerate(reader.pages):
                        if hasattr(page, "images") and page.images:
                            for img in page.images:
                                img_bytes = img.data
                                text_ocr = self.ocr_engine.extract_from_image(img_bytes, f"{filename}_page_{idx+1}.png")
                                if text_ocr:
                                    ocr_pages.append(f"--- Page {idx + 1} (OCR) ---\n{text_ocr}")
                                    break
                    if ocr_pages:
                        extracted_text = "\n\n".join(ocr_pages)

            except Exception as e_pdf:
                print(f"[PDF Extractor Error] {e_pdf}")
                if file_text:
                    extracted_text = file_text

        # 3. Microsoft Word (.docx)
        elif ext == ".docx":
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                    xml_content = z.read("word/document.xml")
                    tree = ET.fromstring(xml_content)
                    # Namespace for Word OpenXML
                    namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                    paragraphs = []
                    for p in tree.iterfind('.//w:p', namespaces):
                        texts = [node.text for node in p.iterfind('.//w:t', namespaces) if node.text]
                        if texts:
                            paragraphs.append("".join(texts))
                    extracted_text = "\n\n".join(paragraphs)
            except Exception as e_docx:
                print(f"[DOCX Extractor Error] {e_docx}")
                if file_text:
                    extracted_text = file_text

        # 4. Images (.png, .jpg, .jpeg, .webp, .bmp)
        elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
            extracted_text = self.ocr_engine.extract_from_image(file_bytes, filename)

        # Fallback if text was already read by browser
        if not extracted_text and file_text:
            extracted_text = file_text

        return {
            "doc_ref": doc_ref,
            "title": title or filename,
            "filename": filename,
            "file_type": ext.lstrip("."),
            "page_count": page_count,
            "content": extracted_text.strip(),
            "char_count": len(extracted_text.strip()),
            "word_count": len(extracted_text.strip().split())
        }

document_extractor = DocumentExtractor()
