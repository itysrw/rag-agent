"""One tool selection, one execution, then generation; no loops or persistence."""

from collections.abc import Callable
from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.app.agent.nodes import create_generate_node, create_rewrite_query_node, create_select_tool_node, create_tool_node
from backend.app.agent.state import AgentContext, AgentState
from backend.app.agent.tools import AgentTools
from backend.app.core.config import ConversationMemorySettings, RAGSettings
from backend.app.services.llm import LLMClient
from backend.app.services.rag import RAGGraphError
from backend.app.services.reranker import RerankedRetrievalService
from backend.app.services.document_catalog import DocumentCatalogService, get_document_catalog_service

CompiledRAGGraph = CompiledStateGraph[
    AgentState, AgentContext, AgentState, AgentState
]


def route_tool_selection(
    state: AgentState,
) -> Literal["rewrite_query_node", "select_tool_node", "generate_node"]:
    """Only the internal PreparedRAG path can skip tool selection."""
    if (type(state.get("needs_tool_selection")) is not bool
            or type(state.get("needs_query_rewrite")) is not bool):
        raise RAGGraphError("The RAG graph tool selection flag is invalid.")
    if state["needs_query_rewrite"]:
        if not state["needs_tool_selection"]:
            raise RAGGraphError("The RAG graph rewrite state is invalid.")
        return "rewrite_query_node"
    return "select_tool_node" if state["needs_tool_selection"] else "generate_node"


def build_rag_graph(
    retrieval_service: RerankedRetrievalService,
    llm_client: LLMClient,
    settings: RAGSettings,
    *,
    catalog_factory: Callable[[], DocumentCatalogService] = get_document_catalog_service,
    memory_settings: ConversationMemorySettings | None = None,
) -> CompiledRAGGraph:
    """Compile lazy service closures without calling any external dependency."""
    builder = StateGraph(AgentState, context_schema=AgentContext)
    tools = AgentTools(retrieval_service, settings, catalog_factory=catalog_factory)
    builder.add_node("rewrite_query_node", create_rewrite_query_node(
        llm_client, memory_settings or ConversationMemorySettings(_env_file=None),
    ))
    builder.add_node("select_tool_node", create_select_tool_node(llm_client))
    builder.add_node("tool_node", create_tool_node(tools))
    builder.add_node("generate_node", create_generate_node(llm_client))
    builder.add_conditional_edges(
        START, route_tool_selection,
        {"rewrite_query_node": "rewrite_query_node", "select_tool_node": "select_tool_node",
         "generate_node": "generate_node"},
    )
    builder.add_edge("rewrite_query_node", "select_tool_node")
    builder.add_edge("select_tool_node", "tool_node")
    builder.add_edge("tool_node", "generate_node")
    builder.add_edge("generate_node", END)
    return builder.compile()
