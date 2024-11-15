# app/routes/ask_route.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.question_handler import generate_response
from app.utils.logger import logger
from app.documentary_researcher import retrieve_context
import traceback

# Initialize router
router = APIRouter()

# Configurations
MODEL_NAME = "llama3.2"

# Declare embeddings and faiss_index as global variables
embeddings = None
faiss_index = None

# Define a simple system prompt
SYSTEM_PROMPT = "Vous êtes Amélie, une assistante virtuelle pour répondre aux questions générales et aux recherches documentaires."


# New documentary prompt template to dynamically insert question and citations
DOCUMENTARY_PROMPT_TEMPLATE = (
    "Vous êtes un assistant aidant à répondre aux questions en utilisant les extraits les plus pertinents des documents fournis, sans modifications. "
    "Votre objectif est d'analyser les informations contenues dans ces extraits pour offrir une réponse claire, structurée et cohérente sous la forme d’un commentaire de texte.\n\n"
    
    "Répondez à la question en suivant les étapes ci-dessous sans indiquer de titres pour chaque étape dans votre réponse. "
    "Suivez cette structure pour garantir une réponse précise et bien organisée :\n\n"
    
    "1. Sélectionnez uniquement les extraits qui contiennent des informations directement pertinentes pour répondre précisément à la question. "
    "Si un extrait est partiellement pertinent, choisissez le sous-ensemble le plus pertinent pour la question, tout en veillant à ce qu’il reste compréhensible et cohérent sans ajout. "
    "Évitez les extraits tronqués qui pourraient paraître coupés de manière incohérente, et ne retenez qu’un sous-ensemble si cela contribue clairement à la réponse.\n\n"
    
    "2. Présentez les extraits sélectionnés dans une liste numérotée. Incluez chaque extrait entre guillemets et indiquez la source au format suivant :\n"
    "   Pour répondre à votre question '{question}', voici les extraits pertinents que j'ai trouvés :\n"
    "   1. \"{{Extrait complet ou sous-extrait selon pertinence}}\" (nom_du_document, page)\n"
    "   2. \"{{Extrait complet ou sous-extrait selon pertinence}}\" (nom_du_document, page)\n\n"
    
    "3. Analysez ces extraits en deux étapes sans utiliser de titres pour les parties. Cette analyse doit être extrêmement complète et autonome, car l'utilisateur ne lira pas les extraits eux-mêmes. La réponse doit donc être suffisante en elle-même pour présenter les preuves nécessaires, les conclusions partielles et la conclusion globale :\n"
    "   - Dans la première partie de votre réponse, revenez sur chaque extrait en mettant en avant les passages clés et en expliquant leur signification par rapport à la question posée. "
    "Utilisez des techniques de discours indirect, citation en filigrane, ou paraphrase pour intégrer subtilement les extraits dans votre analyse. "
    "Faites des conclusions partielles pour chaque point pertinent.\n"
    "   - Dans la partie finale de votre réponse, fournissez une conclusion globale qui résume l'essentiel des points analysés précédemment. "
    "Cette conclusion doit être synthétique et répondre pleinement à la question posée.\n\n"
    
    "Si les extraits ne répondent pas complètement à la question, indiquez 'Je ne sais pas'. Utilisez un ton formel.\n\n"
    
    "**Question** : {question}\n\n"
    "**Extraits disponibles (non visible par l'utilisateur)** :\n"
    "{citations}\n\n"
    "**Question** : {question}\n\n"
    "Réponse en Français :"
)


class Message(BaseModel):
    role: str
    content: str

class QuestionRequest(BaseModel):
    question: str
    requiresDocumentSearch: bool  # Indicates if document retrieval is needed
    history: list[Message]  # Full chat history with role and content fields only

def format_citations(retrieved_context):
    """Generate citations from retrieved context directly in ask_route."""
    citation_texts = []
    for i, doc in enumerate(retrieved_context, start=1):
        document_name = doc["metadata"].get("source", "Unknown")
        page_number = doc["metadata"].get("page", "N/A")
        citation = f"{i}. \"{doc['page_content'].strip()}\" ({document_name}, page {page_number})"
        citation_texts.append(citation)
    return "\n\n".join(citation_texts)

@router.post("/ask")
async def ask(question: QuestionRequest):
    if not embeddings or not faiss_index:
        logger.error("Embeddings and FAISS index are not initialized.")
        logger.error(f"Embeddings: {embeddings}")
        logger.error(f"faiss_index: {faiss_index}")
        raise HTTPException(status_code=500, detail="Embeddings and FAISS index are not initialized.")

    try:
        # Construct the initial system prompt
        conversation = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add conversation history with explicit roles for previous messages
        for msg in question.history:
            conversation.append({"role": msg.role, "content": msg.content})

        # Determine if a documentary prompt and context are required
        context_text = ""  # Initialize as empty; only add if document search is needed
        if question.requiresDocumentSearch:
            # Retrieve context from the documents
            retrieved_context, retrieval_duration = retrieve_context(question.question, faiss_index)
            context_text = format_citations(retrieved_context)

            # Format the documentary prompt with the question and citations
            documentary_prompt = DOCUMENTARY_PROMPT_TEMPLATE.format(
                question=question.question,
                citations=context_text
            )
            conversation.append({"role": "user", "content": documentary_prompt})
        else:
            # Add the user's question directly for general inquiries
            conversation.append({"role": "user", "content": question.question})

        # Generate response with conversation context
        response_text, generation_duration = generate_response(conversation, MODEL_NAME)

        # Prepare the response data with optional context (for front end only)
        response_data = {
            "context": documentary_prompt.strip() if question.requiresDocumentSearch else "",
            "answer": response_text.strip(),
            "retrieval_time": retrieval_duration if question.requiresDocumentSearch else None,
            "generation_time": generation_duration,
            "total_time": (retrieval_duration if question.requiresDocumentSearch else 0) + generation_duration
        }

        return response_data
    except Exception as e:
        logger.error(f"Failed to generate response: {e}")
        logger.error("Traceback:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to generate response.")
