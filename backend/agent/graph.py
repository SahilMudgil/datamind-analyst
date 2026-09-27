import logging
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END

from agent.state import AgentState
from agent.intent_check import intent_check_node
from agent.schema_linker import schema_linker_node
from agent.sql_generator import sql_generator_node
from agent.safety_validator import safety_validator_node
from agent.executor import execution_node
from agent.self_correction import self_correction_node
from agent.data_analysis import data_analysis_node
from agent.result_explainer import result_explainer_node

logger = logging.getLogger(__name__)


def route_after_intent(state: AgentState) -> Literal["schema_linker", "result_explanation"]:
    """Conditional router: If intent is off-topic or greeting, route directly to explanation."""
    if not state.get("is_valid_intent", True):
        return "result_explanation"
    return "schema_linker"


def route_after_safety(state: AgentState) -> Literal["execution", "self_correction", "result_explanation"]:
    """Conditional router: If SQL failed safety checks, self-correct or exit."""
    is_safe = state.get("is_safe", False)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if is_safe:
        return "execution"
    elif retry_count < max_retries:
        return "self_correction"
    else:
        return "result_explanation"


def route_after_execution(state: AgentState) -> Literal["data_analysis", "self_correction", "result_explanation"]:
    """Conditional router: If execution threw a database error, route to self-correction loop."""
    was_successful = state.get("was_successful", False)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if was_successful:
        return "data_analysis"
    elif retry_count < max_retries:
        return "self_correction"
    else:
        return "result_explanation"


def create_agent_graph():
    """Build and compile the complete multi-step agent pipeline."""
    workflow = StateGraph(AgentState)

    # 1. Register all pipeline nodes
    workflow.add_node("intent_check", intent_check_node)
    workflow.add_node("schema_linker", schema_linker_node)
    workflow.add_node("sql_generator", sql_generator_node)
    workflow.add_node("safety_validator", safety_validator_node)
    workflow.add_node("execution", execution_node)
    workflow.add_node("self_correction", self_correction_node)
    workflow.add_node("data_analysis", data_analysis_node)
    workflow.add_node("result_explanation", result_explainer_node)

    # 2. Wire edges and conditional routing
    workflow.add_edge(START, "intent_check")

    workflow.add_conditional_edges(
        "intent_check",
        route_after_intent,
        {
            "schema_linker": "schema_linker",
            "result_explanation": "result_explanation"
        }
    )

    workflow.add_edge("schema_linker", "sql_generator")
    workflow.add_edge("sql_generator", "safety_validator")

    workflow.add_conditional_edges(
        "safety_validator",
        route_after_safety,
        {
            "execution": "execution",
            "self_correction": "self_correction",
            "result_explanation": "result_explanation"
        }
    )

    workflow.add_conditional_edges(
        "execution",
        route_after_execution,
        {
            "data_analysis": "data_analysis",
            "self_correction": "self_correction",
            "result_explanation": "result_explanation"
        }
    )

    # Self-correction loop: feeds back into sql_generator
    workflow.add_edge("self_correction", "sql_generator")

    # Analysis -> Explanation -> End
    workflow.add_edge("data_analysis", "result_explanation")
    workflow.add_edge("result_explanation", END)

    return workflow.compile()


# Compiled agent pipeline instance
agent_pipeline = create_agent_graph()
