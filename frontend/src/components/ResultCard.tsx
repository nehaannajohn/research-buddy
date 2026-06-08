import type { SearchResultItem } from "../types";

function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function ResultCard({ item }: { item: SearchResultItem }) {
  return (
    <article className="result-card">
      <h3>
        <a href={item.url} target="_blank" rel="noreferrer">
          {item.title}
        </a>
      </h3>
      <p className="authors">{item.authors.join(", ")}</p>
      <p className="meta">
        <span>{item.published}</span>
        <span> · {item.citation_count} cites</span>
        {item.citation_data_missing && (
          <span className="badge"> · citation data unavailable</span>
        )}
      </p>
      <p className="abstract">{item.abstract}</p>
      <dl className="scores">
        <div>
          <dt>relevance</dt>
          <dd>{pct(item.sub_scores.relevance)}</dd>
        </div>
        <div>
          <dt>citations</dt>
          <dd>{pct(item.sub_scores.citations)}</dd>
        </div>
        <div>
          <dt>recency</dt>
          <dd>{pct(item.sub_scores.recency)}</dd>
        </div>
        <div>
          <dt>score</dt>
          <dd>{pct(item.final_score)}</dd>
        </div>
      </dl>
    </article>
  );
}
