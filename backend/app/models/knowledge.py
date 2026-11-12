"""项目知识库模型（RAG）。

## 为什么需要

答疑窗口原本只能看到「当前任务 + 最近 12 条对话」。学习者手里通常有
课程讲义、行业报告、自己的笔记 —— 这些资料 AI 完全看不到，
回答只能靠模型自身知识，容易泛泛而谈、也无法核对。

知识库让用户把资料上传到项目里，答疑时检索相关片段并标注出处，
把回答从「凭印象」变成「有据可查」。

## 两层结构

- `KnowledgeDocument`：一份上传的文件（用于列表展示与整体删除）
- `KnowledgeChunk`：切分后的片段 + 向量（检索的最小单位）

片段里冗余存了 `project_id`，让检索可以一次查完整个项目，
不必先 join 文档表。
"""

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class KnowledgeDocument(Base, TimestampMixin):
    """一份上传到项目的参考资料。"""

    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # 归一化后的类型：txt / md / pdf / docx
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 向量化是否成功。降级为关键词检索时这里为 False，界面据此提示
    embedded: Mapped[bool] = mapped_column(nullable=False, default=False)

    # 刻意不用 passive_deletes：那会让删除依赖数据库的 ON DELETE CASCADE，
    # 而 SQLite 默认不开启外键约束（需 PRAGMA foreign_keys=ON）。
    # 依赖它就等于「生产能删、测试留下孤儿行」，行为不一致。
    # 每份资料的片段数只有几十个，由 ORM 级联删除完全够用。
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class KnowledgeChunk(Base, TimestampMixin):
    """知识片段：检索的最小单位。

    `embedding` 存成 JSON 数组。本项目的数据规模是「单用户、几个项目、
    几十份资料」，暴力余弦检索足够快；引入向量数据库在这个量级上只是
    增加部署复杂度。接口设计成可替换，将来量大时换掉存储即可。
    """

    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 向量为 None 表示该片段只参与关键词检索（模型不可用时的降级）
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")
