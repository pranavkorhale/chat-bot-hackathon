from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import os

# Suppress warnings
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Set Groq API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Configure LLM and embedding model
Settings.llm = Groq(model="llama3-70b-8192")  # Or "mixtral-8x7b-32768"
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en")

# Load documents & build index
documents = SimpleDirectoryReader("data").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()

# Continuous chat loop
print("SafeIndy Chatbot is ready! Type your question (or type 'exit' to quit):")
while True:
    question = input("You: ")
    if question.lower() in {"exit", "quit"}:
        print("Chatbot: Goodbye!")
        break
    response = query_engine.query(question)
    print(f"Chatbot: {response}")
