import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import * as api from "../api";
import type { SearchResponse } from "../types";

afterEach(() => {
  vi.restoreAllMocks();
});

const response: SearchResponse = {
  search_id: "sid1",
  results: [
    {
      arxiv_id: "2001.11111",
      title: "Scaling Laws for Neural Language Models",
      authors: ["Jane Researcher"],
      abstract: "abstract",
      published: "2020-01-23",
      url: "http://arxiv.org/abs/2001.11111",
      citation_count: 1234,
      sub_scores: { relevance: 1.0, citations: 0.9, recency: 0.5 },
      final_score: 0.82,
      citation_data_missing: false,
    },
  ],
  pool_size: 50,
  warnings: [],
};

describe("App", () => {
  it("renders results after a successful search", async () => {
    vi.spyOn(api, "searchPapers").mockResolvedValue(response);
    render(<App />);

    await userEvent.type(screen.getByLabelText(/query/i), "scaling laws");
    await userEvent.click(screen.getByRole("button", { name: /search/i }));

    await waitFor(() =>
      expect(
        screen.getByText(/Scaling Laws for Neural Language Models/i)
      ).toBeInTheDocument()
    );
  });

  it("shows an error message when the search fails", async () => {
    vi.spyOn(api, "searchPapers").mockRejectedValue(new Error("Search failed (503)"));
    render(<App />);

    await userEvent.type(screen.getByLabelText(/query/i), "x");
    await userEvent.click(screen.getByRole("button", { name: /search/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/503/)
    );
  });
});
