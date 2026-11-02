# Architecture overview

CostPilot is a **modular monolith**: one backend app, split into modules with strict borders. It is as simple to run as one app, but stays as organised as separate services.

## The main parts

| Part | Job |
|---|---|
| **Caddy** | Front door. Gives free HTTPS and sends each request to the right service. |
| **Next.js** | The screens. |
| **FastAPI** | All business logic and the only part that touches data. |
| **Worker** | Does slow work, such as reading bills, in the background. |
| **Keycloak** | Handles sign-up, passwords and login pages. |
| **PostgreSQL** | Main database: users, billing records, summaries, chats and audit records. |
| **Amazon S3** | Private storage for original bill files. |
| **Qdrant** | Search over trusted cloud documentation. It holds no user data. |
| **Gemini** | Writes answers from facts we give it. |

All of them sit behind one web address, so the browser never has to deal with cross-site requests.

## Five ideas that shape the design

1. **Normal code does the maths.** The AI explains numbers. It never creates them.
2. **One format for all clouds.** Every bill is converted to FOCUS, so the rest of the app never needs to know which cloud it came from.
3. **Every piece of user data belongs to a workspace.** The database itself blocks access to other workspaces.
4. **Bills and documents are untrusted.** They are treated as data, never as instructions.
5. **Free, but production quality.** We pick the proper option that costs $0, and we are honest about the limits.

## Where to read next

- [Backend](backend.md)
- [Frontend](frontend.md)
- [Data model](data-model.md)
- [AI system](ai.md)
- [Security](security.md)
- [Multi-cloud](multi-cloud.md)
