# Backend

The backend is in `apps/api`, using Python and FastAPI.

## Folder layout

```
apps/api/src/costpilot/
  main.py            Connects everything together
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

## Settings and errors

- All settings are in `shared/config.py` and come from environment variables.
- All API errors have the same shape:

```json
{ "error": { "code": "file_too_large", "message": "That file is too large." } }
```

Unexpected errors are logged, and the user only sees a safe general message.
