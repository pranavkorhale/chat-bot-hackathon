import os
import gc
from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from dotenv import load_dotenv
from llama_index.core import set_global_handler

# Initialize with simple handler
set_global_handler("simple")

load_dotenv()

# === Environment setup ===
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set.")

# === Configure models ===
Settings.llm = Groq(model="llama3-70b-8192", api_key=GROQ_API_KEY)
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en")

# Cache for the index
_index_cache = None

def get_response(question: str) -> str:
    global _index_cache
    
    try:
        if _index_cache is None:
            storage_context = StorageContext.from_defaults(
                persist_dir="rag_engine/vector_index"
            )
            _index_cache = load_index_from_storage(storage_context)
        
        query_engine = _index_cache.as_query_engine()
        response = query_engine.query(question)
        return str(response)
    except Exception as e:
        gc.collect()
        raise RuntimeError(f"Error processing query: {str(e)}")

def get_llm():
    return Settings.llm

def clear_cache():
    global _index_cache
    _index_cache = None
    gc.collect()