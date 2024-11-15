# app/documentary_researcher.py
import os
import warnings
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.utils.logger import logger, log_task
import time

warnings.filterwarnings("ignore", category=UserWarning)

def initialize_embeddings():
    """Initialize and return embeddings model."""
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return embeddings

def load_faiss_index(embeddings):
    """Load FAISS index, raise FileNotFoundError if it does not exist."""
    if not os.path.exists("faiss_index"):
        logger.error("FAISS index not found. Please upload documents to create the index.")
        raise FileNotFoundError("FAISS index not found.")
    index = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    return index

def process_and_index_documents(file_paths, embeddings, faiss_index=None):
    """Load, split, and index documents. Save index locally."""
    documents = []
    for file_path in file_paths:
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        documents.extend(docs)
        logger.info(f"Loaded document: {os.path.basename(file_path)}")

    num_documents = len(documents)

    with log_task("Splitting and indexing documents"):
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        split_docs = text_splitter.split_documents(documents)
        num_segments = len(split_docs)

        if faiss_index is None:
            faiss_index = FAISS.from_documents(split_docs, embeddings)
        else:
            faiss_index.add_documents(split_docs)

        faiss_index.save_local("faiss_index")
        logger.info("FAISS index updated and saved successfully.")

    return num_documents, num_segments


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