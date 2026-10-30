"""Compile exactly the two Day14 nodes with explicit conditional entry."""

from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.app.agent.nodes import create_generate_node, create_retrieve_node
from backend.app.agent.state import AgentContext, AgentState
from backend.app.core.config import RAGSettings
from backend.app.services.llm import LLMClient
from backend.app.services.rag import RAGGraphError
from backend.app.services.reranker import RerankedRetrievalService

CompiledRAGGraph = CompiledStateGraph[
    AgentState, AgentContext, AgentState, AgentState
]


def route_retrieval(
    state: AgentState,
) -> Literal["retrieve_node", "generate_node"]:
    """Public inputs are True; only an internal prepared State may skip retrieval."""
    if type(state.get("needs_retrieval")) is not bool:
        raise RAGGraphError("The RAG graph retrieval flag is invalid.")
    return "retrieve_node" if state["needs_retrieval"] else "generate_node"


def build_rag_graph(
    retrieval_service: RerankedRetrievalService,
    llm_client: LLMClient,
    settings: RAGSettings,
) -> CompiledRAGGraph:
    """Compile lazy service closures without calling any external dependency."""
    builder = StateGraph(AgentState, context_schema=AgentContext)
    builder.add_node("retrieve_node", create_retrieve_node(retrieval_service, settings))
    builder.add_node("generate_node", create_generate_node(llm_client))
    builder.add_conditional_edges(
        START, route_retrieval,
        {"retrieve_node": "retrieve_node", "generate_node": "generate_node"},
    )
    builder.add_edge("retrieve_node", "generate_node")
    builder.add_edge("generate_node", END)
    return builder.compile()
