import { registerOTel } from "@vercel/otel";

/**
 * Next.js calls this once when the server starts. Tracing is on only when an OTLP address is set:
 * locally `make monitoring`, in production Grafana Cloud. The address and login header come from
 * the standard OTEL_EXPORTER_OTLP_* variables.
 */
export function register() {
  if (process.env.OTEL_EXPORTER_OTLP_ENDPOINT) {
    registerOTel({ serviceName: "costpilot-web" });
  }
}
