"""Unit tests for ResumeParserAgent.parse_response output sanitization."""
import pytest

from app.agents.resume_parser import ResumeParserAgent
from app.models.errors import APIError
from app.services.nvidia_nim_mock import MockNimClient

_MINIMAL = '{"personal": {"name": "Jane", "email": "jane@example.com"}}'


def _agent() -> ResumeParserAgent:
    return ResumeParserAgent(nim_client=MockNimClient())


class TestParseResponse:
    def test_plain_json(self):
        assert _agent().parse_response(_MINIMAL)["personal"]["name"] == "Jane"

    def test_markdown_fenced(self):
        raw = f"```json\n{_MINIMAL}\n```"
        assert _agent().parse_response(raw)["personal"]["email"] == "jane@example.com"

    def test_prose_wrapped(self):
        raw = f"Here is the extracted profile:\n{_MINIMAL}\nLet me know if you need changes."
        assert _agent().parse_response(raw)["personal"]["name"] == "Jane"

    def test_trailing_commas(self):
        # The exact failure observed in production: trailing comma before a brace.
        raw = (
            '{"personal": {"name": "Jane", "email": "jane@example.com",},'
            ' "education": [{"id": "edu_1", "degree": "MS",},],}'
        )
        data = _agent().parse_response(raw)
        assert data["personal"]["name"] == "Jane"
        assert data["education"][0]["id"] == "edu_1"

    def test_fenced_with_trailing_commas(self):
        raw = '```json\n{"personal": {"name": "Jane", "email": "j@x.com",},}\n```'
        assert _agent().parse_response(raw)["personal"]["email"] == "j@x.com"

    def test_garbage_raises(self):
        with pytest.raises(APIError):
            _agent().parse_response("not json at all")

    def test_missing_personal_raises(self):
        with pytest.raises(APIError):
            _agent().parse_response('{"education": []}')
