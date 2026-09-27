from typing import TypedDict, List, Dict, Any, Optional

class AgentStepTrace(TypedDict, total=False):
    step_name: str
    status: str # 'started' | 'completed' | 'failed' | 'skipped'
    details: Dict[str, Any]
    duration_ms: float

class AgentState(TypedDict, total=False):
    # Inputs
    query: str
    connection_id: int
    conversation_id: Optional[int]
    conversation_history: List[Dict[str, Any]]
    db: Optional[Any]
    target_engine: Optional[Any]
    
    # Step 1: Intent Check & Query Resolution
    intent: str # 'data_query' | 'conversational_followup' | 'off_topic' | 'greeting'
    is_valid_intent: bool
    resolved_query: str
    intent_explanation: Optional[str]
    
    # Step 2: Schema Linking
    relevant_tables: List[str]
    relevant_columns: List[Dict[str, Any]]
    schema_prompt: str
    
    # Step 3: SQL Generation
    generated_sql: Optional[str]
    sql_explanation: Optional[str]
    
    # Step 4: Safety Validation
    is_safe: bool
    safety_violations: List[str]
    sanitized_sql: Optional[str]
    
    # Execution & Retry Control
    retry_count: int
    max_retries: int
    error_message: Optional[str]
    retry_hint: Optional[str]
    retry_history: List[Dict[str, Any]]

    # Step 5: Execution Result
    query_result: Optional[List[Dict[str, Any]]]
    column_names: Optional[List[str]]
    row_count: Optional[int]
    execution_error: Optional[str]
    was_successful: Optional[bool]

    # Step 7: Data Analysis Layer
    analysis_result: Optional[Dict[str, Any]]

    # Step 8: Chart Selection
    chart_type: Optional[str] # 'bar' | 'line' | 'pie' | 'stat_card'
    chart_config: Optional[Dict[str, Any]]

    # Step 9: Result Explanation
    result_explanation: Optional[str]
    
    # Step Trace for live frontend streaming
    trace_steps: List[AgentStepTrace]

    # Semantic Cache & Cost Tracking
    is_cached: Optional[bool]
    cached_similarity: Optional[float]
    total_tokens: Optional[int]
    estimated_cost: Optional[float]
