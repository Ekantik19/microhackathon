import type { MatchApi } from "./api";
import { USE_MOCK_API } from "./config";
import { realApi } from "./realApi";

let mock: Promise<MatchApi> | null = null;

/** The real HTTP API, or (with NEXT_PUBLIC_USE_MOCK_API=true) the clearly-labeled mock replay. */
export function getApi(): Promise<MatchApi> {
  if (!USE_MOCK_API) return Promise.resolve(realApi);
  mock ??= import("./mock/mockApi").then((m) => m.mockApi);
  return mock;
}
