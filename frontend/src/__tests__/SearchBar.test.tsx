import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SearchBar } from "../components/SearchBar";

describe("SearchBar", () => {
  it("submits the query and n", async () => {
    const onSearch = vi.fn();
    render(<SearchBar onSearch={onSearch} loading={false} />);

    await userEvent.type(screen.getByLabelText(/query/i), "scaling laws");
    const nInput = screen.getByLabelText(/results/i);
    await userEvent.clear(nInput);
    await userEvent.type(nInput, "7");
    await userEvent.click(screen.getByRole("button", { name: /search/i }));

    expect(onSearch).toHaveBeenCalledWith("scaling laws", 7);
  });

  it("disables the button while loading", () => {
    render(<SearchBar onSearch={vi.fn()} loading={true} />);
    expect(screen.getByRole("button", { name: /search/i })).toBeDisabled();
  });
});
