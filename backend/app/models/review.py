"""费曼学习法复盘数据模型。

用户先输出自己的理解，AI 再从「纠错 / 补全 / 优化结构 / 深化建议」四个维度处理，
最终生成可一键复制的复盘文档。
"""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.project import Project


class Review(Base, TimestampMixin):
    """一次复盘记录。"""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    form: Mapped[str] = mapped_column(String(20), nullable=False, default="structured")

    # 用户在引导问题下填写的原始复盘内容
    user_content: Mapped[str] = mapped_column(Text, default="")
    # AI 优化后的最终复盘文档（Markdown）
    final_content: Mapped[str] = mapped_column(Text, default="")

    # 结构化处理结果，便于前端分区展示
    corrections: Mapped[list] = mapped_column(JSON, default=list, comment="理解纠错")
    supplements: Mapped[list] = mapped_column(JSON, default=list, comment="知识点补全")
    structure_advice: Mapped[str] = mapped_column(Text, default="", comment="结构优化建议")
    next_steps: Mapped[list] = mapped_column(JSON, default=list, comment="深化学习建议")

    project: Mapped["Project"] = relationship(back_populates="reviews")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Review id={self.id} project_id={self.project_id} form={self.form}>"
