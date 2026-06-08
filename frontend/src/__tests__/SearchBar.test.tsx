import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SearchBar } from "../components/SearchBar";

describe("SearchBar", () => {
  it("submits the typed query", async () => {
    const onSearch = vi.fn();
    render(<SearchBar onSearch={onSearch} loading={false} n={10} onNChange={vi.fn()} />);

    await userEvent.type(screen.getByLabelText(/query/i), "scaling laws");
    await userEvent.click(screen.getByRole("button", { name: /search/i }));

    expect(onSearch).toHaveBeenCalledWith("scaling laws");
  });

  it("calls onNChange when the count selector changes", async () => {
    const onNChange = vi.fn();
    render(<SearchBar onSearch={vi.fn()} loading={false} n={10} onNChange={onNChange} />);

    await userEvent.selectOptions(screen.getByLabelText(/results/i), "25");
    expect(onNChange).toHaveBeenCalledWith(25);
  });

  it("disables the button while loading", () => {
    render(<SearchBar onSearch={vi.fn()} loading={true} n={10} onNChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: /search/i })).toBeDisabled();
  });
});
