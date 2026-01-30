"""Chat API endpoints."""

import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agents import chat, chat_stream

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """Chat message model."""

    content: str


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str
    history: list[dict] | None = None


class ChatResponse(BaseModel):
    """Chat response model."""

    response: str
    success: bool = True
    error: str | None = None


@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest) -> ChatResponse:
    """Send a message and get a response from the agent.

    Args:
        request: Chat request with message and optional history

    Returns:
        Agent's response
    """
    try:
        response = await chat(request.message, request.history)
        return ChatResponse(response=response)
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return ChatResponse(
            response="",
            success=False,
            error=str(e)
        )


@router.post("/stream")
async def send_message_stream(request: ChatRequest):
    """Send a message and stream the response from the agent.

    Args:
        request: Chat request with message and optional history

    Returns:
        Streaming response with agent's reply
    """
    async def generate():
        try:
            async for chunk in chat_stream(request.message, request.history):
                yield chunk
        except Exception as e:
            logger.error(f"Error in chat stream: {e}")
            yield f"Error: {str(e)}"

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )
