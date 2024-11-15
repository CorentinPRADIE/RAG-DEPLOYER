# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import basic_routes, ask_route
from app.documentary_researcher import initialize_embeddings, load_faiss_index, process_and_index_documents
from app.utils.logger import logger, log_task
import os

# Set up the environment
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import logging
logging.getLogger("tensorflow").setLevel(logging.ERROR)

app = FastAPI(title="My RAG App", description="A FastAPI template app for RAG back-end")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize embeddings and FAISS index
embeddings = None
faiss_index = None

@app.on_event("startup")
async def startup_event():
    global embeddings, faiss_index

    with log_task("Initializing embeddings"):
        embeddings = initialize_embeddings()

    try:
        with log_task("Loading FAISS index"):
            faiss_index = load_faiss_index(embeddings)
    except FileNotFoundError:
        logger.warning("FAISS index not found. Attempting to create a new index.")
        UPLOAD_FOLDER = 'uploads'
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        documents_to_index = [
            os.path.join(UPLOAD_FOLDER, file)
            for file in os.listdir(UPLOAD_FOLDER)
            if file.endswith('.pdf')
        ]

        if documents_to_index:
            try:
                with log_task("Creating FAISS index from documents"):
                    num_documents, num_segments = process_and_index_documents(
                        documents_to_index, embeddings, faiss_index=None
                    )
                with log_task("Reloading FAISS index"):
                    faiss_index = load_faiss_index(embeddings)
            except Exception as e:
                logger.error(f"Failed to create FAISS index: {e}")
        else:
            logger.warning("No documents found to create FAISS index. Please upload documents.")
    
    # Set the initialized embeddings and faiss_index for the routes
    basic_routes.embeddings = embeddings
    basic_routes.faiss_index = faiss_index
    ask_route.embeddings = embeddings
    ask_route.faiss_index = faiss_index

# Include the routers
app.include_router(basic_routes.router)
app.include_router(ask_route.router)

@app.get("/")
async def read_root():
    return {"message": "Welcome to the FastAPI RAG App"}
