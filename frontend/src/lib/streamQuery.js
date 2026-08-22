const API_URL = import.meta.env.VITE_API_URL;

/**
 * Parse one SSE message block into an event type + data string.
 * Normalises \r\n → \n so the parser works whether the server
 * sends CRLF (RFC 8895 compliant) or LF-only line endings.
 */
function parseSseMessage(rawMessage, { onToken, onDone, onError }) {
  const message = rawMessage.replace(/\r/g, "");
  if (!message.trim()) return;

  const lines = message.split("\n");
  let eventType = "message";
  let data = "";

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventType = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      // Strip the single optional space after "data:" but preserve the rest.
      const payload = line.slice("data:".length);
      data += payload.startsWith(" ") ? payload.slice(1) : payload;
    }
  }

  if (!data) return;

  if (eventType === "token") {
    onToken(data);
  } else if (eventType === "done") {
    onDone(JSON.parse(data));
  } else if (eventType === "error") {
    onError(JSON.parse(data).message || "Something went wrong.");
  }
}

/**
 * Streams an answer from POST /query/stream.
 *
 * Uses fetch + ReadableStream instead of EventSource because EventSource
 * only supports GET — we need to POST the question in the request body.
 *
 * Pass `signal` (from an AbortController) to support the Stop button.
 * When aborted the stream is finalised with empty sources so the partial
 * answer is preserved in the UI.
 *
 * Callbacks:
 *   onToken(text)    — one call per streamed token
 *   onDone(payload)  — { sources, has_image, image_url } at the end
 *   onError(message) — called on network / parse errors
 *   signal           — optional AbortSignal
 */
export async function streamQuery(question, { onToken, onDone, onError, signal }) {
  if (!API_URL) {
    onError("VITE_API_URL is not set — check frontend/.env and restart the dev server.");
    return;
  }

  let response;
  try {
    response = await fetch(`${API_URL}/query/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal,
    });
  } catch (err) {
    if (err.name === "AbortError") {
      onDone({ sources: [], has_image: false, image_url: null });
      return;
    }
    onError(`Couldn't reach the API at ${API_URL}. Is the backend running?`);
    return;
  }

  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      /* response wasn't JSON — keep generic message */
    }
    onError(detail);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // Track whether the "done" SSE event was successfully processed.
  // The server closes the TCP connection after sending all events, which
  // can cause reader.read() to throw on the *next* call even though the
  // stream completed correctly. Without this flag, the catch block would
  // overwrite a perfectly good answer with the "connection interrupted" error.
  let doneFired = false;

  const guardedOnDone = (payload) => {
    doneFired = true;
    onDone(payload);
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE events are delimited by a blank line. The server (sse-starlette)
      // sends CRLF line endings ("\r\n"), so the event separator is "\r\n\r\n".
      // We normalise all CR characters out of the buffer first so that the
      // split on "\n\n" reliably finds every event boundary.
      buffer = buffer.replace(/\r/g, "");

      // Split on "\n\n" and keep the trailing incomplete fragment in the buffer.
      const parts = buffer.split("\n\n");
      buffer = parts.pop(); // last element may be incomplete

      for (const part of parts) {
        parseSseMessage(part, { onToken, onDone: guardedOnDone, onError });
      }
    }

    // Flush any remaining bytes from the decoder.
    buffer += decoder.decode();
    if (buffer.trim()) {
      parseSseMessage(buffer, { onToken, onDone: guardedOnDone, onError });
    }
  } catch (err) {
    if (err.name === "AbortError") {
      if (!doneFired) onDone({ sources: [], has_image: false, image_url: null });
    } else if (!doneFired) {
      // Only show the network error if we never received a proper "done" event.
      // If doneFired is true, the answer was delivered correctly — the exception
      // is just the server closing the connection after streaming finished.
      onError("The connection was interrupted. Please try again.");
    }
  }
}
