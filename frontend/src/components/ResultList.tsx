import type { SearchResultItem } from "../types";
import { ResultCard } from "./ResultCard";

interface Props {
  results: SearchResultItem[];
  warnings: string[];
}

export function ResultList({ results, warnings }: Props) {
  return (
    <div className="result-list">
      {warnings.map((w) => (
        <p key={w} className="warning" role="status">
          {w}
        </p>
      ))}
      {results.length === 0 ? (
        <p className="empty">No results yet.</p>
      ) : (
        results.map((item) => <ResultCard key={item.arxiv_id} item={item} />)
      )}
    </div>
  );
}
