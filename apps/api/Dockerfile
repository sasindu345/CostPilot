FROM python:3.13-slim AS build
RUN pip install --no-cache-dir uv==0.13.6
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.13-slim
RUN useradd --create-home --uid 1000 costpilot
WORKDIR /app
COPY --from=build /app/.venv ./.venv
ENV PATH="/app/.venv/bin:$PATH"
USER costpilot
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/health')"]
CMD ["uvicorn", "costpilot.main:app", "--host", "0.0.0.0", "--port", "8000"]
