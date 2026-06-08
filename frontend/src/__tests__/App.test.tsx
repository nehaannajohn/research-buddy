import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import * as api from "../api";
import type { ResortResponse, SearchResponse, SearchResultItem } from "../types";

afterEach(() => {
  vi.restoreAllMocks();
});

function item(aid: string, title: string, citations: number): SearchResultItem {
  return {
    arxiv_id: aid,
    title,
    authors: ["A"],
    abstract: "abstract",
    published: "2020-01-23",
    url: `http://arxiv.org/abs/${aid}`,
    citation_count: citations,
    citation_data_missing: false,
  };
}

const searchResponse: SearchResponse = {
  search_id: "sid1",
  results: [item("a", "Alpha paper", 5), item("b", "Beta paper", 999)],
  pool_size: 200,
  warnings: [],
};

const citationsSorted: ResortResponse = {
  search_id: "sid1",
  results: [item("b", "Beta paper", 999), item("a", "Alpha paper", 5)],
  warnings: [],
};

describe("App", () => {
  it("renders results in relevance order after a search", async () => {
    vi.spyOn(api, "searchPapers").mockResolvedValue(searchResponse);
    render(<App />);

    await userEvent.type(screen.getByLabelText(/query/i), "scaling laws");
    await userEvent.click(screen.getByRole("button", { name: /search/i }));

    await waitFor(() => expect(screen.getByText(/Alpha paper/)).toBeInTheDocument());
  });

  it("re-sorts via the resort endpoint when Citations is clicked", async () => {
    vi.spyOn(api, "searchPapers").mockResolvedValue(searchResponse);
    const resortSpy = vi.spyOn(api, "resortPapers").mockResolvedValue(citationsSorted);
    render(<App />);

    await userEvent.type(screen.getByLabelText(/query/i), "scaling laws");
    await userEvent.click(screen.getByRole("button", { name: /search/i }));
    await waitFor(() => expect(screen.getByText(/Alpha paper/)).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /citations/i }));

    await waitFor(() => expect(resortSpy).toHaveBeenCalledWith("sid1", "citations", 10));
  });

  it("shows an error when the search fails", async () => {
    vi.spyOn(api, "searchPapers").mockRejectedValue(new Error("Search failed (503)"));
    render(<App />);

    await userEvent.type(screen.getByLabelText(/query/i), "x");
    await userEvent.click(screen.getByRole("button", { name: /search/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/503/));
  });

  it("shows an expired message when re-sorting a lost search", async () => {
    vi.spyOn(api, "searchPapers").mockResolvedValue(searchResponse);
    vi.spyOn(api, "resortPapers").mockRejectedValue(
      new Error("Search expired — please search again.")
    );
    render(<App />);

    await userEvent.type(screen.getByLabelText(/query/i), "scaling laws");
    await userEvent.click(screen.getByRole("button", { name: /search/i }));
    await waitFor(() => expect(screen.getByText(/Alpha paper/)).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /recency/i }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/expired/i));
  });
});
