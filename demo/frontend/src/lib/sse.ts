import type { ChatResponse } from "../types";

export interface ChatStreamHandlers {
  onToken: (t: string) => void;
  onDone: (final: ChatResponse) => void;
  onError: (err: string) => void;
}

/**
 * POSTs to /api/chat with the given body and parses the SSE stream.
 *
 * Using fetch + ReadableStream rather than EventSource because EventSource
 * only supports GET. SSE framing is simple enough to parse inline.
 */
export async function postChatStream(
  body: { message: string; session_id?: string | null; scenario_id?: string | null },
  { onToken, onDone, onError }: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  let resp: Response;
  try {
    resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (e) {
    onError((e as Error).message);
    return;
  }
  if (!resp.ok || !resp.body) {
    onError(`chat HTTP ${resp.status}`);
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    // Normalise CRLF → LF before parsing. sse-starlette (and the SSE spec
    // in general) allows CR, LF, or CRLF line endings; without this
    // normalisation the `\n\n` event-boundary search never matches when
    // the server emits CRLF and the chat UI hangs forever.
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

    let sepIdx: number;
    while ((sepIdx = buffer.indexOf("\n\n")) >= 0) {
      const raw = buffer.slice(0, sepIdx);
      buffer = buffer.slice(sepIdx + 2);

      let event = "message";
      let data = "";
      for (const line of raw.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (!data) continue;
      try {
        const parsed = JSON.parse(data);
        if (event === "token") onToken(parsed.text ?? "");
        else if (event === "done") onDone(parsed as ChatResponse);
        else if (event === "error") onError(parsed.error ?? "unknown error");
      } catch {
        // skip malformed chunk
      }
    }
  }
}
