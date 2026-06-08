import type { ResortResponse, SearchResponse, SortKey } from "./types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function searchPapers(query: string, n: number): Promise<SearchResponse> {
  const res = await fetch(`${BASE_URL}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, n }),
  });
  if (!res.ok) {
    throw new Error(`Search failed (${res.status})`);
  }
  return (await res.json()) as SearchResponse;
}

export async function resortPapers(
  searchId: string,
  sort: SortKey,
  n: number
): Promise<ResortResponse> {
  const params = new URLSearchParams({ sort, n: String(n) });
  const res = await fetch(`${BASE_URL}/api/search/${searchId}?${params}`);
  if (res.status === 404) {
    throw new Error("Search expired — please search again.");
  }
  if (!res.ok) {
    throw new Error(`Sort failed (${res.status})`);
  }
  return (await res.json()) as ResortResponse;
}
