import { useState } from "react";

interface Props {
  onSearch: (query: string) => void;
  onNChange: (n: number) => void;
  n: number;
  loading: boolean;
}

const COUNT_OPTIONS = [5, 10, 25];

export function SearchBar({ onSearch, onNChange, n, loading }: Props) {
  const [query, setQuery] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  }

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <label>
        Query
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. scaling laws"
        />
      </label>
      <label>
        Results
        <select value={n} onChange={(e) => onNChange(Number(e.target.value))}>
          {COUNT_OPTIONS.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>
      <button type="submit" disabled={loading}>
        {loading ? "Searching…" : "Search"}
      </button>
    </form>
  );
}
