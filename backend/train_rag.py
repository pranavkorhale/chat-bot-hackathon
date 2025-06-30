from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import os
from dotenv import load_dotenv
load_dotenv()
# === Environment setup ===
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set.")

# === Configure LLM and embedding ===
Settings.llm = Groq(model="llama3-70b-8192", api_key=GROQ_API_KEY)
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en")

# === Load documents and build index ===
documents = SimpleDirectoryReader("data", recursive=True).load_data()
index = VectorStoreIndex.from_documents(documents)

# === Save index ===
index.storage_context.persist(persist_dir="rag_engine/vector_index")

print("✅ Index trained and saved successfully.")
