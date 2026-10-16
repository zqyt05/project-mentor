"""演示模式的鉴权与访客身份。

## 为什么需要这个模块

本项目原本是「单用户本地工具」——没有账号体系，所有数据在一个 SQLite 里。
一旦通过公网隧道分享给朋友试用，就会暴露两个问题：

1. **费用与滥用**：后端的 DeepSeek Key 为所有调用付费。零门禁意味着
   链接一旦被转发，陌生人就能烧掉持有者的额度。
2. **数据混用**：朋友 A 会在「历史项目」里看到并删除朋友 B 的项目。

## 设计取舍

这是**轻量访客隔离**，不是完整的账号体系：

- 一个共享口令（`DEMO_PASSWORD`），不做注册/找回密码
- 登录成功后签发一个**签名 Cookie**，内容是随机访客 ID
- 访客 ID 即数据归属（`Project.owner_id`），彼此不可见
- Cookie 用 HMAC 签名，**防止伪造他人 ID 越权读取**

明确不解决的问题（对演示场景可接受，已在 README 说明）：
- 清除 Cookie 或换设备会失去自己的项目列表
- 口令泄露 = 任何人都能进入（但看不到既有访客的数据）

## 门禁关闭时的行为

`DEMO_PASSWORD` 为空（默认）时，门禁完全关闭：
`current_visitor` 返回 `None`，所有归属校验跳过，行为与本地单用户模式**完全一致**。
这样本地开发无需任何额外配置。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
from typing import Annotated

from fastapi import Cookie, HTTPException, Response, status

from app.config import settings

logger = logging.getLogger(__name__)

# Cookie 名称与有效期：演示期较长，避免朋友频繁重新登录
VISITOR_COOKIE = "pm_visitor"
COOKIE_MAX_AGE = 60 * 60 * 24 * 180  # 180 天


def is_gate_enabled() -> bool:
    """是否开启了演示门禁。未设置 DEMO_PASSWORD 时视为本地单用户模式。"""
    return bool(settings.DEMO_PASSWORD)


def _sign(payload: str) -> str:
    """用口令作为 HMAC 密钥对访客 ID 签名。

    刻意不额外引入密钥配置：演示场景下「口令即密钥」足够，
    且重启服务后签名依然有效（不会把所有人踢下线）。
    """
    digest = hmac.new(
        settings.DEMO_PASSWORD.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _make_token(visitor_id: str) -> str:
    """生成 `访客ID.签名` 形式的 Cookie 值。"""
    return f"{visitor_id}.{_sign(visitor_id)}"


def parse_token(token: str | None) -> str | None:
    """校验并解出访客 ID；签名不合法或格式错误返回 None。"""
    if not token or "." not in token:
        return None
    visitor_id, _, signature = token.rpartition(".")
    if not visitor_id or not signature:
        return None
    # compare_digest 防时序攻击
    if not hmac.compare_digest(signature, _sign(visitor_id)):
        logger.warning("访客 Cookie 签名校验失败，可能是伪造或口令已变更")
        return None
    return visitor_id


def verify_password(candidate: str) -> bool:
    """校验口令。空口令视为不匹配（避免误开门）。"""
    expected = settings.DEMO_PASSWORD
    if not expected:
        return False
    return hmac.compare_digest(candidate, expected)


def issue_visitor(response: Response) -> str:
    """签发新的访客身份并写入 Cookie，返回访客 ID。"""
    visitor_id = secrets.token_urlsafe(16)
    response.set_cookie(
        key=VISITOR_COOKIE,
        value=_make_token(visitor_id),
        max_age=COOKIE_MAX_AGE,
        httponly=True,  # 前端 JS 读不到，降低 XSS 窃取风险
        samesite="lax",
        # 注意：隧道场景下是 HTTPS，但本地调试走 http，
        # 因此这里不写死 secure=True，改由部署说明提醒使用 HTTPS。
        secure=False,
        path="/",
    )
    return visitor_id


def clear_visitor(response: Response) -> None:
    """清除访客 Cookie。"""
    response.delete_cookie(key=VISITOR_COOKIE, path="/")


def current_visitor(
    pm_visitor: Annotated[str | None, Cookie()] = None,
) -> str | None:
    """FastAPI 依赖：解析当前访客标识。

    - 门禁关闭 → 始终返回 None（本地单用户模式）
    - 门禁开启但未登录/签名无效 → 抛 401，由前端跳转登录页
    """
    if not is_gate_enabled():
        return None

    visitor_id = parse_token(pm_visitor)
    if visitor_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要先通过演示口令验证",
        )
    return visitor_id
