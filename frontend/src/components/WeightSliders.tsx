import type { Weights } from "../types";

interface Props {
  weights: Weights;
  onChange: (weights: Weights) => void;
}

const FIELDS: { key: keyof Weights; label: string }[] = [
  { key: "relevance", label: "Relevance" },
  { key: "citations", label: "Citations" },
  { key: "recency", label: "Recency" },
];

export function WeightSliders({ weights, onChange }: Props) {
  return (
    <fieldset className="weight-sliders">
      <legend>Ranking weights</legend>
      {FIELDS.map(({ key, label }) => (
        <label key={key}>
          {label} ({weights[key].toFixed(2)})
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={weights[key]}
            onChange={(e) =>
              onChange({ ...weights, [key]: Number(e.target.value) })
            }
          />
        </label>
      ))}
    </fieldset>
  );
}
