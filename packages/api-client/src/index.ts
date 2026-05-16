import type {
  ChatRequest,
  ChatResponse,
  Conversation,
  ConversationListResponse,
  ConversationMessagesResponse,
  CreateConversationRequest,
  HealthResponse,
  Message
} from "@sirat/shared-types";

export interface ApiClientOptions {
  baseUrl?: string;
  fetcher?: typeof fetch;
  accessToken?: string | null;
  getAccessToken?: () => Promise<string | null> | string | null;
}

let defaultGetAccessToken: ApiClientOptions["getAccessToken"];

export function setApiClientAccessTokenProvider(
  getAccessToken: NonNullable<ApiClientOptions["getAccessToken"]>
) {
  defaultGetAccessToken = getAccessToken;
}

export class ApiClientError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body: unknown
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

function getDefaultBaseUrl() {
  const processLike = globalThis as {
    process?: { env?: Record<string, string | undefined> };
  };
  return processLike.process?.env?.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

function parseSseChunk(chunk: string) {
  const events: { event: string; data: string }[] = [];
  const records = chunk.replace(/\r\n/g, "\n").split("\n\n");

  for (const record of records) {
    if (!record.trim()) {
      continue;
    }

    let event = "message";
    const dataLines: string[] = [];

    for (const line of record.split("\n")) {
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      }
      if (line.startsWith("data:")) {
        const data = line.slice(5);
        dataLines.push(data.startsWith(" ") ? data.slice(1) : data);
      }
    }

    events.push({ event, data: dataLines.join("\n") });
  }

  return events;
}

export function createApiClient({
  baseUrl = getDefaultBaseUrl(),
  fetcher = fetch,
  accessToken,
  getAccessToken
}: ApiClientOptions = {}) {
  const normalizedBaseUrl = baseUrl.replace(/\/$/, "");

  async function resolveAccessToken() {
    if (accessToken !== undefined) {
      return accessToken;
    }
    return (await getAccessToken?.()) ?? null;
  }

  async function createHeaders(init?: RequestInit) {
    const headers = new Headers(init?.headers);
    const token = await resolveAccessToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    return headers;
  }

  async function request<TResponse>(path: string, init?: RequestInit): Promise<TResponse> {
    const headers = await createHeaders(init);
    headers.set("Content-Type", "application/json");

    const response = await fetcher(`${normalizedBaseUrl}${path}`, {
      ...init,
      headers
    });

    const body = (await response.json().catch(() => null)) as unknown;

    if (!response.ok) {
      throw new ApiClientError(
        `API request failed with ${String(response.status)}`,
        response.status,
        body
      );
    }

    return body as TResponse;
  }

  async function* stream(path: string, init?: RequestInit): AsyncGenerator<string> {
    const headers = await createHeaders(init);
    headers.set("Content-Type", "application/json");

    const response = await fetcher(`${normalizedBaseUrl}${path}`, {
      ...init,
      headers
    });

    if (!response.ok || response.body === null) {
      const body = (await response.json().catch(() => null)) as unknown;
      throw new ApiClientError("Streaming API request failed", response.status, body);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let result = await reader.read();

    while (!result.done) {
      buffer = `${buffer}${decoder.decode(result.value, { stream: true })}`.replace(/\r\n/g, "\n");
      const completeRecordIndex = buffer.lastIndexOf("\n\n");
      if (completeRecordIndex === -1) {
        result = await reader.read();
        continue;
      }

      const complete = buffer.slice(0, completeRecordIndex);
      buffer = buffer.slice(completeRecordIndex + 2);

      for (const event of parseSseChunk(complete)) {
        if (event.event === "delta") {
          yield event.data;
        }
        if (event.event === "done") {
          yield `[DONE:${event.data}]`;
        }
        if (event.event === "error") {
          throw new ApiClientError(event.data, response.status, event.data);
        }
      }

      result = await reader.read();
    }
  }

  return {
    health: () => request<HealthResponse>("/health"),
    chatStream: (messages: Message[], conversationId?: string | null) =>
      stream("/chat", {
        method: "POST",
        body: JSON.stringify({
          conversation_id: conversationId ?? null,
          messages
        } satisfies ChatRequest)
      }),
    createChatCompletion: (payload: ChatRequest) =>
      request<ChatResponse>("/chat", {
        method: "POST",
        body: JSON.stringify(payload)
      }),
    getConversations: async () => {
      const body = await request<ConversationListResponse>("/conversations");
      return body.conversations;
    },
    getConversationMessages: async (id: string) => {
      const body = await request<ConversationMessagesResponse>(
        `/conversations/${encodeURIComponent(id)}/messages`
      );
      return body.messages;
    },
    createConversation: (title: string) =>
      request<Conversation>("/conversations", {
        method: "POST",
        body: JSON.stringify({ title } satisfies CreateConversationRequest)
      }),
    deleteConversation: async (id: string) => {
      await request<null>(`/conversations/${encodeURIComponent(id)}`, {
        method: "DELETE"
      });
    }
  };
}

function getDefaultClient() {
  return createApiClient({ getAccessToken: defaultGetAccessToken });
}

export function chatStream(messages: Message[], conversationId?: string | null) {
  return getDefaultClient().chatStream(messages, conversationId);
}

export function getConversations() {
  return getDefaultClient().getConversations();
}

export function getConversationMessages(id: string) {
  return getDefaultClient().getConversationMessages(id);
}

export function createConversation(title: string) {
  return getDefaultClient().createConversation(title);
}

export function deleteConversation(id: string) {
  return getDefaultClient().deleteConversation(id);
}
