from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import DashScopeEmbeddings
from pathlib import Path
load_dotenv()
LLM_MODEL_ID = os.getenv("LLM_MODEL_ID")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
EMBEDDING_MODEL_ID = os.getenv("EMBEDDING_MODEL_ID")
DATA_PATH = Path(__file__).parent.absolute()
# 配置模型和embedding
model = ChatOpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
    model=LLM_MODEL_ID,
    temperature=0.3,
)

embeddings = DashScopeEmbeddings(
    model=EMBEDDING_MODEL_ID,
    dashscope_api_key=LLM_API_KEY,
)