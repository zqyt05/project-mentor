"""项目知识库接口（RAG 的资料管理）。

路径前缀：/api/knowledge

归属校验与其余项目级接口一致：一律经 `project_service.get_project`
这个唯一收口点，越权访问返回 404 而非 403，避免泄露项目存在性。
"""

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import knowledge_service, project_service
from app.services.auth_service import current_visitor
from app.utils.response import BusinessError, success

router = APIRouter(prefix="/api/knowledge", tags=["项目知识库"])


@router.get("/{project_id}", summary="列出项目已上传的资料")
def list_documents(
    project_id: int,
    db: Session = Depends(get_db),
    visitor: str | None = Depends(current_visitor),
) -> dict:
    """返回资料列表，并告知是否启用了语义检索（模型不可用时会降级）。"""
    project_service.get_project(db, project_id, visitor)
    documents = knowledge_service.list_documents(db, project_id)
    return success(
        {
            "documents": [
                {
                    "id": document.id,
                    "filename": document.filename,
                    "file_type": document.file_type,
                    "char_count": document.char_count,
                    "chunk_count": document.chunk_count,
                    "embedded": document.embedded,
                    "created_at": document.created_at.isoformat(),
                }
                for document in documents
            ],
            "semantic_search": knowledge_service.embedding_available(),
            "supported_types": sorted(set(knowledge_service.SUPPORTED_TYPES.values())),
            "max_size_mb": knowledge_service.MAX_FILE_BYTES // 1024 // 1024,
        }
    )


@router.post("/{project_id}/upload", summary="上传资料并建立索引")
async def upload_document(
    project_id: int,
    file: UploadFile = File(..., description="txt / md / pdf / docx"),
    db: Session = Depends(get_db),
    visitor: str | None = Depends(current_visitor),
) -> dict:
    """解析、分块、向量化后入库。

    向量化是本地模型推理，不产生 API 费用，所以**不受每日 AI 调用配额限制**
    （配额保护的是花钱的对话模型调用）。
    """
    project_service.get_project(db, project_id, visitor)

    if not file.filename:
        raise BusinessError("缺少文件名")

    data = await file.read()
    document = knowledge_service.add_document(db, project_id, file.filename, data)

    return success(
        {
            "id": document.id,
            "filename": document.filename,
            "file_type": document.file_type,
            "char_count": document.char_count,
            "chunk_count": document.chunk_count,
            "embedded": document.embedded,
        },
        message=(
            f"已索引 {document.chunk_count} 个片段"
            if document.embedded
            else "已索引，但向量模型不可用，当前使用关键词检索"
        ),
    )


@router.delete("/{project_id}/{document_id}", summary="删除一份资料")
def delete_document(
    project_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    visitor: str | None = Depends(current_visitor),
) -> dict:
    """删除资料及其全部片段。"""
    project_service.get_project(db, project_id, visitor)
    knowledge_service.delete_document(db, project_id, document_id)
    return success({"id": document_id}, message="资料已删除")


@router.get("/{project_id}/search", summary="按问题检索资料（调试用）")
def search(
    project_id: int,
    q: str,
    top_k: int = 4,
    db: Session = Depends(get_db),
    visitor: str | None = Depends(current_visitor),
) -> dict:
    """直接查看检索结果，便于确认「答疑时到底拿到了哪些资料」。

    RAG 出问题时，这个接口能快速区分是「没检索到」还是「检索到了但模型没用」。
    """
    project_service.get_project(db, project_id, visitor)
    sources = knowledge_service.retrieve(db, project_id, q, top_k=max(1, min(top_k, 10)))
    return success(
        {
            "query": q,
            "sources": [
                {
                    "filename": source.filename,
                    "chunk_index": source.chunk_index,
                    "score": round(source.score, 3),
                    "content": source.content,
                }
                for source in sources
            ],
        }
    )
