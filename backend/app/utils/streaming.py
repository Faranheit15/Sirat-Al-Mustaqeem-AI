from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

from sse_starlette.sse import EventSourceResponse

from app.core.logging import get_logger
from app.models.schemas import ChatMessage, ChatStreamRequest
from app.services.conversation import ConversationService
from app.services.llm.router import ProviderRouter

logger = get_logger(__name__)


def _is_word_like(character: str) -> bool:
    return character.isalnum()


def _should_insert_space(previous: str, next_chunk: str) -> bool:
    if not previous or not next_chunk or previous[-1].isspace() or next_chunk[0].isspace():
        return False

    previous_character = previous[-1]
    next_character = next_chunk[0]

    if next_character in ",.;:!?%)" or next_character == "'":
        return False

    if previous_character in "([{/$-":
        return False

    if _is_word_like(previous_character) and _is_word_like(next_character):
        return True

    return previous_character in ".!?:;" and _is_word_like(next_character)


def append_assistant_delta(previous: str, delta: str) -> str:
    separator = " " if _should_insert_space(previous, delta) else ""
    return f"{previous}{separator}{delta}"


async def chat_event_generator(
    request: ChatStreamRequest,
    user_id: str,
    provider_router: ProviderRouter,
    conversations: ConversationService,
) -> AsyncIterator[dict[str, str]]:
    assistant_content = ""

    logger.info(
        "sse_stream_start | user_id=%s conversation_id=%s",
        user_id,
        request.conversation_id,
    )

    try:
        async for delta in provider_router.stream_chat(request.messages):
            assistant_content = append_assistant_delta(assistant_content, delta)
            yield {"event": "delta", "data": delta}

        assistant_message = ChatMessage(
            id=str(uuid4()),
            role="assistant",
            content=assistant_content,
            created_at=datetime.now(UTC).isoformat(),
        )
        user_message = next(
            (message for message in reversed(request.messages) if message.role == "user"),
            request.messages[-1],
        )
        conversation_id = await conversations.save_exchange(
            user_id=user_id,
            conversation_id=request.conversation_id,
            user_message=user_message,
            assistant_message=assistant_message,
        )
        logger.info(
            "sse_stream_done | user_id=%s conversation_id=%s provider=%s",
            user_id,
            conversation_id,
            provider_router.last_provider_name,
        )
        yield {"event": "done", "data": conversation_id or ""}
    except Exception as exc:
        logger.error(
            "sse_stream_error | user_id=%s conversation_id=%s error=%s",
            user_id,
            request.conversation_id,
            exc,
        )
        yield {"event": "error", "data": str(exc)}


def stream_chat_response(
    request: ChatStreamRequest,
    user_id: str,
    provider_router: ProviderRouter,
    conversations: ConversationService,
) -> EventSourceResponse:
    return EventSourceResponse(
        chat_event_generator(
            request=request,
            user_id=user_id,
            provider_router=provider_router,
            conversations=conversations,
        ),
        media_type="text/event-stream",
    )
