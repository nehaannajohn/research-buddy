import type { SearchResultItem } from "../types";

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
        <span> · {item.citation_count} citations</span>
        {item.citation_data_missing && (
          <span className="badge"> · citation data unavailable</span>
        )}
      </p>
      <p className="abstract">{item.abstract}</p>
    </article>
  );
}
