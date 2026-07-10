# File Upload API Route
# POST /api/upload/pdf — Extract text from a PDF file
# Uses OCRService for smart fallback (PyPDF -> Pixtral VLM)
#

import io
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from backend.api.deps import get_current_user
from models.user import User
from services.ocr_service import ocr_service
from services.anonymizer_service import anonymizer_service

router = APIRouter(prefix="/api/upload", tags=["Upload"])


@router.post("/pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    _current_user: User = Depends(get_current_user),
):
    """Upload a PDF and extract text content using smart OCR / PyPDF."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        contents = await file.read()
        
        # Calculate page count for response
        pages = 0
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(contents))
            pages = len(reader.pages)
        except Exception:
            try:
                import fitz
                doc = fitz.open(stream=contents, filetype="pdf")
                pages = len(doc)
                doc.close()
            except Exception:
                pass

        # Extract text via OCR service
        text = ocr_service.extract_text(contents)

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from PDF. The file may be empty or corrupted."
            )

        # Anonymize PII before returning to client
        # The frontend will send this anonymized text to AI agents.
        # Real values are stored encrypted in the PII vault (SQLite).
        user_id = str(_current_user.id)
        anonymized_text = anonymizer_service.anonymize(text.strip(), user_id)

        return {"text": anonymized_text, "pages": pages}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading PDF: {str(e)}")

