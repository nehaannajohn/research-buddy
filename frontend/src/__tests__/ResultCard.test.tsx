import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ResultCard } from "../components/ResultCard";
import type { SearchResultItem } from "../types";

const item: SearchResultItem = {
  arxiv_id: "2001.08361",
  title: "Scaling Laws for Neural Language Models",
  authors: ["Jared Kaplan", "Sam McCandlish"],
  abstract: "We study empirical scaling laws.",
  published: "2020-01-23",
  url: "http://arxiv.org/abs/2001.08361",
  citation_count: 1504,
  citation_data_missing: false,
};

describe("ResultCard", () => {
  it("renders the title linked to arXiv", () => {
    render(<ResultCard item={item} />);
    const link = screen.getByRole("link", {
      name: /Scaling Laws for Neural Language Models/i,
    });
    expect(link).toHaveAttribute("href", "http://arxiv.org/abs/2001.08361");
  });

  it("shows the citation count and date", () => {
    render(<ResultCard item={item} />);
    expect(screen.getByText(/1504/)).toBeInTheDocument();
    expect(screen.getByText(/2020-01-23/)).toBeInTheDocument();
  });

  it("does not render a score breakdown", () => {
    render(<ResultCard item={item} />);
    expect(screen.queryByText(/relevance/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/recency/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/score/i)).not.toBeInTheDocument();
  });

  it("shows a flag badge when citation data is missing", () => {
    render(<ResultCard item={{ ...item, citation_data_missing: true }} />);
    expect(screen.getByText(/citation data unavailable/i)).toBeInTheDocument();
  });
});
