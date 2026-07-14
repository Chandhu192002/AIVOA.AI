"""POST /api/chat — one turn of the AI Assistant conversation."""
from fastapi import APIRouter, HTTPException
from langchain_core.messages import AIMessage, HumanMessage

from ..agent.graph import get_graph
from ..schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    # Rebuild the conversation for the agent (short history keeps context for
    # follow-up corrections like "sorry, the name was actually Dr. John").
    messages = []
    for item in req.history[-12:]:
        if item.role == "user":
            messages.append(HumanMessage(content=item.content))
        else:
            messages.append(AIMessage(content=item.content))
    messages.append(HumanMessage(content=req.message))

    initial_state = {
        "messages": messages,
        "form_state": req.form_state or {},
        "form_updates": {},
        "suggested_followups": [],
        "interaction_id": req.interaction_id,
        "model_used": "",
    }

    try:
        result = get_graph().invoke(initial_state, config={"recursion_limit": 12})
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent error: {exc}") from exc

    reply = ""
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            reply = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    tool_calls = [
        call["name"]
        for msg in result["messages"]
        if isinstance(msg, AIMessage)
        for call in (msg.tool_calls or [])
    ]

    return ChatResponse(
        reply=reply or "Done.",
        form_updates=result.get("form_updates") or {},
        suggested_followups=result.get("suggested_followups") or [],
        interaction_id=result.get("interaction_id"),
        tool_calls=tool_calls,
        model_used=result.get("model_used", ""),
    )
