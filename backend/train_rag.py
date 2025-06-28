from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import os

os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["GROQ_API_KEY"] = "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"

Settings.llm = Groq(model="llama3-70b-8192")
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en")

documents = SimpleDirectoryReader("data",recursive=True).load_data()
index = VectorStoreIndex.from_documents(documents)

# Save the index
index.storage_context.persist(persist_dir="rag_engine/vector_index")

print("✅ Index trained and saved successfully.")
