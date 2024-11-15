# app/routes/basic_routes.py
import os
from fastapi import APIRouter, HTTPException, UploadFile
from app.documentary_researcher import process_and_index_documents
from app.utils.logger import logger

# Initialize router
router = APIRouter()

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Declare embeddings and faiss_index as global variables
embeddings = None
faiss_index = None

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@router.get("/status")
async def status():
    return {
        "embeddings_loaded": embeddings is not None,
        "index_loaded": faiss_index is not None
    }

@router.post("/upload")
async def upload(files: list[UploadFile]):
    uploaded_files = []

    # Save and process each file
    for file in files:
        if allowed_file(file.filename):
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            with open(file_path, "wb") as f:
                f.write(file.file.read())
            uploaded_files.append(file_path)
        else:
            raise HTTPException(status_code=400, detail=f"File not allowed: {file.filename}")

    # Process and index documents
    try:
        num_documents, num_segments = process_and_index_documents(
            uploaded_files, embeddings, faiss_index
        )
        return {
            "message": "Documents uploaded and indexed successfully.",
            "num_documents": num_documents,
            "num_segments": num_segments
        }
    except Exception as e:
        logger.error(f"Error processing documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to process documents.")
