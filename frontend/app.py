"""Local Streamlit knowledge-base interface."""

import streamlit as st

from backend.app.document_formats import UPLOAD_CONTENT_TYPES
from frontend.api_client import ApiError, RagClient, open_client
from frontend.models import TOOL_LABELS, ChatCompletion, ChatTurn, UiSession
from frontend.sse import StreamError, StreamInterrupted


def _refresh_catalog(client: RagClient, state: UiSession) -> None:
    try:
        state.catalog = client.list_documents()
    except ApiError:
        state.catalog = None
        state.catalog_unavailable = True
    else:
        state.catalog_unavailable = False


def _documents(client: RagClient, state: UiSession) -> None:
    st.header("文档")
    refresh = st.button("刷新列表", key="refresh_documents")
    if refresh or (state.catalog is None and not state.catalog_unavailable):
        with st.spinner("正在加载文档…"):
            _refresh_catalog(client, state)
    if state.catalog_unavailable:
        st.warning("文档列表暂不可用，请手动刷新。")
    elif state.catalog is not None:
        if state.catalog.truncated:
            st.caption("仅显示最近 50 份文档。")
        if not state.catalog.documents:
            st.caption("暂无已解析文档。")
        if state.catalog.documents:
            with st.container(height=210, border=True):
                for document in state.catalog.documents:
                    st.text(document.filename)

    st.subheader("上传")
    file = st.file_uploader(
        "选择 .pdf、.md 或 .txt 文件",
        type=[extension[1:] for extension in UPLOAD_CONTENT_TYPES],
        help="后端默认上限为 20 MiB。",
        key=f"upload_file_{state.uploader_version}",
    )
    if st.button("上传文件", disabled=file is None) and file is not None:
        state.uploaded = None
        state.upload_error = ""
        file.seek(0)
        try:
            with st.spinner("正在上传并解析…"):
                state.uploaded = client.upload_document(file.name, file)
        except ApiError as exc:
            state.upload_error = str(exc)
        else:
            state.uploader_version += 1
            state.catalog = None
            state.catalog_unavailable = False
            st.rerun()
    if state.uploaded is not None:
        st.success("已上传并解析，向量索引需单独执行。")
        st.text(f"{state.uploaded.filename}\nID {state.uploaded.id}")
    if state.upload_error:
        st.error(state.upload_error)


def _tool_panel(turn: ChatTurn | None) -> None:
    if turn is None:
        st.caption("完成提问后显示本轮工具。")
    elif turn.status == "complete":
        name = turn.tool_name
        st.text(TOOL_LABELS[name] if name in TOOL_LABELS else "后端未提供")
        if name in TOOL_LABELS:
            st.text(name)
    elif turn.status == "streaming":
        st.caption("等待本轮完成。")
    else:
        st.caption("本轮未确认。")


def _sources_panel(turn: ChatTurn | None) -> None:
    if turn is None:
        st.caption("完成提问后显示来源。")
    elif turn.status == "complete":
        if not turn.sources:
            st.caption("本轮无引用。")
        for source in turn.sources:
            st.text(f"{source.filename} · 第 {source.page} 页")
    elif turn.status == "streaming":
        st.caption("等待本轮完成。")
    else:
        st.caption("本轮未确认。")


def _show_turn(turn: ChatTurn) -> None:
    with st.chat_message("user"):
        st.text(turn.question)
    with st.chat_message("assistant"):
        if turn.answer:
            st.text(turn.answer)
        if turn.status != "complete":
            st.warning(turn.error or "本轮未确认。")


def _stream_turn(client: RagClient, state: UiSession, turn: ChatTurn) -> None:
    with st.chat_message("user"):
        st.text(turn.question)
    with st.chat_message("assistant"):
        output = st.empty()
        output.caption("正在等待回答…")
        try:
            for event in client.stream_chat(turn.question, state.session_id):
                if isinstance(event, ChatCompletion):
                    state.session_id = event.session_id
                    turn.sources = event.sources
                    turn.tool_name = event.tool_name
                    turn.status = "complete"
                else:
                    turn.answer += event
                    output.text(turn.answer)
        except StreamInterrupted as exc:
            turn.status, turn.error = "interrupted", str(exc)
        except (ApiError, StreamError) as exc:
            turn.status, turn.error = "error", str(exc)
        if turn.status == "streaming":
            turn.status, turn.error = "interrupted", "本轮未收到完成确认。"


def main() -> None:
    st.set_page_config(page_title="知识库问答", layout="wide", initial_sidebar_state="expanded")
    if "ui" not in st.session_state:
        st.session_state.ui = UiSession()
    state: UiSession = st.session_state.ui
    if state.turns and state.turns[-1].status == "streaming":
        abandoned = state.turns[-1]
        abandoned.status = "interrupted"
        abandoned.error = "页面在本轮确认前刷新，后端可能已保存本轮。"
    with open_client() as client:
        with st.sidebar:
            if st.button("新建对话"):
                state.turns.clear()
                state.session_id = None
            _documents(client, state)
            st.divider()
            st.subheader("本轮工具")
            tool_panel = st.empty()

        center, right = st.columns([3, 1], gap="large")
        with center:
            st.title("知识库问答")
            for turn in state.turns:
                _show_turn(turn)
            question = st.chat_input("输入关于知识库的问题", max_chars=4096)
        with right:
            st.header("本轮引用")
            sources_panel = st.empty()

        new_turn = ChatTurn(question.strip()) if question and question.strip() else None
        if new_turn is not None:
            state.turns.append(new_turn)
        latest = state.turns[-1] if state.turns else None
        with tool_panel.container():
            _tool_panel(latest)
        with sources_panel.container():
            _sources_panel(latest)
        if new_turn is not None:
            with center:
                _stream_turn(client, state, new_turn)
            st.rerun()


if __name__ == "__main__":
    main()
