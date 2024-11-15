# app/documentary_researcher.py

"""
This file handles the indexing and retrieval processes for the RAG system.

1. Indexing Process and Cleaning:
   - Extracts text and tables from PDFs using `pdfplumber`.
   - Cleans the extracted text by normalizing spaces, removing headers/footers, and ensuring consistency.
   - Tags and labels document sections (e.g., headings, body text, tables) to enhance granularity.
   - Implements semantic splitting to split text into coherent chunks, ensuring logical boundaries like sentences or paragraphs using `spaCy`.
   - Saves the indexed data into a FAISS vector store for efficient retrieval.

2. Retrieval Process:
   - Uses FAISS to retrieve the most relevant context for a given query.
   - Returns top-k results with associated metadata, such as source and page number.
   - Prioritizes accuracy through dense embeddings and structured indexing.
"""

import os
import warnings
import time
import pdfplumber
import spacy
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from app.utils.logger import logger, log_task

warnings.filterwarnings("ignore", category=UserWarning)

# Load the French language model for spaCy
nlp = spacy.load("fr_core_news_sm")


def initialize_embeddings():
    """Initialize and return embeddings model."""
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return embeddings


def load_faiss_index(embeddings):
    """Load FAISS index, raise FileNotFoundError if it does not exist."""
    if not os.path.exists("faiss_index"):
        logger.warning("FAISS index not found.")
        raise FileNotFoundError("FAISS index not found.")
    index = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    if not validate_faiss_index(index):  # Validate structure and health
        logger.error("FAISS index validation failed.")
        raise ValueError("FAISS index is corrupted or inconsistent.")
    return index


def clean_text(text):
    """Clean extracted text by normalizing spaces, removing headers/footers, and fixing line breaks."""
    text = " ".join(text.split())  # Normalize spaces
    text = text.replace("\n\n", "\n").replace("\n", " ").strip()  # Normalize line breaks
    return text


def tag_sections(content, page_number, file_path):
    """Tag and label content for better granularity during indexing."""
    return f"[Page {page_number} - Source: {os.path.basename(file_path)}]\n{content}"


def validate_faiss_index(index):
    """Validate FAISS index structure and ensure consistency."""
    try:
        assert index.index.ntotal > 0  # Use ntotal to check the number of items in the index
        return True
    except Exception as e:
        logger.error(f"FAISS index validation error: {e}")
        return False


def extract_text_from_pdf(file_path):
    """Extract text and tables from a PDF file using pdfplumber."""
    documents = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            tables = page.extract_tables()
            clean_text_content = clean_text(text)
            tagged_content = tag_sections(clean_text_content, page_number=i + 1, file_path=file_path)
            
            # Append text content as a Document object
            documents.append(Document(
                page_content=tagged_content,
                metadata={"source": file_path, "page": i + 1}
            ))

            # Append tables as markdown-style text as a Document object
            for table in tables:
                table_md = "\n".join([" | ".join(map(str, row)) for row in table])
                documents.append(Document(
                    page_content=table_md,
                    metadata={"source": file_path, "page": i + 1, "type": "table"}
                ))
    return documents


def semantic_split(text, chunk_size=500):
    """Split text into semantically meaningful chunks using spaCy."""
    doc = nlp(text)
    sentences = [sent.text for sent in doc.sents]  # Tokenize sentences
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # Check if adding the next sentence exceeds the chunk size
        if len(current_chunk) + len(sentence) > chunk_size:
            chunks.append(current_chunk.strip())
            current_chunk = sentence  # Start a new chunk
        else:
            current_chunk += " " + sentence

    if current_chunk:  # Add any remaining text as the last chunk
        chunks.append(current_chunk.strip())

    return chunks


def process_and_index_documents(file_paths, embeddings, faiss_index=None):
    """Load, clean, semantically split, and index documents. Save index locally."""
    documents = []
    for file_path in file_paths:
        docs = extract_text_from_pdf(file_path)
        documents.extend(docs)
        logger.info(f"Loaded document: {os.path.basename(file_path)}")

    num_documents = len(documents)

    with log_task("Splitting and indexing documents"):
        split_docs = []
        for doc in documents:
            chunks = semantic_split(doc.page_content)  # Use semantic splitting
            for chunk in chunks:
                split_docs.append(Document(page_content=chunk, metadata=doc.metadata))

        # Index documents with FAISS
        if faiss_index is None:
            faiss_index = FAISS.from_documents(split_docs, embeddings)
        else:
            faiss_index.add_documents(split_docs)

        faiss_index.save_local("faiss_index")
        logger.info("FAISS index updated and saved successfully.")

    logger.debug(f"Processed {num_documents} documents into {len(split_docs)} segments.")
    return num_documents, len(split_docs)


def retrieve_dense_results(question, faiss_index):
    """Retrieve top dense results from FAISS index and format them as dictionaries with metadata."""
    start_time = time.time()
    dense_results_raw = faiss_index.as_retriever(k=10).invoke(question)
    retrieval_duration = time.time() - start_time

    dense_results = [
        {
            "page_content": result.page_content,
            "metadata": {
                "source": result.metadata.get("source", "Unknown"),
                "page": result.metadata.get("page", "N/A")
            },
            "source_type": "Dense"
        }
        for result in dense_results_raw
    ]
    return dense_results, retrieval_duration


def retrieve_context(question, faiss_index):
    """Retrieve context from dense retriever only."""
    dense_results, dense_duration = retrieve_dense_results(question, faiss_index)
    return dense_results, dense_duration
