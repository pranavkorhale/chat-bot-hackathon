import os
from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# === Set environment variables ===
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["GROQ_API_KEY"] = "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"  # 🔑 Replace with your actual key

# === Configure models ===
Settings.llm = Groq(model="llama3-70b-8192")  # Or "mixtral-8x7b-32768"
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en")




# === Define response function ===
def get_response(question: str) -> str:
    storage_context = StorageContext.from_defaults(persist_dir="rag_engine/vector_index")
    index = load_index_from_storage(storage_context)
    query_engine = index.as_query_engine()
    return str(query_engine.query(question))

def get_llm():
    return Settings.llm
