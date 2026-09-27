import time
import json
import logging
from typing import Dict, Any, List
from agent.state import AgentState, AgentStepTrace
from config import settings

logger = logging.getLogger(__name__)

# Common follow-up patterns
FOLLOW_UP_INDICATORS = [
    "why did", "why is", "why was", "what about", "now just", "now show",
    "filter by", "only for", "show me only", "compare with", "instead",
    "how about", "break that down", "drill down", "now in", "now for"
]

GREETING_INDICATORS = ["hi", "hello", "hey", "good morning", "good evening", "howdy"]


def heuristic_intent_resolution(query: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fast, deterministic fallback resolver for intent check and multi-turn query disambiguation."""
    q_clean = query.strip().lower()
    q_words = [w.strip("!?,.;:") for w in q_clean.split()]

    if any(w in GREETING_INDICATORS for w in q_words) and len(q_words) <= 3:
        return {
            "intent": "greeting",
            "is_valid_intent": False,
            "resolved_query": query,
            "intent_explanation": "User greeted the system."
        }

    # Off-topic / generic prompt checks
    off_topic_keywords = ["poem", "joke", "who are you", "recipe", "sing a song", "weather in", "system prompt", "ignore instructions"]
    if any(k in q_clean for k in off_topic_keywords):
        return {
            "intent": "off_topic",
            "is_valid_intent": False,
            "resolved_query": query,
            "intent_explanation": "Question is not related to database queries or business metrics."
        }

    # Check for follow-up indicators and pronouns
    pronoun_words = [" their ", " them ", " it ", " those ", " these ", " that ", " its "]
    has_pronouns = any(p in f" {q_clean} " for p in pronoun_words)
    is_followup = any(q_clean.startswith(ind) or ind in q_clean for ind in FOLLOW_UP_INDICATORS) or has_pronouns or q_clean.startswith("now ") or q_clean.startswith("only ")
    
    # If there is history and question is short or has follow-up indicator
    if history and (is_followup or len(q_clean.split()) <= 7):
        # Find last user question and last assistant message
        last_user_q = None
        for msg in reversed(history):
            if msg.get("role") == "user":
                last_user_q = msg.get("content")
                break

        if last_user_q:
            # Check for city filter follow-up
            indian_cities = ["mumbai", "delhi", "bangalore", "bengaluru", "hyderabad", "chennai", "pune", "kolkata", "ahmedabad", "jaipur"]
            matched_city = next((c.capitalize() for c in indian_cities if c in q_clean), None)

            if matched_city:
                resolved = f"{last_user_q.rstrip('?.')} filtered specifically for city = '{matched_city}'."
            elif "august" in q_clean or "why" in q_clean:
                resolved = f"Investigate monthly breakdown and driver causes: {query} (in context of previous query: '{last_user_q}')."
            elif "status" in q_clean or "completed" in q_clean or "pending" in q_clean or "cancelled" in q_clean:
                status_val = "completed" if "completed" in q_clean else ("pending" if "pending" in q_clean else "cancelled")
                resolved = f"{last_user_q.rstrip('?.')} filtered where status = '{status_val}'."
            elif has_pronouns:
                resolved = f"{query} in context of previous question: '{last_user_q}'."
            else:
                resolved = f"{last_user_q.rstrip('.?')} with additional filter/dimension: {query}"
            
            return {
                "intent": "conversational_followup",
                "is_valid_intent": True,
                "resolved_query": resolved,
                "intent_explanation": f"Resolved conversational follow-up using previous question context ('{last_user_q}')."
            }

    return {
        "intent": "data_query",
        "is_valid_intent": True,
        "resolved_query": query,
        "intent_explanation": "Standalone analytical data question."
    }


async def intent_check_node(state: AgentState) -> AgentState:
    """LangGraph node: Classifies query intent and resolves multi-turn conversational context."""
    start_time = time.time()
    query = state.get("query", "").strip()
    history = state.get("conversation_history", [])

    intent_result = None

    # Try fast Groq Llama 3 LLM call if configured
    if settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your_groq_api_key_here":
        try:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)
            
            system_prompt = (
                "You are an intent classifier for an SQL data analyst agent. "
                "Analyze the user's latest query along with conversation history. "
                "Classify intent into one of: 'data_query', 'conversational_followup', 'off_topic', 'greeting'. "
                "If conversational_followup, rewrite into a standalone 'resolved_query' incorporating necessary filters "
                "or metrics from history. Respond strictly in valid JSON with keys: "
                "'intent' (string), 'is_valid_data_intent' (boolean), 'resolved_query' (string), 'explanation' (string)."
            )

            history_context = []
            for h in history[-4:]: # Take last 4 messages
                history_context.append(f"{h.get('role', 'user')}: {h.get('content', '')}")

            user_prompt = f"Conversation History:\n" + ("\n".join(history_context) if history_context else "None")
            user_prompt += f"\n\nCurrent Query: {query}"

            # Candidate Groq models with high reliability and structured output support
            candidate_models = ["qwen/qwen3.8-27b", "openai/gpt-oss-20b", "llama-3.1-8b-instant"]
            parsed = None
            used_model = None

            for m in candidate_models:
                try:
                    completion = client.chat.completions.create(
                        model=m,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.0
                    )
                    raw_content = completion.choices[0].message.content
                    parsed = json.loads(raw_content)
                    used_model = m
                    break
                except Exception as model_err:
                    logger.debug(f"Groq model {m} attempt: {model_err}")
                    continue

            if parsed:
                intent_result = {
                    "intent": parsed.get("intent", "data_query"),
                    "is_valid_intent": parsed.get("is_valid_data_intent", True),
                    "resolved_query": parsed.get("resolved_query", query),
                    "intent_explanation": parsed.get("explanation", f"Classified via Groq ({used_model}).")
                }
        except Exception as e:
            logger.warning(f"Groq intent classification fallback: {e}")

    # Deterministic fallback
    if not intent_result:
        intent_result = heuristic_intent_resolution(query, history)

    duration_ms = round((time.time() - start_time) * 1000, 2)

    trace_step: AgentStepTrace = {
        "step_name": "Intent Check & Context Disambiguation",
        "status": "completed" if intent_result["is_valid_intent"] else "rejected",
        "details": {
            "intent": intent_result["intent"],
            "resolved_query": intent_result["resolved_query"],
            "explanation": intent_result["intent_explanation"]
        },
        "duration_ms": duration_ms
    }

    current_traces = list(state.get("trace_steps", []))
    current_traces.append(trace_step)

    return {
        **state,
        "intent": intent_result["intent"],
        "is_valid_intent": intent_result["is_valid_intent"],
        "resolved_query": intent_result["resolved_query"],
        "intent_explanation": intent_result["intent_explanation"],
        "trace_steps": current_traces
    }
