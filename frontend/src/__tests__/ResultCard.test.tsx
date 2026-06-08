import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ResultCard } from "../components/ResultCard";
import type { SearchResultItem } from "../types";

const item: SearchResultItem = {
  arxiv_id: "2001.11111",
  title: "Scaling Laws for Neural Language Models",
  authors: ["Jane Researcher", "John Scientist"],
  abstract: "We study empirical scaling laws.",
  published: "2020-01-23",
  url: "http://arxiv.org/abs/2001.11111",
  citation_count: 1234,
  sub_scores: { relevance: 1.0, citations: 0.9, recency: 0.5 },
  final_score: 0.82,
  citation_data_missing: false,
};

describe("ResultCard", () => {
  it("renders the title linked to arXiv", () => {
    render(<ResultCard item={item} />);
    const link = screen.getByRole("link", {
      name: /Scaling Laws for Neural Language Models/i,
    });
    expect(link).toHaveAttribute("href", "http://arxiv.org/abs/2001.11111");
  });

  it("shows citation count and the three sub-scores", () => {
    render(<ResultCard item={item} />);
    expect(screen.getByText(/1234/)).toBeInTheDocument();
    expect(screen.getByText(/relevance/i)).toBeInTheDocument();
    expect(screen.getByText(/citations/i)).toBeInTheDocument();
    expect(screen.getByText(/recency/i)).toBeInTheDocument();
  });

  it("shows a flag badge when citation data is missing", () => {
    render(<ResultCard item={{ ...item, citation_data_missing: true }} />);
    expect(screen.getByText(/citation data unavailable/i)).toBeInTheDocument();
  });

  it("does not show the flag badge when citation data is present", () => {
    render(<ResultCard item={item} />);
    expect(screen.queryByText(/citation data unavailable/i)).not.toBeInTheDocument();
  });
});
