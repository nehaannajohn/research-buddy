import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SortControl } from "../components/SortControl";

describe("SortControl", () => {
  it("renders Citations and Recency options", () => {
    render(<SortControl sort="relevance" onChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: /citations/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /recency/i })).toBeInTheDocument();
  });

  it("calls onChange with the chosen sort key", async () => {
    const onChange = vi.fn();
    render(<SortControl sort="relevance" onChange={onChange} />);

    await userEvent.click(screen.getByRole("button", { name: /citations/i }));
    expect(onChange).toHaveBeenCalledWith("citations");

    await userEvent.click(screen.getByRole("button", { name: /recency/i }));
    expect(onChange).toHaveBeenCalledWith("recency");
  });

  it("marks the active sort as pressed", () => {
    render(<SortControl sort="citations" onChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: /citations/i })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.getByRole("button", { name: /recency/i })).toHaveAttribute(
      "aria-pressed",
      "false"
    );
  });
});
