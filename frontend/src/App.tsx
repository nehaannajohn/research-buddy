import { useState } from "react";
import { resortPapers, searchPapers } from "./api";
import { ResultList } from "./components/ResultList";
import { SearchBar } from "./components/SearchBar";
import { SortControl } from "./components/SortControl";
import type { SearchResultItem, SortKey } from "./types";
import "./App.css";

export default function App() {
  const [searchId, setSearchId] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [sort, setSort] = useState<SortKey>("relevance");
  const [n, setN] = useState(10);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(query: string) {
    setLoading(true);
    setError(null);
    setSort("relevance");
    try {
      const resp = await searchPapers(query, n);
      setSearchId(resp.search_id);
      setResults(resp.results);
      setWarnings(resp.warnings);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setResults([]);
      setSearched(true);
    } finally {
      setLoading(false);
    }
  }

  async function applySort(nextSort: SortKey, nextN: number) {
    if (!searchId) return;
    setError(null);
    try {
      const resp = await resortPapers(searchId, nextSort, nextN);
      setResults(resp.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    }
  }

  function handleSortChange(nextSort: SortKey) {
    setSort(nextSort);
    applySort(nextSort, n);
  }

  function handleNChange(nextN: number) {
    setN(nextN);
    applySort(sort, nextN);
  }

  return (
    <main className="app">
      <h1>Research Buddy</h1>
      <SearchBar onSearch={handleSearch} onNChange={handleNChange} n={n} loading={loading} />
      {searchId && <SortControl sort={sort} onChange={handleSortChange} />}

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {loading && <p className="loading">Searching…</p>}

      {!loading && searched && !error && (
        <ResultList results={results} warnings={warnings} />
      )}
    </main>
  );
}
