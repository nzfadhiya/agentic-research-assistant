import os
import sys
sys.path.insert(0, '.')

def read_pdf(file_bytes: bytes) -> str:
    """
    Extracts text from a PDF file.
    Returns full text content as string.
    """
    import fitz  # pymupdf
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    print(f"[doc_reader] Extracted {len(text)} chars from PDF")
    return text


def read_docx(file_bytes: bytes) -> str:
    """
    Extracts text from a DOCX file.
    Returns full text content as string.
    """
    import io
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    print(f"[doc_reader] Extracted {len(text)} chars from DOCX")
    return text


def read_txt(file_bytes: bytes) -> str:
    """Reads plain text file."""
    return file_bytes.decode("utf-8", errors="ignore")


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Auto-detects file type and extracts text.
    Supports PDF, DOCX, TXT.
    """
    filename_lower = filename.lower()
    if filename_lower.endswith(".pdf"):
        return read_pdf(file_bytes)
    elif filename_lower.endswith(".docx"):
        return read_docx(file_bytes)
    elif filename_lower.endswith(".txt"):
        return read_txt(file_bytes)
    else:
        return "Unsupported file format. Please upload PDF, DOCX, or TXT."