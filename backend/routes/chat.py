import json
import time
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from database import get_db, SessionLocal
from models.models import User, Conversation, Message, AgentStep, DatabaseConnection
from services.auth_service import get_current_user
from jose import jwt, JWTError
from config import settings
from agent.graph import agent_pipeline
from agent.state import AgentState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat & Conversations"])

# Pydantic Schemas
class ConversationCreateSchema(BaseModel):
    connection_id: int
    title: Optional[str] = "New Analysis"

class ConversationResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    connection_id: int
    title: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class MessageResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    role: str
    content: Optional[str] = None
    final_sql: Optional[str] = None
    query_result: Optional[List[Dict[str, Any]]] = None
    analysis_result: Optional[Dict[str, Any]] = None
    chart_type: Optional[str] = None
    chart_config: Optional[Dict[str, Any]] = None
    was_successful: Optional[bool] = True
    total_latency_ms: Optional[int] = None
    is_cached: Optional[bool] = False
    created_at: Optional[datetime] = None

class QueryRequestSchema(BaseModel):
    connection_id: int
    query: str
    conversation_id: Optional[int] = None


# --- REST Endpoints ---

@router.post("/conversations", response_model=ConversationResponseSchema, status_code=status.HTTP_201_CREATED)
def create_conversation(
    data: ConversationCreateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversational session associated with a database connection."""
    conn = db.query(DatabaseConnection).filter(
        DatabaseConnection.id == data.connection_id,
        DatabaseConnection.user_id == current_user.id
    ).first()
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Database connection not found.")

    new_conv = Conversation(
        user_id=current_user.id,
        connection_id=data.connection_id,
        title=data.title or "New Analysis"
    )
    db.add(new_conv)
    db.commit()
    db.refresh(new_conv)
    return ConversationResponseSchema.model_validate(new_conv)


@router.get("/conversations", response_model=List[ConversationResponseSchema])
def list_conversations(
    connection_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List conversational sessions for the current user."""
    query = db.query(Conversation).filter(Conversation.user_id == current_user.id)
    if connection_id:
        query = query.filter(Conversation.connection_id == connection_id)
    convs = query.order_by(Conversation.updated_at.desc()).all()
    return [ConversationResponseSchema.model_validate(c) for c in convs]


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponseSchema])
def get_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch message history for a specific conversation."""
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()
    return [MessageResponseSchema.model_validate(m) for m in messages]


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_200_OK)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversational session and all its associated messages."""
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    db.delete(conv)
    db.commit()
    return {"message": "Conversation deleted successfully", "id": conversation_id}


@router.post("/query", response_model=MessageResponseSchema)
async def execute_query_rest(
    req: QueryRequestSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """HTTP REST fallback endpoint to execute a query through the LangGraph pipeline."""
    start_time = time.time()

    # 1. Get or create conversation
    conv_id = req.conversation_id
    if not conv_id:
        new_conv = Conversation(
            user_id=current_user.id,
            connection_id=req.connection_id,
            title=req.query[:40] + ("..." if len(req.query) > 40 else "")
        )
        db.add(new_conv)
        db.commit()
        db.refresh(new_conv)
        conv_id = new_conv.id

    # 2. Fetch conversation history for multi-turn context
    history_records = db.query(Message).filter(
        Message.conversation_id == conv_id
    ).order_by(Message.created_at.asc()).limit(10).all()

    conv_history = [
        {"role": h.role, "content": h.content or ""}
        for h in history_records
    ]

    # Save user message
    user_msg = Message(
        conversation_id=conv_id,
        role="user",
        content=req.query
    )
    db.add(user_msg)
    db.commit()

    # 3. Run through LangGraph pipeline
    initial_state: AgentState = {
        "query": req.query,
        "connection_id": req.connection_id,
        "conversation_id": conv_id,
        "conversation_history": conv_history,
        "max_retries": 2,
        "retry_count": 0,
        "trace_steps": [],
        "db": db
    }

    final_state = await agent_pipeline.ainvoke(initial_state)
    total_latency_ms = int((time.time() - start_time) * 1000)

    # 4. Save assistant response
    assistant_msg = Message(
        conversation_id=conv_id,
        role="assistant",
        content=final_state.get("result_explanation") or "Analysis completed.",
        final_sql=final_state.get("sanitized_sql") or final_state.get("generated_sql"),
        query_result=final_state.get("query_result"),
        analysis_result=final_state.get("analysis_result"),
        chart_type=final_state.get("chart_type"),
        chart_config=final_state.get("chart_config"),
        was_successful=final_state.get("was_successful", True),
        total_latency_ms=total_latency_ms
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    # 5. Persist agent steps
    trace_steps = final_state.get("trace_steps", [])
    for idx, step in enumerate(trace_steps, start=1):
        agent_step_record = AgentStep(
            message_id=assistant_msg.id,
            step_number=idx,
            step_type=str(step.get("step_name", "step"))[:250],
            output_data=step.get("details"),
            latency_ms=int(step.get("duration_ms", 0))
        )
        db.add(agent_step_record)
    # 6. Save to semantic query cache if successful and not cached
    if assistant_msg.was_successful and assistant_msg.final_sql and not final_state.get("is_cached"):
        try:
            from services.query_cache_service import query_cache_service
            await query_cache_service.save_cached_query(
                connection_id=req.connection_id,
                question_text=req.query,
                generated_sql=assistant_msg.final_sql,
                db=db
            )
        except Exception:
            pass

    # 7. Log LLM usage
    try:
        from services.llm_tracking_service import llm_tracking_service
        in_tok = llm_tracking_service.estimate_tokens(req.query)
        out_tok = llm_tracking_service.estimate_tokens(assistant_msg.content or "")
        llm_tracking_service.log_usage(
            db=db,
            user_id=current_user.id,
            provider="gemini" if not final_state.get("is_cached") else "cache",
            model_used="gemini-2.5-flash" if not final_state.get("is_cached") else "semantic-cache",
            step_type="sql_generation",
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=total_latency_ms,
            message_id=assistant_msg.id
        )
    except Exception:
        pass

    resp_dict = MessageResponseSchema.model_validate(assistant_msg).model_dump()
    resp_dict["is_cached"] = bool(final_state.get("is_cached", False))
    return MessageResponseSchema(**resp_dict)


# --- WebSocket Streaming Endpoint ---

async def authenticate_ws_token(token: str, db: Session) -> Optional[User]:
    """Validate JWT token passed in WebSocket connection."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            return None
        return db.query(User).filter(User.email == email).first()
    except (JWTError, Exception):
        return None

@router.websocket("/ws")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Live streaming WebSocket endpoint for step-by-step agent execution."""
    await websocket.accept()

    try:
        # Authenticate connection
        user = None
        if token:
            user = await authenticate_ws_token(token, db)

        if not user:
            # Wait for first auth message if token wasn't in query params
            auth_msg = await websocket.receive_text()
            data = json.loads(auth_msg)
            msg_token = data.get("token")
            user = await authenticate_ws_token(msg_token, db) if msg_token else None

        if not user:
            await websocket.send_json({"type": "error", "message": "Authentication failed"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Connected message
        await websocket.send_json({"type": "connected", "message": f"Connected as {user.email}"})

        # Main message processing loop
        while True:
            raw_msg = await websocket.receive_text()
            payload = json.loads(raw_msg)
            query_text = payload.get("query")
            connection_id = payload.get("connection_id")
            conv_id = payload.get("conversation_id")

            if not query_text or not connection_id:
                await websocket.send_json({"type": "error", "message": "query and connection_id are required"})
                continue

            start_time = time.time()

            # Ensure conversation exists
            if not conv_id:
                new_conv = Conversation(
                    user_id=user.id,
                    connection_id=connection_id,
                    title=query_text[:40] + ("..." if len(query_text) > 40 else "")
                )
                db.add(new_conv)
                db.commit()
                db.refresh(new_conv)
                conv_id = new_conv.id
                await websocket.send_json({
                    "type": "conversation_created",
                    "conversation_id": conv_id,
                    "title": new_conv.title
                })

            # Save user message
            user_msg = Message(conversation_id=conv_id, role="user", content=query_text)
            db.add(user_msg)
            db.commit()

            # Notify client query received
            await websocket.send_json({"type": "query_start", "query": query_text, "conversation_id": conv_id})

            # Fetch conversation history for context
            history_records = db.query(Message).filter(
                Message.conversation_id == conv_id
            ).order_by(Message.created_at.asc()).limit(10).all()

            conv_history = [{"role": h.role, "content": h.content or ""} for h in history_records]

            # Prepare initial state
            initial_state: AgentState = {
                "query": query_text,
                "connection_id": connection_id,
                "conversation_id": conv_id,
                "conversation_history": conv_history,
                "max_retries": 2,
                "retry_count": 0,
                "trace_steps": [],
                "db": db
            }

            # Run LangGraph pipeline with step streaming
            # LangGraph astream streams updates as each node finishes
            streamed_state: Dict[str, Any] = {}
            try:
                async for chunk in agent_pipeline.astream(initial_state):
                    for node_name, node_output in chunk.items():
                        streamed_state.update(node_output)
                        # Stream live step event to client
                        try:
                            trace = node_output.get("trace_steps", [])[-1] if node_output.get("trace_steps") else {}
                            await websocket.send_json(jsonable_encoder({
                                "type": "step_complete",
                                "step_name": node_name,
                                "details": trace.get("details", {}),
                                "duration_ms": trace.get("duration_ms", 0)
                            }))
                        except Exception as step_err:
                            logger.warning(f"Failed to stream step event: {step_err}")

                total_latency_ms = int((time.time() - start_time) * 1000)

                # Persist assistant message
                assistant_msg = Message(
                    conversation_id=conv_id,
                    role="assistant",
                    content=streamed_state.get("result_explanation") or "Analysis completed.",
                    final_sql=streamed_state.get("sanitized_sql") or streamed_state.get("generated_sql"),
                    query_result=streamed_state.get("query_result"),
                    analysis_result=streamed_state.get("analysis_result"),
                    chart_type=streamed_state.get("chart_type"),
                    chart_config=streamed_state.get("chart_config"),
                    was_successful=streamed_state.get("was_successful", True),
                    total_latency_ms=total_latency_ms
                )
                db.add(assistant_msg)
                db.commit()
                db.refresh(assistant_msg)

                # Persist agent steps audit trail
                for idx, step in enumerate(streamed_state.get("trace_steps", []), start=1):
                    agent_step_record = AgentStep(
                        message_id=assistant_msg.id,
                        step_number=idx,
                        step_type=str(step.get("step_name", "step"))[:250],
                        output_data=step.get("details"),
                        latency_ms=int(step.get("duration_ms", 0))
                    )
                    db.add(agent_step_record)
                db.commit()

                # Save to semantic query cache if successful and not cached
                if assistant_msg.was_successful and assistant_msg.final_sql and not streamed_state.get("is_cached"):
                    try:
                        from services.query_cache_service import query_cache_service
                        await query_cache_service.save_cached_query(
                            connection_id=connection_id,
                            question_text=query_text,
                            generated_sql=assistant_msg.final_sql,
                            db=db
                        )
                    except Exception:
                        pass

                # Log LLM usage
                try:
                    from services.llm_tracking_service import llm_tracking_service
                    in_tok = llm_tracking_service.estimate_tokens(query_text)
                    out_tok = llm_tracking_service.estimate_tokens(assistant_msg.content or "")
                    llm_tracking_service.log_usage(
                        db=db,
                        user_id=user.id,
                        provider="gemini" if not streamed_state.get("is_cached") else "cache",
                        model_used="gemini-2.5-flash" if not streamed_state.get("is_cached") else "semantic-cache",
                        step_type="sql_generation",
                        input_tokens=in_tok,
                        output_tokens=out_tok,
                        latency_ms=total_latency_ms,
                        message_id=assistant_msg.id
                    )
                except Exception:
                    pass

                # Send final response payload safely using jsonable_encoder
                await websocket.send_json(jsonable_encoder({
                    "type": "final_result",
                    "message_id": assistant_msg.id,
                    "conversation_id": conv_id,
                    "content": assistant_msg.content,
                    "final_sql": assistant_msg.final_sql,
                    "query_result": assistant_msg.query_result,
                    "analysis_result": assistant_msg.analysis_result,
                    "chart_type": assistant_msg.chart_type,
                    "chart_config": assistant_msg.chart_config,
                    "was_successful": assistant_msg.was_successful,
                    "total_latency_ms": total_latency_ms,
                    "is_cached": bool(streamed_state.get("is_cached", False)),
                    "trace_steps": streamed_state.get("trace_steps", [])
                }))
            except Exception as stream_err:
                logger.error(f"Error executing agent pipeline: {stream_err}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Pipeline error: {str(stream_err)}"
                })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
