"""接口契约测试：统一响应格式与全局异常处理。

这些用例保证前端永远只需要处理一种响应结构 `{code, message, data}`，
不会因为某个接口改了异常处理方式而导致前端解析失败。

说明：全部用例都不触碰 AI 与 GitHub（校验在进入业务逻辑前就完成了）。
"""

from fastapi.testclient import TestClient

REQUIRED_KEYS = {"code", "message", "data"}


class TestResponseContract:
    """所有响应都必须是 {code, message, data} 三字段。"""

    def test_health_success(self, client: TestClient) -> None:
        response = client.get("/api/health")
        assert response.status_code == 200

        body = response.json()
        assert set(body) == REQUIRED_KEYS
        assert body["code"] == 0
        assert body["data"]["status"] == "ok"

    def test_list_success_returns_empty_array(self, client: TestClient) -> None:
        body = client.get("/api/project/list").json()
        assert body["code"] == 0
        assert body["data"] == []

    def test_success_message_default(self, client: TestClient) -> None:
        body = client.get("/api/health").json()
        assert body["message"] == "success"


class TestErrorContract:
    """错误也必须走同一套结构，且给出用户可读的中文提示。"""

    def test_not_found_project(self, client: TestClient) -> None:
        body = client.get("/api/project/999999").json()
        assert body["code"] == 404
        assert "不存在" in body["message"]
        assert body["data"] is None

    def test_not_found_task(self, client: TestClient) -> None:
        body = client.get("/api/task/999999").json()
        assert body["code"] == 404
        assert "不存在" in body["message"]

    def test_validation_error_empty_domain(self, client: TestClient) -> None:
        """空学习方向应在参数校验阶段被拦下，不会真的去调 AI。"""
        response = client.post(
            "/api/project/match", json={"domain": "", "difficulty": "入门"}
        )
        body = response.json()
        assert body["code"] == 400
        assert "参数校验失败" in body["message"]
        assert body["data"] is None

    def test_validation_error_missing_field(self, client: TestClient) -> None:
        response = client.post("/api/project/match", json={})
        body = response.json()
        assert body["code"] == 400
        assert "参数校验失败" in body["message"]

    def test_validation_error_invalid_difficulty(self, client: TestClient) -> None:
        """难度只允许 入门/初级/中级。"""
        response = client.post(
            "/api/project/match", json={"domain": "React", "difficulty": "地狱级"}
        )
        assert response.json()["code"] == 400

    def test_validation_error_task_status_pattern(self, client: TestClient) -> None:
        """任务状态只允许 todo / in_progress / done。"""
        response = client.patch("/api/task/1", json={"status": "finished"})
        assert response.json()["code"] == 400

    def test_chat_ask_requires_non_empty_question(self, client: TestClient) -> None:
        response = client.post(
            "/api/chat/ask",
            json={"project_id": 1, "scope": "task", "task_id": 1, "question": ""},
        )
        assert response.json()["code"] == 400

    def test_unknown_route_returns_unified_shape(self, client: TestClient) -> None:
        body = client.get("/api/definitely-not-a-route").json()
        assert set(body) == REQUIRED_KEYS
        assert body["code"] != 0


class TestStaticEndpoints:
    """不依赖 AI 的只读接口，保证基础数据可用。"""

    def test_review_guide_has_three_forms(self, client: TestClient) -> None:
        body = client.get("/api/review/guide").json()
        assert body["code"] == 0
        assert len(body["data"]["forms"]) == 3

    def test_review_guide_has_four_questions(self, client: TestClient) -> None:
        body = client.get("/api/review/guide").json()
        assert len(body["data"]["questions"]) == 4

    def test_review_latest_returns_null_when_absent(self, client: TestClient) -> None:
        """未复盘时返回 data=null，前端据此展示引导区。"""
        body = client.get("/api/review/1").json()
        assert body["code"] == 0
        assert body["data"] is None
