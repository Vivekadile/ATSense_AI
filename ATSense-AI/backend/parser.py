import io

import pymupdf as fitz
from docx import Document

from backend import config

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


async def extract_resume_text(file, *, max_bytes: int | None = None) -> str:
    max_bytes = max_bytes or config.MAX_UPLOAD_BYTES
    filename = (file.filename or "").lower()
    # reject oversized uploads before buffering them in memory
    if file.size is not None and file.size > max_bytes:
        raise ValueError(
            f"File is too large ({file.size // 1024} KB). "
            f"Limit is {max_bytes // 1024} KB."
        )
    content = await file.read()

    if len(content) == 0:
        raise ValueError("Uploaded file is empty.")
    if len(content) > max_bytes:
        raise ValueError(
            f"File is too large ({len(content) // 1024} KB). "
            f"Limit is {max_bytes // 1024} KB."
        )
    if "." not in filename:
        raise ValueError("Resume must have a file extension.")

    extension = "." + filename.rsplit(".", 1)[1]
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file format. Use PDF, DOCX, or TXT.")

    if extension == ".pdf":
        text = extract_pdf(content)
    elif extension == ".docx":
        text = extract_docx(content)
    else:
        text = content.decode("utf-8", errors="ignore")

    if len(text.strip()) < 30:
        raise ValueError(
            "Could not read meaningful text from the resume. "
            "If it's a scanned PDF, upload a text-based version."
        )
    return text


def extract_pdf(content: bytes) -> str:
    text = []
    try:
        with fitz.open(stream=content, filetype="pdf") as pdf:
            for page in pdf:
                text.append(page.get_text())
    except Exception as exc:  # corrupt / password-protected PDF
        raise ValueError(f"Could not open PDF: {exc}")
    return "\n".join(text).strip()


def extract_docx(content: bytes) -> str:
    try:
        document = Document(io.BytesIO(content))
    except Exception as exc:
        raise ValueError(f"Could not open DOCX: {exc}")
    return "\n".join(
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ).strip()
