import { useState } from "react";
import { searchPapers } from "./api";
import { ResultList } from "./components/ResultList";
import { SearchBar } from "./components/SearchBar";
import { WeightSliders } from "./components/WeightSliders";
import type { SearchResponse, Weights } from "./types";
import "./App.css";

const DEFAULT_WEIGHTS: Weights = { relevance: 0.5, citations: 0.3, recency: 0.2 };

export default function App() {
  const [weights, setWeights] = useState<Weights>(DEFAULT_WEIGHTS);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(query: string, n: number) {
    setLoading(true);
    setError(null);
    try {
      const result = await searchPapers(query, n, weights);
      setResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setResponse(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app">
      <h1>Research Buddy</h1>
      <SearchBar onSearch={handleSearch} loading={loading} />
      <WeightSliders weights={weights} onChange={setWeights} />

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {loading && <p className="loading">Searching…</p>}

      {!loading && response && (
        <ResultList results={response.results} warnings={response.warnings} />
      )}
    </main>
  );
}
