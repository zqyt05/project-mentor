"""全局配置管理模块。

所有敏感信息（API Key、Token 等）统一从环境变量读取，禁止硬编码。
配置文件位置：backend/.env（该文件已被 .gitignore 忽略）。
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录：backend/
BASE_DIR = Path(__file__).resolve().parent.parent
# Prompt 模板目录
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class Settings(BaseSettings):
    """应用配置，字段名与环境变量名一一对应（大小写不敏感）。"""

    # ===== 应用元信息 =====
    APP_NAME: str = "ProjectMentor API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ===== 服务监听 =====
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # ===== DeepSeek / LLM =====
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-flash"
    # deepseek-flash 为推理模型，思考过程会消耗 token，需预留充足预算
    LLM_MAX_TOKENS: int = 8192
    LLM_TEMPERATURE: float = 0.4
    LLM_TIMEOUT: int = 180

    # ===== GitHub =====
    GITHUB_TOKEN: str = ""
    GITHUB_API_BASE: str = "https://api.github.com"
    # GitHub 检索筛选条件（详见 PRD 模块 1）
    GITHUB_MIN_STARS: int = 500
    GITHUB_CANDIDATE_LIMIT: int = 10
    # 优质项目不足该数量时降级到 AI 定制路径
    GITHUB_MIN_QUALIFIED: int = 3

    # ===== 数据库 =====
    DATABASE_URL: str = "sqlite:///./projectmentor.db"

    # ===== CORS =====
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """把逗号分隔的 CORS 配置解析为列表。"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """获取全局配置单例（带缓存，避免重复解析 .env）。"""
    return Settings()


settings = get_settings()
