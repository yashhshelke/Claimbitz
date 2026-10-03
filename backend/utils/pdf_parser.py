from __future__ import annotations

import io

import pdfplumber


def extract_text_from_pdf(file_bytes: bytes) -> str:
    text_chunks: list[str] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                cleaned = extracted.strip()
                if cleaned:
                    text_chunks.append(cleaned)

    return "\n".join(text_chunks).strip()
