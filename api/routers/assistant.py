# api/routers/assistant.py
"""
Phase 5: Natural Language Scheduling Assistant API

Routes:
  POST /api/assistant/chat   — Send a message, get a structured response
  GET  /api/assistant/prompts — Get suggested starter prompts
"""
from fastapi import APIRouter, Depends

from api.schemas import AssistantChatRequest, AssistantChatResponse, AssistantToolCall
from core.logger import logger
from core.security import get_current_user

router = APIRouter(prefix="/api/assistant", tags=["AI Assistant"])


STARTER_PROMPTS = [
    "What's the makespan of my latest run?",
    "Which machine has the worst utilization?",
    "Show me all late jobs",
    "Are there any active maintenance alerts?",
    "Compare algorithm performance",
    "Show me recent schedule runs",
    "Give me a system overview",
]


@router.post(
    "/chat",
    response_model=AssistantChatResponse,
    summary="Chat with the scheduling assistant",
    description=(
        "Send a natural language question about your schedules, machines, "
        "alerts, or system health. The assistant uses rule-based intent matching "
        "backed by live database queries."
    ),
)
def chat(
    body: AssistantChatRequest,
    _current_user=Depends(get_current_user),
) -> AssistantChatResponse:
    from assistant.agent import run_agent

    logger.debug("Assistant query: {}", body.message[:120])
    history = [m.model_dump() for m in body.history[-10:]]  # cap at 10 turns
    result = run_agent(body.message, history=history)

    return AssistantChatResponse(
        reply=result["reply"],
        tool_calls=[AssistantToolCall(**tc) for tc in result["tool_calls"]],
        suggested_prompts=result["suggested_prompts"],
    )


@router.get(
    "/prompts",
    response_model=list[str],
    summary="Get suggested starter prompts",
)
def get_starter_prompts(
    _current_user=Depends(get_current_user),
) -> list[str]:
    """Return a list of suggested questions the user can ask the assistant."""
    return STARTER_PROMPTS
