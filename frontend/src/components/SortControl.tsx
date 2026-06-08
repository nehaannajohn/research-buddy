import type { SortKey } from "../types";

interface Props {
  sort: SortKey;
  onChange: (sort: SortKey) => void;
}

const OPTIONS: { key: SortKey; label: string }[] = [
  { key: "citations", label: "Citations" },
  { key: "recency", label: "Recency" },
];

export function SortControl({ sort, onChange }: Props) {
  return (
    <div className="sort-control" role="group" aria-label="Sort results">
      <span>Sort by:</span>
      {OPTIONS.map(({ key, label }) => (
        <button
          key={key}
          type="button"
          aria-pressed={sort === key}
          onClick={() => onChange(key)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
