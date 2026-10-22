// NEXT_PUBLIC_* values are inlined at build time, so the Docker image must be built with the real API URL.
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
export const USE_MOCK_API = process.env.NEXT_PUBLIC_USE_MOCK_API === "true";
export const REPO_URL = "https://github.com/Ekantik19/microhackathon";
