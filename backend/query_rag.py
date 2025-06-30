import os
from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from dotenv import load_dotenv
load_dotenv()
# === Set environment variables ===
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set.")

# === Configure models ===
Settings.llm = Groq(model="llama3-70b-8192", api_key=GROQ_API_KEY)
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en")

# === Define response function ===
def get_response(question: str) -> str:
    storage_context = StorageContext.from_defaults(persist_dir="rag_engine/vector_index")
    index = load_index_from_storage(storage_context)
    query_engine = index.as_query_engine()
    return str(query_engine.query(question))

def get_llm():
    return Settings.llm
