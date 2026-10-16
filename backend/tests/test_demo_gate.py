"""演示门禁与访客隔离的单元测试。

与 `/tmp` 下的端到端脚本互补：这里覆盖**逻辑层**，全部离线、不碰 LLM。
端到端脚本负责验证真实隧道/浏览器场景。

覆盖：
- 门禁关闭时完全放行（本地单用户模式，不能因改造而回归）
- 门禁开启时的鉴权、口令校验、Cookie 签名
- 访客之间的数据隔离与越权拦截
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Project
from app.services import auth_service


def _make_project(db: Session, name: str, owner_id: str | None) -> Project:
    project = Project(
        name=name,
        domain="测试方向",
        difficulty="入门",
        owner_id=owner_id,
    )
    db.add(project)
    db.commit()
    return project


class TestGateDisabled:
    """门禁关闭（默认）：行为必须与改造前完全一致。"""

    def test_me_reports_not_required(self, client: TestClient) -> None:
        body = client.get("/api/auth/me").json()
        assert body["data"]["required"] is False
        assert body["data"]["authenticated"] is True

    def test_project_list_needs_no_cookie(self, client: TestClient) -> None:
        assert client.get("/api/project/list").json()["code"] == 0

    def test_login_is_noop(self, client: TestClient) -> None:
        body = client.post("/api/auth/login", json={"password": "whatever"}).json()
        assert body["code"] == 0
        assert body["data"]["required"] is False

    def test_local_projects_are_visible(self, client: TestClient, db: Session) -> None:
        """owner_id 为 None 的本机数据在门禁关闭时应可见。"""
        _make_project(db, "本机项目", None)
        assert len(client.get("/api/project/list").json()["data"]) == 1


class TestGateEnabled:
    """门禁开启：未登录一律拦截。"""

    def test_me_reports_required(
        self, client: TestClient, enable_gate: str
    ) -> None:
        body = client.get("/api/auth/me").json()
        assert body["data"]["required"] is True
        assert body["data"]["authenticated"] is False

    def test_project_endpoints_require_auth(
        self, client: TestClient, enable_gate: str
    ) -> None:
        for method, path in [
            ("get", "/api/project/list"),
            ("get", "/api/project/1"),
            ("delete", "/api/project/1"),
            ("get", "/api/task/project/1/stages"),
            ("get", "/api/review/1"),
        ]:
            response = getattr(client, method)(path)
            assert response.status_code == 401, f"{method} {path} 未被拦截"

    def test_wrong_password_rejected(
        self, client: TestClient, enable_gate: str
    ) -> None:
        body = client.post("/api/auth/login", json={"password": "wrong"}).json()
        assert body["code"] == 401

    def test_empty_password_rejected(
        self, client: TestClient, enable_gate: str
    ) -> None:
        body = client.post("/api/auth/login", json={"password": ""}).json()
        assert body["code"] == 401

    def test_login_issues_cookie(
        self, client: TestClient, enable_gate: str
    ) -> None:
        response = client.post("/api/auth/login", json={"password": enable_gate})
        assert response.json()["code"] == 0
        assert auth_service.VISITOR_COOKIE in response.cookies
        assert client.get("/api/project/list").json()["code"] == 0


class TestCookieSignature:
    """Cookie 签名：防伪造他人访客 ID 越权。"""

    def test_valid_token_round_trip(self, enable_gate: str) -> None:
        token = auth_service._make_token("visitor-abc")
        assert auth_service.parse_token(token) == "visitor-abc"

    def test_forged_signature_rejected(self, enable_gate: str) -> None:
        assert auth_service.parse_token("visitor-abc.forged") is None

    def test_garbage_rejected(self, enable_gate: str) -> None:
        for bad in [None, "", "no-dot", ".", "abc.", ".sig"]:
            assert auth_service.parse_token(bad) is None

    def test_signature_is_stable_across_calls(self, enable_gate: str) -> None:
        """签名不能带随机数，否则服务重启会把所有人踢下线。"""
        assert auth_service._make_token("v1") == auth_service._make_token("v1")

    def test_different_visitors_differ(self, enable_gate: str) -> None:
        assert auth_service._make_token("v1") != auth_service._make_token("v2")

    def test_password_change_invalidates_token(self, monkeypatch) -> None:
        """更换口令应让既有 Cookie 失效（签名密钥变了）。"""
        from app.config import settings

        monkeypatch.setattr(settings, "DEMO_PASSWORD", "old-pass")
        token = auth_service._make_token("visitor-x")
        assert auth_service.parse_token(token) == "visitor-x"

        monkeypatch.setattr(settings, "DEMO_PASSWORD", "new-pass")
        assert auth_service.parse_token(token) is None


class TestVisitorIsolation:
    """两个访客的数据必须互不可见、互不可改。"""

    def _login(self, client: TestClient, password: str) -> None:
        assert client.post("/api/auth/login", json={"password": password}).json()["code"] == 0

    def test_list_only_shows_own_projects(
        self, client: TestClient, db: Session, enable_gate: str
    ) -> None:
        self._login(client, enable_gate)
        mine = client.get("/api/auth/me").json()["data"]["visitor_label"]
        assert mine

        # 直接落一条属于他人的项目
        _make_project(db, "别人的项目", "someone-else")
        assert client.get("/api/project/list").json()["data"] == []

    def test_read_other_project_returns_404(
        self, client: TestClient, db: Session, enable_gate: str
    ) -> None:
        other = _make_project(db, "别人的项目", "someone-else")
        self._login(client, enable_gate)

        body = client.get(f"/api/project/{other.id}").json()
        assert body["code"] == 404
        # 文案不能泄露「存在但无权访问」
        assert "不存在" in body["message"]

    def test_delete_other_project_returns_404(
        self, client: TestClient, db: Session, enable_gate: str
    ) -> None:
        other = _make_project(db, "别人的项目", "someone-else")
        self._login(client, enable_gate)

        assert client.delete(f"/api/project/{other.id}").json()["code"] == 404
        # 确实没被删掉
        assert db.get(Project, other.id) is not None

    def test_task_endpoints_check_project_ownership(
        self, client: TestClient, db: Session, enable_gate: str
    ) -> None:
        """任务自身没有归属字段，必须通过所属项目校验。"""
        from app.models import Stage, Task

        other = _make_project(db, "别人的项目", "someone-else")
        stage = Stage(project_id=other.id, name="阶段一", order_index=1)
        db.add(stage)
        db.flush()
        task = Task(project_id=other.id, stage_id=stage.id, name="别人的任务", order_index=1)
        db.add(task)
        db.commit()

        self._login(client, enable_gate)
        assert client.get(f"/api/task/{task.id}").json()["code"] == 404
        assert client.post(f"/api/task/{task.id}/start").json()["code"] == 404
        assert client.post(f"/api/task/{task.id}/complete").json()["code"] == 404

    def test_own_project_still_accessible(
        self, client: TestClient, db: Session, enable_gate: str
    ) -> None:
        """拦截不能误伤：访客必须能正常访问自己的项目。"""
        self._login(client, enable_gate)
        own = _make_project(db, "我的项目", None)

        # 把「我的项目」改成当前访客所有，模拟真实创建流程
        visitor_id = auth_service.parse_token(
            client.cookies.get(auth_service.VISITOR_COOKIE)
        )
        own.owner_id = visitor_id
        db.commit()

        assert client.get(f"/api/project/{own.id}").json()["code"] == 0
        assert len(client.get("/api/project/list").json()["data"]) == 1
