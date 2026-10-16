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
    # 默认锚定 backend/ 目录的绝对路径，与进程的当前工作目录（CWD）无关。
    # 这样无论从仓库根目录还是 backend/ 下启动，数据库都落在同一处，
    # 避免「按 README 启动后找不到数据」这类问题。
    # 注意：SQLAlchemy 的 sqlite 绝对路径需要四个斜杠（sqlite:////abs/path）。
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'projectmentor.db'}"

    # ===== 演示模式（公网分享给他人试用时开启）=====
    # 为空 = 门禁关闭，行为与本地单用户模式完全一致（默认）。
    # 填入任意口令即开启：访客需先输入口令，且各自的项目互相隔离。
    # 该字段同时用作访客 Cookie 的签名密钥。
    DEMO_PASSWORD: str = ""
    # 是否由后端托管前端构建产物（生产同源部署用，免 CORS）
    SERVE_FRONTEND: bool = False
    # 每日 AI 调用上限（保护分享者的钱包）。
    # 0 = 不限制（本地单用户模式的默认值）。
    # 按「实际 LLM 调用次数」统计：一次项目匹配约 2-3 次，
    # 一次任务拆解 1 次，一次答疑 1 次，一次复盘 1-2 次。
    # 分享给朋友试用时建议设为 50-100。
    DAILY_LLM_CALL_LIMIT: int = 0

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
