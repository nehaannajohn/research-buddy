import { afterEach, describe, expect, it, vi } from "vitest";
import { resortPapers, searchPapers } from "../api";
import type { ResortResponse, SearchResponse } from "../types";

afterEach(() => {
  vi.restoreAllMocks();
});

const searchSample: SearchResponse = {
  search_id: "sid1",
  results: [],
  pool_size: 200,
  warnings: [],
};

const resortSample: ResortResponse = {
  search_id: "sid1",
  results: [],
  warnings: [],
};

describe("searchPapers", () => {
  it("POSTs query and n, returns parsed JSON", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(searchSample), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await searchPapers("scaling laws", 10);
    expect(result.search_id).toBe("sid1");

    const [url, options] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/search$/);
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body as string)).toEqual({ query: "scaling laws", n: 10 });
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("nope", { status: 503 }))
    );
    await expect(searchPapers("x", 10)).rejects.toThrow("503");
  });
});

describe("resortPapers", () => {
  it("GETs the re-sort endpoint with sort and n", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(resortSample), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await resortPapers("sid1", "citations", 25);

    const [url, options] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/api/search/sid1");
    expect(String(url)).toContain("sort=citations");
    expect(String(url)).toContain("n=25");
    expect(options?.method ?? "GET").toBe("GET");
  });

  it("throws an expired error on 404", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("gone", { status: 404 }))
    );
    await expect(resortPapers("sid1", "citations", 10)).rejects.toThrow(/expired/i);
  });
});
