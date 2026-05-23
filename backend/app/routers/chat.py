from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sse_starlette.sse import EventSourceResponse

from app.dependencies import get_current_user
from app.middleware.auth import AuthenticatedUser
from app.models.schemas import (
    ChatStreamRequest,
    ConversationListData,
    ConversationListResponse,
    ConversationMessagesData,
    ConversationMessagesResponse,
    ConversationResponse,
    CreateConversationRequest,
)
from app.services.conversation import ConversationService, get_conversation_service
from app.services.llm.router import ProviderRouter, get_provider_router
from app.utils.streaming import stream_chat_response

router = APIRouter(prefix="/chat", tags=["chat"])
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
ConversationDependency = Annotated[ConversationService, Depends(get_conversation_service)]
ProviderRouterDependency = Annotated[ProviderRouter, Depends(get_provider_router)]


@router.post("/stream", response_class=EventSourceResponse)
async def stream_chat(
    payload: ChatStreamRequest,
    current_user: CurrentUser,
    llm_router: ProviderRouterDependency,
    conversations: ConversationDependency,
) -> EventSourceResponse:
    return stream_chat_response(
        request=payload,
        user_id=current_user.user_id,
        provider_router=llm_router,
        conversations=conversations,
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    current_user: CurrentUser,
    conversations: ConversationDependency,
) -> ConversationListResponse:
    items = await conversations.list_conversations(user_id=current_user.user_id)
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
    conversation = await conversations.create_conversation(
        user_id=current_user.user_id,
        title=payload.title,
    )
    return ConversationResponse(data=conversation, error=None, message="Conversation created.")


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationMessagesResponse,
)
async def list_conversation_messages(
    conversation_id: str,
    current_user: CurrentUser,
    conversations: ConversationDependency,
) -> ConversationMessagesResponse:
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
    await conversations.delete_conversation(
        user_id=current_user.user_id,
        conversation_id=conversation_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
