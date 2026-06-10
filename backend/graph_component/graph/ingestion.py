import os
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from vector_store import store_document_chunks

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=64,
    separators=["\n\n", "\n", ".", " "]
)


def extract_text_from_pdf(file_path: str) -> list[dict]:
    """Extract text from PDF, returns list of {text, page} dicts."""
    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages.append({"text": text.strip(), "page": i + 1})
    return pages


def extract_text_from_txt(file_path: str) -> list[dict]:
    """Extract text from plain text file."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return [{"text": text, "page": 1}]


def ingest_document(file_path: str, source_name: str) -> int:
    """
    Full ingestion pipeline:
    1. Extract text based on file type
    2. Split into chunks
    3. Store in Qdrant private collection
    Returns total chunks stored.
    """
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        pages = extract_text_from_pdf(file_path)
    elif ext in [".txt", ".md"]:
        pages = extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Supported: .pdf, .txt, .md")

    # Split each page into chunks
    all_chunks = []
    for page_data in pages:
        splits = text_splitter.split_text(page_data["text"])
        for split in splits:
            all_chunks.append({
                "text": split,
                "source": source_name,
                "page": page_data["page"]
            })

    if not all_chunks:
        raise ValueError(f"No text extracted from {source_name}")

    return store_document_chunks(all_chunks)