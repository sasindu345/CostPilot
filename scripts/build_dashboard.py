"""Writes infra/monitoring/costpilot-dashboard.json. Edit the panels here, then run this script.

The same file can be imported into Grafana Cloud.
"""

import json
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "infra/monitoring/costpilot-dashboard.json"
PROMETHEUS = {"type": "prometheus", "uid": "${metrics}"}
TEMPO = {"type": "tempo", "uid": "${traces}"}
API = 'service_name="costpilot-api"'
REQUESTS = f"http_server_request_duration_seconds_count{{{API}}}"
WINDOW = "[$__rate_interval]"


# Counts over a period use increase(), which needs two samples of a series. Right after a restart
# the first few minutes can read low.


def stat(title, expr, unit, x, description, thresholds=None):
    steps = thresholds or [{"color": "text", "value": None}]
    return {
        "type": "stat",
        "title": title,
        "description": description,
        "datasource": PROMETHEUS,
        "gridPos": {"h": 4, "w": 6, "x": x, "y": 0},
        "targets": [{"expr": expr, "refId": "A", "instant": True}],
        "fieldConfig": {
            "defaults": {"unit": unit, "thresholds": {"mode": "absolute", "steps": steps}},
            "overrides": [],
        },
        "options": {
            "colorMode": "value",
            "graphMode": "none",
            "reduceOptions": {"calcs": ["lastNotNull"]},
        },
    }


def series(title, targets, unit, grid, description, kind="timeseries"):
    return {
        "type": kind,
        "title": title,
        "description": description,
        "datasource": PROMETHEUS,
        "gridPos": grid,
        "targets": [
            {"expr": expr, "legendFormat": legend, "refId": chr(65 + i)}
            for i, (expr, legend) in enumerate(targets)
        ],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "min": 0,
                "custom": {"lineWidth": 2, "fillOpacity": 0, "showPoints": "never"},
            },
            "overrides": [],
        },
        "options": {"legend": {"displayMode": "list", "placement": "bottom", "showLegend": True}},
    }


def bars(title, expr, legend, grid, description):
    panel = series(title, [(expr, legend)], "short", grid, description, kind="bargauge")
    panel["targets"][0]["instant"] = True
    panel["options"] = {
        "orientation": "horizontal",
        "displayMode": "basic",
        "reduceOptions": {"calcs": ["lastNotNull"]},
    }
    return panel


PANELS = [
    stat(
        "Requests per minute",
        f"sum(rate({REQUESTS}{WINDOW})) * 60",
        "short",
        0,
        "API requests per minute, health checks left out.",
    ),
    stat(
        "Server errors",
        f'(sum(rate(http_server_request_duration_seconds_count{{{API},http_response_status_code=~"5.."}}{WINDOW}))'
        f" or vector(0)) / sum(rate({REQUESTS}{WINDOW}))",
        "percentunit",
        6,
        "Share of API requests that failed on our side (5xx).",
        [{"color": "text", "value": None}, {"color": "red", "value": 0.01}],
    ),
    stat(
        "AI calls (period)",
        "round(sum(increase(costpilot_ai_calls_total[$__range])))",
        "short",
        12,
        "Gemini calls in the selected time range. The free key allows few per minute.",
    ),
    stat(
        "Failed AI calls (period)",
        'round(sum(increase(costpilot_ai_calls_total{outcome="failed"}[$__range]))) or vector(0)',
        "short",
        18,
        "Gemini calls that failed, in the selected time range.",
        [{"color": "text", "value": None}, {"color": "red", "value": 1}],
    ),
    series(
        "Requests per second, by route",
        [(f"topk(8, sum by (http_route) (rate({REQUESTS}{WINDOW})))", "{{http_route}}")],
        "reqps",
        {"h": 8, "w": 12, "x": 0, "y": 4},
        "The eight busiest API routes.",
    ),
    series(
        "Response time, 95th percentile",
        [
            (
                "histogram_quantile(0.95, sum by (le) (rate("
                f'http_server_request_duration_seconds_bucket{{{API},http_route!~".*/messages"}}{WINDOW})))',
                "API, without AI answers",
            ),
            (
                "histogram_quantile(0.95, sum by (le) (rate("
                f'http_server_request_duration_seconds_bucket{{{API},http_route=~".*/messages",http_request_method="POST"}}{WINDOW})))',
                "AI answers",
            ),
        ],
        "s",
        {"h": 8, "w": 12, "x": 12, "y": 4},
        "95 of every 100 requests were faster than this. AI answers stream, so they are apart.",
    ),
    series(
        "Gemini calls per minute, by step",
        [(f"sum by (step) (rate(costpilot_ai_calls_total{WINDOW})) * 60", "{{step}}")],
        "short",
        {"h": 8, "w": 8, "x": 0, "y": 12},
        "route = supervisor, specialist = AI specialist agents, answer = final answer.",
    ),
    series(
        "Gemini call time, 95th percentile",
        [
            (
                "histogram_quantile(0.95, sum by (le, step) "
                f"(rate(costpilot_ai_duration_seconds_bucket{WINDOW})))",
                "{{step}}",
            )
        ],
        "s",
        {"h": 8, "w": 8, "x": 8, "y": 12},
        "Time for one Gemini call. Almost all of an answer's wait is here.",
    ),
    series(
        "Gemini tokens per minute",
        [(f"sum by (direction) (rate(costpilot_ai_tokens_total{WINDOW})) * 60", "{{direction}}")],
        "short",
        {"h": 8, "w": 8, "x": 16, "y": 12},
        "Tokens sent to Gemini (input) and received (output).",
    ),
    bars(
        "Answer evidence grades (period)",
        "round(sum by (grade) (increase("
        'costpilot_events_total{action="assistant.answered",grade=~"A|B|C|D"}[$__range])))',
        "Grade {{grade}}",
        {"h": 8, "w": 8, "x": 0, "y": 20},
        "A = full detail and documents. D = not enough evidence. Grades are set by code. "
        "Refusals have no grade.",
    ),
    bars(
        "Actions (period)",
        "sort_desc(round(sum by (action) (increase(costpilot_events_total[$__range]))))",
        "{{action}}",
        {"h": 8, "w": 8, "x": 8, "y": 20},
        "Audited actions: uploads, sign-ins, answers, exports and deletions.",
    ),
    {
        "type": "table",
        "title": "Slowest recent requests (traces)",
        "description": "Click a trace ID to see each step, including every agent and Gemini call.",
        "datasource": TEMPO,
        "gridPos": {"h": 8, "w": 8, "x": 16, "y": 20},
        "targets": [
            {
                "refId": "A",
                "queryType": "traceql",
                "query": '{ resource.service.name = "costpilot-api" && duration > 1s }',
                "limit": 20,
            }
        ],
    },
]

DASHBOARD = {
    "uid": "costpilot",
    "title": "CostPilot",
    "description": "API health, AI use and answer quality. Built by scripts/build_dashboard.py.",
    "tags": ["costpilot"],
    "timezone": "browser",
    "refresh": "30s",
    "time": {"from": "now-1h", "to": "now"},
    "schemaVersion": 41,
    "templating": {
        "list": [
            {"name": "metrics", "label": "Metrics", "type": "datasource", "query": "prometheus"},
            {"name": "traces", "label": "Traces", "type": "datasource", "query": "tempo"},
        ]
    },
    "panels": PANELS,
}

OUTPUT.write_text(json.dumps(DASHBOARD, indent=2) + "\n")
print(f"Wrote {OUTPUT.relative_to(OUTPUT.parents[2])}")
