import type { SearchResponse, Weights } from "./types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function searchPapers(
  query: string,
  n: number,
  weights?: Weights
): Promise<SearchResponse> {
  const res = await fetch(`${BASE_URL}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, n, weights }),
  });
  if (!res.ok) {
    throw new Error(`Search failed (${res.status})`);
  }
  return (await res.json()) as SearchResponse;
}
