"""Streamlit rerun and turn isolation tests."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest

pytest.importorskip("streamlit")
import streamlit as st
from streamlit.testing.v1 import AppTest

from frontend import api_client
from frontend.api_client import ApiError
from frontend.models import ChatCompletion, DocumentItem, DocumentList, SourceRef
from frontend.sse import StreamInterrupted

_APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
_SESSION_ID = UUID(int=1)


class FakeRagClient:
    def __init__(self) -> None:
        self.questions: list[tuple[str, UUID | None]] = []
        self.list_requests = 0
        self.uploads = 0

    def list_documents(self) -> DocumentList:
        self.list_requests += 1
        if self.uploads:
            raise ApiError("outage")
        return DocumentList((), False)

    def upload_document(self, filename: str, file: BytesIO) -> DocumentItem:
        assert file.read() == b"hello"
        self.uploads += 1
        return DocumentItem(UUID(int=2), filename, 5, "ready", datetime.now(timezone.utc))

    def stream_chat(self, message: str, session_id: UUID | None) -> Iterator[str | ChatCompletion]:
        self.questions.append((message, session_id))
        yield "正文第一段"
        if message == "断流":
            raise StreamInterrupted("本轮未确认，后端可能已保存本轮。")
        yield "，正文第二段"
        if message == "文档列表":
            yield ChatCompletion(_SESSION_ID, (), "list_documents")
        else:
            yield ChatCompletion(_SESSION_ID, (SourceRef("指南.pdf", 2),), "search_knowledge_base")


@pytest.fixture
def ui(monkeypatch: pytest.MonkeyPatch) -> tuple[AppTest, FakeRagClient]:
    client = FakeRagClient()

    @contextmanager
    def open_fake_client() -> Iterator[FakeRagClient]:
        yield client

    monkeypatch.setattr(api_client, "open_client", open_fake_client)
    return AppTest.from_file(str(_APP_PATH)), client


def submit(app: AppTest, question: str) -> None:
    app.chat_input[0].set_value(question).run()
    assert not app.exception


def test_rerun_session_reuse_empty_sources_and_new_chat(ui: tuple[AppTest, FakeRagClient]) -> None:
    app, client = ui
    app.run()
    submit(app, "查指南")
    assert "指南.pdf · 第 2 页" in [entry.value for entry in app.text]
    assert "search_knowledge_base" in [entry.value for entry in app.text]
    app.run()
    assert client.questions == [("查指南", None)] and client.list_requests == 1

    submit(app, "文档列表")
    assert client.questions[-1] == ("文档列表", _SESSION_ID)
    assert "指南.pdf · 第 2 页" not in [entry.value for entry in app.text]
    assert "list_documents" in [entry.value for entry in app.text]
    assert "本轮无引用。" in [entry.value for entry in app.caption]

    next(button for button in app.button if button.label == "新建对话").click().run()
    assert not app.session_state.ui.turns and app.session_state.ui.session_id is None
    submit(app, "新的问题")
    assert client.questions[-1] == ("新的问题", None)


def test_interrupted_turn_hides_old_sources_and_is_never_replayed(ui: tuple[AppTest, FakeRagClient]) -> None:
    app, client = ui
    app.run()
    submit(app, "查指南")
    submit(app, "断流")
    turn = app.session_state.ui.turns[-1]
    assert turn.status == "interrupted" and turn.answer == "正文第一段"
    assert app.session_state.ui.session_id == _SESSION_ID
    assert "指南.pdf · 第 2 页" not in [entry.value for entry in app.text]

    turn.status = "streaming"
    app.run()
    assert not app.exception
    assert turn.status == "interrupted" and len(client.questions) == 2


def test_upload_success_survives_list_refresh_failure_without_another_post(
    ui: tuple[AppTest, FakeRagClient], monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client = ui

    class Uploaded(BytesIO):
        name = "政策.txt"
        type = "text/plain"

    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: Uploaded(b"hello"))
    app.run()
    assert client.uploads == 0
    next(button for button in app.button if button.label == "上传文件").click().run()
    assert not app.exception
    assert client.uploads == 1 and client.list_requests == 2
    assert any("向量索引需单独执行" in entry.value for entry in app.success)
    assert any("列表暂不可用" in entry.value for entry in app.warning)
    app.run()
    assert client.uploads == 1
