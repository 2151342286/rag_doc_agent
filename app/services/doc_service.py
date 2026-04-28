import asyncio
import uuid
from pathlib import Path
import hashlib
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.rag_service import process_document
from app.core.config import settings,BASE_DIR
from app.models.document import Document, DocStatus


UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
# 允许的文件类型
ALLOWED_TYPES = {".pdf", ".txt", ".md"}

async def upload_document(db: AsyncSession, user_id: int, file: UploadFile) -> Document:
    """保存文件，创建文档记录，状态为 uploading"""
    # 校验文件类型
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {ext or '未知'}，仅支持 PDF、TXT、MD",
        )
    # 校验文件大小
    contents = await file.read()
    file_hash = hashlib.md5(contents).hexdigest()
    # 查重
    result = await db.execute(
        select(Document).where(
            Document.user_id == user_id,
            Document.file_hash == file_hash,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"文件已存在（ID: {existing.id}），请勿重复上传",
        )
    if len(contents) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过 {settings.MAX_UPLOAD_SIZE_MB}MB 限制",
        )

    # 生成唯一文件名，防止覆盖
    ext = Path(file.filename).suffix if file.filename else ""
    saved_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / saved_name

    with open(file_path, "wb") as f:
        f.write(contents)

    # 取原始文件名和扩展名
    original_title = file.filename or "unknown"
    file_type = ext.lstrip(".") if ext else None

    doc = Document(
        user_id=user_id,
        title=original_title,
        file_type=file_type,
        file_size=len(contents),
        status=DocStatus.UPLOADING,
        file_hash=file_hash,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    asyncio.create_task(process_document(doc.id, file_path))
    return doc


async def list_documents(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Document], int]:
    """分页查询用户的文档列表"""
    # 查询总数
    count_result = await db.execute(
        select(func.count()).select_from(Document).where(Document.user_id == user_id)
    )
    total = count_result.scalar() or 0

    # 查询列表
    result = await db.execute(
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.creat_time.desc())
        .offset(skip)
        .limit(limit)
    )
    documents = result.scalars().all()

    return list(documents), total