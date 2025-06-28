from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import os

os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

Settings.llm = Groq(model="llama3-70b-8192")
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en")

documents = SimpleDirectoryReader("data",recursive=True).load_data()
index = VectorStoreIndex.from_documents(documents)

# Save the index
index.storage_context.persist(persist_dir="rag_engine/vector_index")

print("✅ Index trained and saved successfully.")
