"""LLM 输出容错解析测试。

`extract_json` 是 AI 链路里最容易被改坏的纯函数：每加一层兜底，
都可能让前面的分支失效。这里逐个锁定五种容错路径。
"""

import pytest

from app.services.llm_service import extract_json
from app.utils.response import BusinessError


class TestExtractJson:
    """五种兜底策略 + 异常路径。"""

    def test_plain_object(self) -> None:
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_plain_array(self) -> None:
        assert extract_json('[1, 2, 3]') == [1, 2, 3]

    def test_markdown_fenced_with_language(self) -> None:
        """模型最常见的输出形式：套一层 ```json 代码块。"""
        assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_markdown_fenced_without_language(self) -> None:
        assert extract_json('```\n{"a": 1}\n```') == {"a": 1}

    def test_wrapped_in_prose(self) -> None:
        """前后带解释文字时，应截取最外层括号。"""
        raw = "好的，结果如下：\n{\"projects\": []}\n希望有帮助。"
        assert extract_json(raw) == {"projects": []}

    def test_array_wrapped_in_prose(self) -> None:
        assert extract_json("结果：\n[1, 2]\n完毕") == [1, 2]

    def test_trailing_comma(self) -> None:
        assert extract_json('{"a": [1, 2,], "b": 3,}') == {"a": [1, 2], "b": 3}

    def test_raw_newline_inside_string(self) -> None:
        """模型偶尔在 JSON 字符串里输出未转义的裸换行。"""
        assert extract_json('{"doc": "第一行\n第二行"}') == {"doc": "第一行\n第二行"}

    def test_raw_tab_inside_string(self) -> None:
        assert extract_json('{"doc": "a\tb"}') == {"doc": "a\tb"}

    def test_structural_newlines_are_preserved(self) -> None:
        """字符串外的换行是 JSON 的结构性空白，不能被转义，否则会破坏文档。

        本用例同时包含「结构性换行」和「字符串内裸换行」，
        是 _escape_control_chars 最容易写错的地方。
        """
        raw = '{\n  "doc": "第一行\n第二行",\n  "n": 1\n}'
        assert extract_json(raw) == {"doc": "第一行\n第二行", "n": 1}

    def test_existing_escape_sequences_not_double_escaped(self) -> None:
        """已经是 \\n 的转义序列不能被二次转义成 \\\\n。"""
        assert extract_json('{"doc": "a\\nb"}') == {"doc": "a\nb"}

    def test_nested_structure_preserved(self) -> None:
        raw = '```json\n{"stages": [{"name": "阶段一", "tasks": [{"name": "A"}]}]}\n```'
        result = extract_json(raw)
        assert result["stages"][0]["tasks"][0]["name"] == "A"

    def test_empty_string_raises(self) -> None:
        with pytest.raises(BusinessError):
            extract_json("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(BusinessError):
            extract_json("   \n\t  ")

    def test_non_json_text_raises(self) -> None:
        with pytest.raises(BusinessError):
            extract_json("这完全不是 JSON，只是一段说明文字")

    def test_truncated_json_raises(self) -> None:
        """被 max_tokens 截断的输出应报错，而不是返回半个对象。"""
        with pytest.raises(BusinessError):
            extract_json('{"a": 1, "b": [1, 2')
