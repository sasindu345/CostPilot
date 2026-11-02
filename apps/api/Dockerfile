FROM python:3.13-slim AS build
RUN pip install --no-cache-dir uv==0.13.6
WORKDIR /app
# Packages come first, so a code change does not download them all again.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.13-slim
# The running app has no use for pip or Python's test files, and they carry known security problems.
RUN useradd --create-home --uid 1000 costpilot \
  && install -d -o costpilot /app/uploads \
  && rm -rf /usr/local/bin/pip* \
    /usr/local/lib/python3.13/site-packages/pip* \
    /usr/local/lib/python3.13/ensurepip \
    /usr/local/lib/python3.13/test
WORKDIR /app
COPY --from=build /app/.venv ./.venv
COPY alembic.ini ./
COPY migrations ./migrations
ENV PATH="/app/.venv/bin:$PATH"
USER costpilot
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/health')"]
CMD ["uvicorn", "costpilot.main:app", "--host", "0.0.0.0", "--port", "8000"]
