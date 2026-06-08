import { useState } from "react";

interface Props {
  onSearch: (query: string, n: number) => void;
  loading: boolean;
}

export function SearchBar({ onSearch, loading }: Props) {
  const [query, setQuery] = useState("");
  const [n, setN] = useState(10);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim(), n);
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
        <input
          type="number"
          min={1}
          max={100}
          value={n}
          onChange={(e) => setN(Number(e.target.value))}
        />
      </label>
      <button type="submit" disabled={loading}>
        {loading ? "Searching…" : "Search"}
      </button>
    </form>
  );
}
