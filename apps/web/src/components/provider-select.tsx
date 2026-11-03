import { providerName } from "@/lib/format";

type ProviderSelectProps = {
  providers: string[];
  value?: string;
  onChange: (provider?: string) => void;
};

/** Shown only when bills come from more than one cloud. */
export function ProviderSelect({ providers, value, onChange }: ProviderSelectProps) {
  if (providers.length < 2 && !value) {
    return null;
  }
  return (
    <label className="text-sm text-muted">
      <select
        aria-label="Cloud"
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value || undefined)}
        className="rounded-control border border-border bg-surface px-3 py-2 font-medium text-foreground"
      >
        <option value="">All clouds</option>
        {providers.map((name) => (
          <option key={name} value={name}>
            {providerName(name)}
          </option>
        ))}
      </select>
    </label>
  );
}
