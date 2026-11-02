# Backend

The backend is in `apps/api`, using Python and FastAPI.

## Folder layout

```
apps/api/src/costpilot/
  main.py            Starts the web API
  worker.py          Starts the background worker
  composition.py     Connects modules to real tools
  shared/            Settings, logging and errors, used by all modules
  modules/
    billing/
      contracts.py   The public interface of this module
      domain/        Pure business rules
      application/   Steps of each use case, plus interfaces
      infrastructure/ Real tools: Postgres, S3, Gemini
      api/           Routes
    identity/ documents/ analytics/ recommendations/
    assistant/ knowledge/ audit/
```

## The four layers

Code only points inward:

```
api  →  application  →  domain  ←  infrastructure
```

**Example: uploading a bill.**

| Layer | What it does |
|---|---|
| `api` | Receives the file and calls the use case |
| `application` | `UploadDocument`: runs the steps and asks for a `FileStorage` |
| `domain` | Decides if the file is allowed |
| `infrastructure` | `S3FileStorage`: the real storage code |

Because the use case only knows the `FileStorage` interface, S3 can be replaced by a local folder in development, or by any other storage, without changing the business logic. It also makes tests fast.

## Rules between modules

A module may only import another module through its `contracts.py` file. Everything else inside a module is private.

## How the rules are enforced

| Rule | Checked by |
|---|---|
| Layers point the right way | `lint-imports` (settings in `pyproject.toml`) |
| Domain code does not use outside tools | `lint-imports` |
| Modules only use each other's contracts | `tests/architecture/test_module_boundaries.py` |

When a new library is added that the domain must not use, such as SQLAlchemy, add it to `forbidden_modules` in `pyproject.toml`.

## The background worker

Reading a bill is slow, so it does not happen during the upload.

1. The upload saves the file, then saves the document and a job in one transaction.
2. `worker.py` claims the next job with `FOR UPDATE SKIP LOCKED`, so two workers never take the same job.
3. `JobRunner` does the work and records the result.

| What goes wrong | What happens |
|---|---|
| The file is bad | It fails at once, and the user sees the reason |
| A temporary problem | It retries, waiting longer each time, up to `JOB_MAX_ATTEMPTS` |
| The worker crashes | The job goes back in the queue after `JOB_STALE_MINUTES` |
| The document was deleted | The job is skipped |

The `jobs` table has no Row-Level Security, because the worker must see every workspace. It only holds IDs and error class names, never user data.

## Settings and errors

- All settings are in `shared/config.py` and come from environment variables.
- All API errors have the same shape:

```json
{ "error": { "code": "file_too_large", "message": "That file is too large." } }
```

Unexpected errors are logged, and the user only sees a safe general message.
