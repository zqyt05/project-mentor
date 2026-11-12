"""项目知识库服务（RAG：解析 → 分块 → 向量化 → 检索）。

## 技术选型说明

**为什么不用 DeepSeek 做 embedding**：DeepSeek 只提供对话模型
（deepseek-flash / deepseek-v4-pro），实测 `/v1/embeddings` 返回 404，
没有 embedding 接口。因此向量化只能用本地模型或第三方 API。

**为什么是 fastembed 而不是 sentence-transformers**：后者依赖 PyTorch
（约 2GB），对一个本地单用户工具太重。fastembed 走 ONNX Runtime，
模型 `BAAI/bge-small-zh-v1.5` 只有 91MB，实测中文语义区分有效：
「存货周转率」vs「库存周转天数」相似度 0.754，
对比「React useEffect」仅 0.328。

**为什么模型下载要指定国内镜像**：HuggingFace 直连在国内经常超时，
实测必须走 `hf-mirror.com`。默认值已指向镜像，可用环境变量覆盖。

**降级策略（重要）**：模型可能因为网络、磁盘、平台不兼容而加载失败。
此时**不能**让知识库整体不可用 —— 自动退化为关键词检索（BM25 式的简单
打分），功能照常工作、只是语义召回变弱，并在界面上如实标注。
"""

from __future__ import annotations

import io
import logging
import math
import os
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import BASE_DIR
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.utils.response import CODE_BAD_REQUEST, CODE_NOT_FOUND, BusinessError

logger = logging.getLogger(__name__)

# ==============================================================================
# 向量模型（懒加载单例）
# ==============================================================================

EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
# 中文小模型，512 维，91MB。改模型会让已有向量失效，需要重建知识库。
EMBEDDING_DIM = 512

_model = None
_model_failed = False


def _configure_hf_endpoint() -> None:
    """把 HuggingFace 指向国内镜像。

    必须在导入 fastembed **之前**设置才生效，所以放在模块级。
    用户可通过 HF_ENDPOINT 覆盖（例如有代理时直连）。
    """
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")


def _cache_dir() -> str:
    """模型缓存目录：放在**仓库根目录**下的 .hf-cache，便于随项目清理。

    不放用户主目录，是为了让「换机器」「清系统缓存」都不必重下 91MB，
    也方便 Docker 构建时把模型直接烘进镜像层。

    注意用 BASE_DIR（backend/）的上一级，而不是数 __file__ 的层数 ——
    后者容易算错一级，导致缓存永远不命中、每次都重新下载。
    """
    custom = os.environ.get("KNOWLEDGE_MODEL_CACHE")
    if custom:
        return custom
    return str(BASE_DIR.parent / ".hf-cache" / "fastembed")


def get_model():
    """获取向量模型；不可用时返回 None（触发关键词降级）。"""
    global _model, _model_failed

    if _model is not None:
        return _model
    if _model_failed:
        return None

    _configure_hf_endpoint()
    try:
        from fastembed import TextEmbedding

        _model = TextEmbedding(model_name=EMBEDDING_MODEL, cache_dir=_cache_dir())
        logger.info("向量模型已加载：%s", EMBEDDING_MODEL)
        return _model
    except Exception as exc:  # 网络、磁盘、平台兼容性等
        _model_failed = True
        logger.warning(
            "向量模型加载失败，知识库降级为关键词检索：%s。"
            "如需语义检索，请确认能访问 hf-mirror.com（约 91MB 模型）。",
            exc,
        )
        return None


def embedding_available() -> bool:
    """向量检索是否可用（供界面提示）。"""
    return get_model() is not None


def reset_model_state() -> None:
    """重置单例状态。测试用。"""
    global _model, _model_failed
    _model = None
    _model_failed = False


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """批量向量化。模型不可用时返回 None。"""
    model = get_model()
    if model is None:
        return None
    try:
        # fastembed 返回 numpy 数组，转成 list 才能存 JSON 列
        return [[float(x) for x in vector] for vector in model.embed(texts)]
    except Exception as exc:
        logger.warning("向量化失败，本次降级为关键词检索：%s", exc)
        return None


# ==============================================================================
# 文档解析
# ==============================================================================

SUPPORTED_TYPES = {
    "txt": "txt",
    "md": "md",
    "markdown": "md",
    "pdf": "pdf",
    "docx": "docx",
}
# 单文件大小上限：演示环境下足够，也能防止误传超大文件拖垮嵌入
MAX_FILE_BYTES = 5 * 1024 * 1024


def _file_type(filename: str) -> str:
    suffix = PurePosixPath(filename).suffix.lower().lstrip(".")
    if suffix not in SUPPORTED_TYPES:
        raise BusinessError(
            f"不支持的文件类型：.{suffix or '未知'}。"
            f"目前支持 {', '.join(sorted(set(SUPPORTED_TYPES.values())))}",
            CODE_BAD_REQUEST,
        )
    return SUPPORTED_TYPES[suffix]


def parse_document(filename: str, data: bytes) -> tuple[str, str]:
    """把上传的文件解析成纯文本，返回 (文本, 归一化类型)。"""
    file_type = _file_type(filename)

    if not data:
        raise BusinessError("文件内容为空", CODE_BAD_REQUEST)
    if len(data) > MAX_FILE_BYTES:
        raise BusinessError(
            f"文件过大（{len(data) // 1024} KB），上限 {MAX_FILE_BYTES // 1024 // 1024} MB",
            CODE_BAD_REQUEST,
        )

    try:
        if file_type in ("txt", "md"):
            text = data.decode("utf-8", errors="replace")
        elif file_type == "pdf":
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        else:  # docx
            from docx import Document

            document = Document(io.BytesIO(data))
            parts = [paragraph.text for paragraph in document.paragraphs]
            # 表格内容常是重点（财务数据、指标定义），一并抽出
            for table in document.tables:
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    if any(cells):
                        parts.append(" | ".join(cells))
            text = "\n".join(parts)
    except BusinessError:
        raise
    except Exception as exc:
        raise BusinessError(f"文件解析失败：{exc}", CODE_BAD_REQUEST) from exc

    text = _normalize(text)
    if not text.strip():
        raise BusinessError(
            "没能从文件里提取到文字。若是扫描版 PDF（图片），需要先做 OCR",
            CODE_BAD_REQUEST,
        )
    return text, file_type


def _normalize(text: str) -> str:
    """统一换行、压缩多余空白，但不破坏段落结构（分块要用）。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\u3000]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ==============================================================================
# 分块
# ==============================================================================

# 块大小按中文字符数计。400 字约等于一段落，既能保住上下文，又不至于
# 让一次检索带进太多无关内容。
CHUNK_SIZE = 400
CHUNK_OVERLAP = 60


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """按段落聚合切块，块之间保留少量重叠。

    先按空行/换行拆段，再贪心合并到接近 size；超长段落内部强制切开。
    保留重叠是为了避免答案正好落在切点上被割断。
    """
    if not text.strip():
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
    chunks: list[str] = []
    buffer = ""

    def flush() -> None:
        nonlocal buffer
        if buffer.strip():
            chunks.append(buffer.strip())
        buffer = ""

    for paragraph in paragraphs:
        # 单段本身就超长 → 先冲掉缓冲，再按长度硬切
        if len(paragraph) > size:
            flush()
            start = 0
            while start < len(paragraph):
                chunks.append(paragraph[start : start + size])
                start += size - overlap
            continue

        if len(buffer) + len(paragraph) + 1 <= size:
            buffer = f"{buffer}\n{paragraph}" if buffer else paragraph
        else:
            flush()
            # 与上一块的重叠：取上一块尾部
            tail = chunks[-1][-overlap:] if chunks else ""
            buffer = f"{tail}\n{paragraph}" if tail else paragraph

    flush()
    return [chunk for chunk in chunks if chunk.strip()]


# ==============================================================================
# 写入与读取
# ==============================================================================


@dataclass
class RetrievedChunk:
    """检索结果。"""

    chunk_id: int
    document_id: int
    filename: str
    chunk_index: int
    content: str
    score: float


def add_document(
    db: Session, project_id: int, filename: str, data: bytes
) -> KnowledgeDocument:
    """解析、分块、向量化并落库。"""
    text, file_type = parse_document(filename, data)
    pieces = chunk_text(text)
    if not pieces:
        raise BusinessError("文件里没有可用的文本片段", CODE_BAD_REQUEST)

    document = KnowledgeDocument(
        project_id=project_id,
        filename=filename,
        file_type=file_type,
        char_count=len(text),
        chunk_count=len(pieces),
        embedded=False,
    )
    db.add(document)
    db.flush()  # 拿到 document.id

    vectors = embed_texts(pieces)
    for index, piece in enumerate(pieces):
        db.add(
            KnowledgeChunk(
                document_id=document.id,
                project_id=project_id,
                chunk_index=index,
                content=piece,
                embedding=vectors[index] if vectors else None,
            )
        )

    document.embedded = vectors is not None
    db.commit()
    db.refresh(document)
    logger.info(
        "知识库新增：%s（%s 字 → %s 块，向量化%s）",
        filename,
        document.char_count,
        document.chunk_count,
        "成功" if document.embedded else "失败（已降级）",
    )
    return document


def list_documents(db: Session, project_id: int) -> list[KnowledgeDocument]:
    """列出项目下已上传的资料（新→旧）。"""
    stmt = (
        select(KnowledgeDocument)
        .where(KnowledgeDocument.project_id == project_id)
        .order_by(KnowledgeDocument.id.desc())
    )
    return list(db.execute(stmt).scalars().all())


def delete_document(db: Session, project_id: int, document_id: int) -> None:
    """删除一份资料及其全部片段。"""
    document = db.get(KnowledgeDocument, document_id)
    if document is None or document.project_id != project_id:
        raise BusinessError(f"资料不存在（id={document_id}）", CODE_NOT_FOUND)
    db.delete(document)  # 片段由 cascade 连带删除
    db.commit()


def count_documents(db: Session, project_id: int) -> int:
    stmt = select(KnowledgeDocument).where(KnowledgeDocument.project_id == project_id)
    return len(list(db.execute(stmt).scalars().all()))


# ==============================================================================
# 检索
# ==============================================================================


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


# 中文常见虚词：关键词打分时不该参与匹配
_STOPWORDS = set("的了和是在有与及或就把被让给从对为也就都而及其这个那个我你他她它")


def _keyword_score(query: str, content: str) -> float:
    """关键词打分（降级方案）。

    用字符二元组做重叠度，配合虚词过滤 —— 中文不需要分词器也能有
    可用的召回，代价是语义泛化能力弱于向量检索。
    """
    query_chars = [c for c in query if c.strip() and c not in _STOPWORDS]
    if not query_chars:
        return 0.0

    grams = {query_chars[i] + query_chars[i + 1] for i in range(len(query_chars) - 1)}
    if not grams:
        grams = set(query_chars)

    hits = sum(1 for gram in grams if gram in content)
    return hits / len(grams)


def retrieve(
    db: Session, project_id: int, query: str, top_k: int = 4
) -> list[RetrievedChunk]:
    """在项目知识库里检索与问题最相关的片段。

    优先向量检索；模型不可用或该片段没有向量时回退到关键词打分。
    """
    stmt = select(KnowledgeChunk).where(KnowledgeChunk.project_id == project_id)
    chunks = list(db.execute(stmt).scalars().all())
    if not chunks:
        return []

    documents = {
        doc.id: doc for doc in list_documents(db, project_id)
    }

    query_vector = None
    if any(chunk.embedding for chunk in chunks):
        vectors = embed_texts([query])
        if vectors:
            query_vector = vectors[0]

    scored: list[RetrievedChunk] = []
    for chunk in chunks:
        if query_vector is not None and chunk.embedding:
            score = _cosine(query_vector, chunk.embedding)
        else:
            score = _keyword_score(query, chunk.content)

        document = documents.get(chunk.document_id)
        scored.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                filename=document.filename if document else "未知资料",
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=score,
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    # 分数太低的不该硬塞进上下文：向量相似度 0.35 / 关键词重叠 0.15 以下
    # 基本是无关内容，塞进去只会干扰回答。
    threshold = 0.35 if query_vector is not None else 0.15
    return [item for item in scored[:top_k] if item.score >= threshold]


def build_retrieval_context(chunks: list[RetrievedChunk]) -> str:
    """把检索结果拼成可注入提示词的文本，带编号便于模型引用。"""
    if not chunks:
        return ""
    lines = ["以下是学习者上传的资料中与问题最相关的片段，回答时请优先依据这些内容，"
             "并在引用处标注编号（如 [资料1]）："]
    for index, chunk in enumerate(chunks, start=1):
        lines.append(f"\n[资料{index}] 来源：{chunk.filename}\n{chunk.content}")
    return "\n".join(lines)
