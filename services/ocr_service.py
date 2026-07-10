"""
OCR Service — Mistral Pixtral VLM-powered PDF text extraction
=============================================================
Strategy (smart fallback):
  1. Try PyPDF text extraction (fast, free, works for text-native PDFs)
  2. If quality is poor (scanned CV, complex layout, image-heavy), fall back
     to Mistral Pixtral (pixtral-12b-2409) which renders each page as an
     image and extracts structured text via VLM.

Usage:
    from services.ocr_service import ocr_service
    text = ocr_service.extract_text(pdf_bytes)
"""

import os
import io
import base64
import logging
import requests
from typing import Optional, List

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Quality heuristics
# ─────────────────────────────────────────────

MIN_CHARS = 300          # below this → almost certainly a scanned PDF
MIN_READABLE_RATIO = 0.6  # ratio of alphanumeric+space chars required


def _text_quality(text: str) -> float:
    """Return a quality score between 0 and 1 for extracted text."""
    if not text or len(text.strip()) < 10:
        return 0.0
    readable = sum(c.isalnum() or c.isspace() or c in ".,;:!?-()@" for c in text)
    return readable / len(text)


def _is_good_quality(text: str) -> bool:
    """Return True if PyPDF extraction is usable and complete."""
    stripped = text.strip() if text else ""
    if len(stripped) < MIN_CHARS:
        return False
    return _text_quality(text) >= MIN_READABLE_RATIO


# ─────────────────────────────────────────────
# OCR Service
# ─────────────────────────────────────────────

class OCRService:
    """
    Smart PDF text extractor.
    - Uses PyPDF for clean, text-native PDFs (fast, no API cost).
    - Falls back to Mistral Pixtral VLM for scanned or complex-layout CVs.
    """

    def __init__(self):
        self.api_key = os.getenv("MISTRAL_API_KEY")
        # Allow overriding the VLM model; pixtral-12b-2409 is the cost-effective choice
        self.ocr_model = os.getenv("MISTRAL_OCR_MODEL", "pixtral-12b-2409")
        self.api_url = "https://api.mistral.ai/v1/chat/completions"
        self.max_pages = int(os.getenv("OCR_MAX_PAGES", "6"))

    # ── Public API ─────────────────────────────

    def extract_text(self, pdf_bytes: bytes) -> str:
        """
        Main entry point.
        Returns the best possible text from the PDF.
        """
        # Step 1 — Try PyPDF (free, instant)
        pypdf_text = self._extract_with_pypdf(pdf_bytes)

        if _is_good_quality(pypdf_text):
            logger.info("[OCR] ✅ PyPDF extraction OK (%d chars) — skipping VLM", len(pypdf_text))
            return pypdf_text.strip()

        logger.info(
            "[OCR] ⚠️  PyPDF quality poor (%d chars, score=%.2f) — activating Pixtral VLM",
            len(pypdf_text or ""),
            _text_quality(pypdf_text or ""),
        )

        # Step 2 — Render pages to images → Pixtral
        if not self.api_key:
            logger.warning("[OCR] No MISTRAL_API_KEY — cannot use VLM, returning PyPDF text as-is")
            return (pypdf_text or "").strip()

        vlm_text = self._extract_with_pixtral(pdf_bytes)

        if vlm_text and len(vlm_text.strip()) > len((pypdf_text or "").strip()):
            logger.info("[OCR] ✅ Pixtral VLM extraction: %d chars", len(vlm_text))
            return vlm_text.strip()

        # Last resort: return whatever PyPDF gave us
        return (pypdf_text or "").strip()

    # ── Step 1: PyPDF ──────────────────────────

    def _extract_with_pypdf(self, pdf_bytes: bytes) -> str:
        """Extract text using pypdf (text-native PDFs only)."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            pages_text = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    pages_text.append(t)
            return "\n".join(pages_text)
        except ImportError:
            pass

        # Fallback to PyPDF2
        try:
            from PyPDF2 import PdfReader as PdfReader2
            reader = PdfReader2(io.BytesIO(pdf_bytes))
            pages_text = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    pages_text.append(t)
            return "\n".join(pages_text)
        except Exception as e:
            logger.warning("[OCR] PyPDF failed: %s", e)
            return ""

    # ── Step 2: Pixtral VLM ────────────────────

    def _extract_with_pixtral(self, pdf_bytes: bytes) -> str:
        """Render PDF pages to images and run Pixtral OCR on each."""
        images_b64 = self._pdf_to_images_b64(pdf_bytes)

        if not images_b64:
            logger.error("[OCR] Could not render PDF to images")
            return ""

        logger.info("[OCR] Sending %d page(s) to Pixtral (%s)…", len(images_b64), self.ocr_model)

        all_text: List[str] = []
        for idx, img_b64 in enumerate(images_b64):
            page_text = self._call_pixtral_page(img_b64, page_num=idx + 1)
            if page_text:
                all_text.append(page_text)

        return "\n\n".join(all_text)

    def _pdf_to_images_b64(self, pdf_bytes: bytes) -> List[str]:
        """
        Render PDF pages to PNG images (base64-encoded).
        Uses PyMuPDF (fitz) — no system dependencies, works on Windows.
        """
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            images: List[str] = []
            n_pages = min(len(doc), self.max_pages)

            for i in range(n_pages):
                page = doc[i]
                # 2× zoom → ~150 dpi render → good balance quality/size
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_bytes = pix.tobytes("png")
                images.append(base64.b64encode(img_bytes).decode("utf-8"))

            doc.close()
            logger.info("[OCR] Rendered %d page(s) via PyMuPDF", len(images))
            return images

        except ImportError:
            logger.error(
                "[OCR] PyMuPDF not installed. Run: pip install PyMuPDF\n"
                "      Cannot render PDF pages for VLM OCR."
            )
            return []
        except Exception as e:
            logger.error("[OCR] PDF rendering failed: %s", e)
            return []

    def _call_pixtral_page(self, img_b64: str, page_num: int = 1) -> Optional[str]:
        """Send a single page image to Pixtral and return extracted text."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        system_prompt = (
            "You are an expert OCR engine specialized in CV/resume parsing. "
            "Your task is to extract ALL text from the provided CV page image. "
            "Rules:\n"
            "- Preserve the logical structure: name, contact info, sections (Experience, Education, Skills, etc.)\n"
            "- Keep bullet points and date ranges\n"
            "- Handle multi-column layouts by reading left-to-right, top-to-bottom\n"
            "- Output ONLY the extracted text — no commentary, no markdown fences\n"
            "- If a section has a table (e.g. skill levels), extract as plain text rows"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_b64}"
                        },
                    },
                    {
                        "type": "text",
                        "text": f"Extract all text from CV page {page_num}.",
                    },
                ],
            },
        ]

        payload = {
            "model": self.ocr_model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.0,  # deterministic — we want exact extraction
        }

        try:
            resp = requests.post(self.api_url, headers=headers, json=payload, timeout=90)
            resp.raise_for_status()
            result = resp.json()
            text = result["choices"][0]["message"]["content"]
            logger.info("[OCR] Page %d → %d chars", page_num, len(text))
            return text
        except requests.exceptions.Timeout:
            logger.error("[OCR] Pixtral timeout on page %d", page_num)
        except requests.exceptions.HTTPError as e:
            logger.error("[OCR] Pixtral HTTP %s on page %d: %s", e.response.status_code, page_num, e)
        except Exception as e:
            logger.error("[OCR] Pixtral error on page %d: %s", page_num, e)
        return None


# ── Singleton ────────────────────────────────────

ocr_service = OCRService()
