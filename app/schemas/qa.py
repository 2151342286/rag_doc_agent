from pydantic import BaseModel


class QuestionRequest(BaseModel):
    question: str
    session_id: int


class SourceInfo(BaseModel):
    document_id: int
    title: str
    chunk_index: int
    content: str


class AnswerResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]