from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sse_starlette.sse import EventSourceResponse

from app.config import Settings, get_settings
from app.core.logging import get_logger
from app.middleware.auth import UserContext
from app.middleware.rate_limit import check_rate_limit
from app.models.schemas import (
    ChatStreamRequest,
    ConversationDetailResponse,
    ConversationListData,
    ConversationListResponse,
    ConversationMessagesData,
    ConversationMessagesResponse,
    ConversationResponse,
    CreateConversationRequest,
    SearchData,
    SearchResponse,
    SearchResult,
)
from app.services.conversation import ConversationService, get_conversation_service
from app.services.llm.router import ProviderRouter, get_provider_router
from app.services.search import semantic_search
from app.services.supabase import SupabaseClient, get_supabase_client
from app.utils.streaming import stream_chat_response

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])
CurrentUser = Annotated[UserContext, Depends(check_rate_limit)]
ConversationDependency = Annotated[ConversationService, Depends(get_conversation_service)]
ProviderRouterDependency = Annotated[ProviderRouter, Depends(get_provider_router)]
SupabaseDependency = Annotated[SupabaseClient, Depends(get_supabase_client)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.post("/stream", response_class=EventSourceResponse)
async def stream_chat(
    payload: ChatStreamRequest,
    current_user: CurrentUser,
    llm_router: ProviderRouterDependency,
    conversations: ConversationDependency,
    supabase: SupabaseDependency,
    settings: SettingsDep,
) -> EventSourceResponse:
    logger.info(
        "chat_stream | user_id=%s conversation_id=%s message_count=%d",
        current_user.user_id,
        payload.conversation_id,
        len(payload.messages),
    )
    return stream_chat_response(
        request=payload,
        user_id=current_user.user_id,
        provider_router=llm_router,
        conversations=conversations,
        supabase=supabase,
        settings=settings,
    )


@router.post("/stream/test", response_class=EventSourceResponse)
async def stream_chat_test(
    payload: ChatStreamRequest,
    llm_router: ProviderRouterDependency,
    conversations: ConversationDependency,
    supabase: SupabaseDependency,
    settings: SettingsDep,
) -> EventSourceResponse:
    if not settings.debug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")

    logger.info(
        "chat_stream_test | user_id=%s conversation_id=%s message_count=%d",
        settings.local_dev_user_id,
        payload.conversation_id,
        len(payload.messages),
    )
    return stream_chat_response(
        request=payload,
        user_id=settings.local_dev_user_id,
        provider_router=llm_router,
        conversations=conversations,
        supabase=supabase,
        settings=settings,
    )


@router.get("/search", response_model=SearchResponse)
async def search_knowledge_base(
    current_user: CurrentUser,
    supabase: SupabaseDependency,
    settings: SettingsDep,
    q: str = Query(min_length=1, max_length=500, description="Search query"),
    top_k: int = Query(default=5, ge=1, le=20, description="Number of results"),
    threshold: float = Query(default=0.7, ge=0.0, le=1.0, description="Similarity threshold"),
) -> SearchResponse:
    logger.info(
        "chat_search | user_id=%s query_len=%d top_k=%d",
        current_user.user_id,
        len(q),
        top_k,
    )
    results = await semantic_search(
        query=q,
        supabase=supabase,
        settings=settings,
        top_k=top_k,
        threshold=threshold,
    )
    return SearchResponse(
        data=SearchData(
            query=q,
            results=[SearchResult.model_validate(r.__dict__) for r in results],
        ),
        message=f"{len(results)} result(s) found.",
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    current_user: CurrentUser,
    conversations: ConversationDependency,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ConversationListResponse:
    logger.info("list_conversations | user_id=%s", current_user.user_id)
    items = await conversations.get_conversations(
        user_id=current_user.user_id,
        limit=limit,
        offset=offset,
    )
    return ConversationListResponse(
        data=ConversationListData(conversations=items),
        error=None,
        message=None,
    )


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    payload: CreateConversationRequest,
    current_user: CurrentUser,
    conversations: ConversationDependency,
) -> ConversationResponse:
    logger.info("create_conversation | user_id=%s", current_user.user_id)
    conversation = await conversations.create_conversation(
        user_id=current_user.user_id,
        title=payload.title,
    )
    return ConversationResponse(data=conversation, error=None, message="Conversation created.")


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
async def get_conversation(
    conversation_id: str,
    current_user: CurrentUser,
    conversations: ConversationDependency,
) -> ConversationDetailResponse:
    logger.info(
        "get_conversation | user_id=%s conversation_id=%s",
        current_user.user_id,
        conversation_id,
    )
    try:
        conversation = await conversations.get_conversation(
            user_id=current_user.user_id,
            conversation_id=conversation_id,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        ) from exc
    return ConversationDetailResponse(data=conversation, error=None, message=None)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationMessagesResponse,
)
async def list_conversation_messages(
    conversation_id: str,
    current_user: CurrentUser,
    conversations: ConversationDependency,
) -> ConversationMessagesResponse:
    logger.info(
        "list_messages | user_id=%s conversation_id=%s",
        current_user.user_id,
        conversation_id,
    )
    messages = await conversations.list_messages(
        user_id=current_user.user_id,
        conversation_id=conversation_id,
    )
    return ConversationMessagesResponse(
        data=ConversationMessagesData(messages=messages),
        error=None,
        message=None,
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user: CurrentUser,
    conversations: ConversationDependency,
) -> Response:
    logger.info(
        "delete_conversation | user_id=%s conversation_id=%s",
        current_user.user_id,
        conversation_id,
    )
    await conversations.delete_conversation(
        user_id=current_user.user_id,
        conversation_id=conversation_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
