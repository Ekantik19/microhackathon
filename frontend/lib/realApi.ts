import { ApiError, STREAM_TOPICS, type MatchApi } from "./api";
import { API_BASE_URL } from "./config";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError("network_error", "Can't reach the InsideMatch API.");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const error = body?.error ?? {};
    throw new ApiError(error.code ?? `http_${response.status}`, error.message ?? response.statusText, response.status);
  }
  return body as T;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const realApi: MatchApi = {
  kind: "real",
  health: () => request("/health"),
  match: (id) => request(`/matches/${id}`),
  state: (id) => request(`/matches/${id}/state`),
  stats: (id, window) => request(`/matches/${id}/stats?window=${window}`),
  timeline: async (id) => (await request<{ items: never[] }>(`/matches/${id}/timeline`)).items,
  events: async (id, sinceSeq, limit) =>
    (await request<{ events: never[] }>(`/matches/${id}/events?since_seq=${sinceSeq}&limit=${limit}`)).events,
  insights: (id, mode) => request(`/matches/${id}/insights?mode=${mode}`),
  recaps: (id) => request(`/matches/${id}/recaps`),
  control: (id, action, speed) =>
    post(`/matches/${id}/simulation/${action}`, action === "start" && speed ? { speed } : undefined),
  setSpeed: (id, speed) => post(`/matches/${id}/simulation/speed`, { speed }),
  seek: (id, matchSecond) => post(`/matches/${id}/simulation/seek`, { match_second: Math.round(matchSecond) }),
  generateRecap: (id, mode, scope) => post(`/matches/${id}/generate-recap`, { mode, scope }),

  subscribe(id, mode, handlers) {
    // One EventSource. On error we close it and reconnect with exponential backoff (1 s → 15 s).
    let source: EventSource | null = null;
    let retry = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let closed = false;

    const connect = () => {
      source = new EventSource(`${API_BASE_URL}/matches/${id}/stream?mode=${mode}`);
      source.onopen = () => {
        retry = 0;
        handlers.onOpen();
      };
      source.onerror = () => {
        source?.close();
        handlers.onError();
        if (closed) return;
        const delay = Math.min(15000, 1000 * 2 ** retry++);
        timer = setTimeout(connect, delay);
      };
      for (const topic of STREAM_TOPICS) {
        source.addEventListener(topic, (e) => handlers.onMessage(topic, JSON.parse((e as MessageEvent).data)));
      }
    };
    connect();
    return () => {
      closed = true;
      if (timer) clearTimeout(timer);
      source?.close();
    };
  },
};
