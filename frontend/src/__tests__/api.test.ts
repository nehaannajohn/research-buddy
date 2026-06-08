import { afterEach, describe, expect, it, vi } from "vitest";
import { searchPapers } from "../api";
import type { SearchResponse } from "../types";

afterEach(() => {
  vi.restoreAllMocks();
});

const sample: SearchResponse = {
  search_id: "sid1",
  results: [],
  pool_size: 50,
  warnings: [],
};

describe("searchPapers", () => {
  it("posts query, n, and weights and returns parsed JSON", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(sample), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await searchPapers("scaling laws", 5, {
      relevance: 0.5,
      citations: 0.3,
      recency: 0.2,
    });

    expect(result.search_id).toBe("sid1");
    const [, options] = fetchMock.mock.calls[0];
    const body = JSON.parse(options.body as string);
    expect(body).toEqual({
      query: "scaling laws",
      n: 5,
      weights: { relevance: 0.5, citations: 0.3, recency: 0.2 },
    });
    expect(options.method).toBe("POST");
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("nope", { status: 503 }))
    );
    await expect(searchPapers("x", 5)).rejects.toThrow("503");
  });
});
