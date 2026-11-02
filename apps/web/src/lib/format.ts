const BYTES_PER_UNIT = 1024;
const SIZE_UNITS = ["B", "KB", "MB", "GB"];

export function formatFileSize(bytes: number): string {
  let value = bytes;
  let unit = 0;
  while (value >= BYTES_PER_UNIT && unit < SIZE_UNITS.length - 1) {
    value /= BYTES_PER_UNIT;
    unit += 1;
  }
  return `${unit === 0 ? value : value.toFixed(1)} ${SIZE_UNITS[unit]}`;
}

const dateFormatter = new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" });

export function formatDateTime(value: string): string {
  return dateFormatter.format(new Date(value));
}

const monthFormatter = new Intl.DateTimeFormat("en", {
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

export function formatMonthRange(first: string | null, last: string | null): string {
  if (!first || !last) {
    return "Not read yet";
  }
  const start = monthFormatter.format(new Date(first));
  const end = monthFormatter.format(new Date(last));
  return start === end ? start : `${start} to ${end}`;
}

const PROVIDER_NAMES: Record<string, string> = {
  aws: "AWS",
  azure: "Microsoft Azure",
  gcp: "Google Cloud",
  oci: "Oracle Cloud",
  digitalocean: "DigitalOcean",
  multiple: "Several clouds",
};

export function providerName(provider: string | null): string {
  if (!provider) {
    return "Not read yet";
  }
  return PROVIDER_NAMES[provider] ?? provider;
}

export function formatMoney(value: string | number, currency: string): string {
  return new Intl.NumberFormat("en", { style: "currency", currency }).format(Number(value));
}

export function formatPercent(value: string): string {
  return `${Math.abs(Number(value)).toFixed(1)}%`;
}

export function formatMonth(value: string): string {
  return monthFormatter.format(new Date(value));
}
