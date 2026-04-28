from langchain_openai import  ChatOpenAI
from langchain_community.embeddings import DashScopeEmbeddings
from app.core.config import settings
from FlagEmbedding import FlagReranker

embeddings = DashScopeEmbeddings(
    model=settings.EMBEDDING_MODEL,
    dashscope_api_key=settings.EMBEDDING_API_KEY
)

llm = ChatOpenAI(
    model=settings.LLM_MODEL,
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL,
    temperature=0.3,
)
if settings.RERANKER_MODEL_PATH is not None:
    reranker = FlagReranker(settings.RERANKER_MODEL_PATH, use_fp16=True,local_files_only=True)
else:
    reranker = None
