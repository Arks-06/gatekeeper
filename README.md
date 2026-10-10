# Gatekeeper

An agentic IT-security ticket triage and remediation system. Gatekeeper ingests alerts from a Jira webhook, investigates them through MCP tools, uses an LLM to score risk and propose a remediation, and then either executes low-risk actions autonomously or pauses for human approval. Every action passes a whitelist and identity guardrail layer before anything is executed.

Built with FastAPI, LangGraph, PostgreSQL, Docker Compose, and an MCP tool server, with a Prometheus/Grafana/Loki monitoring stack and a Streamlit review UI.

## Quick Start

```bash
# 1. Configure environment (a free Groq API key is required for the LLM step)
cp backend/.env.example backend/.env
# edit backend/.env and set GROQ_API_KEY

# 2. Start the full stack
docker compose up --build -d

# 3. Send a test alert (the response includes a thread_id)
uv run python simulate_alert.py

# 4. Review it in the UI at http://localhost:3000, or approve via the API:
curl -X POST http://localhost:8000/api/v1/tickets/<thread_id>/approve
```

Low-risk tickets (risk score below 70) resolve on their own. Higher-risk tickets stop at the approval step until a human approves or rejects them.

## How It Works

Each ticket moves through a LangGraph state machine:

```mermaid
flowchart TD
    A["Jira webhook"] --> B["investigate"]
    B --> C["synthesize: LLM risk score and proposed action"]
    C -->|"risk >= 70"| H["human approval (interrupt)"]
    C -->|"risk < 70"| R["remediate"]
    C -->|"error"| F["fallback"]
    H -->|"approved"| R
    H -->|"rejected"| E(["end"])
    H -->|"error"| F
    R --> J["jira sync"]
    R -->|"error"| F
    J --> E
    J -->|"failed"| F
    F --> E
```

1. **Investigate.** Every ticket queries Active Directory, then runs alert-type-specific lookups through the MCP server (for example VPN logs for impossible travel, email headers for phishing, endpoint scan results for malware).
2. **Synthesize.** An LLM (via Groq, with structured output enforced by `instructor`) produces a summary, a risk score from 1 to 100, and a proposed action. The proposed action must come from the whitelist for that alert type. A missing risk score defaults to 100, which forces human review.
3. **Route.** A risk score of 70 or above pauses the workflow at a LangGraph `interrupt` until a human approves or rejects. Below 70, the action executes autonomously.
4. **Remediate.** The proposed action passes the guardrail checks, then executes through an MCP tool.
5. **Sync and log.** The outcome is pushed back to Jira, and every decision is written to the `audit_logs` table. Workflow state is checkpointed in PostgreSQL, so a paused workflow survives restarts and resumes exactly where it stopped.
6. **Fallback.** Any error at any stage parks the ticket in a human-review state instead of failing silently.

### Guardrails

`graph/guardrails.py` validates every action before execution:

- **Whitelist.** Each alert type has a fixed set of permitted actions. Anything else is rejected, regardless of what the LLM proposes.
- **Protected entities.** Actions targeting protected accounts (`ceo@`, `cfo@`, `admin@`) are only allowed when the reporter is the designated security admin.
- **Identity verification.** A password reset requires the reporter to be the target user or the system monitor.

### Supported Alert Types

| Alert type | Whitelisted actions |
|---|---|
| `account_lockout` | `unlock_account`, `reset_user_password` |
| `impossible_travel` | `force_mfa_reauth`, `suspend_account` |
| `phishing_report` | `quarantine_email`, `suspend_account` |
| `malware_detected` | `isolate_host`, `quarantine_file` |
| `suspicious_behavior` | `monitor_account`, `suspend_account`, `revoke_tokens` |
| `mass_download` | `suspend_account`, `revoke_tokens` |

### Ticket Statuses

| Status | Meaning |
|---|---|
| `pending` | Ingested, in progress or waiting at the approval step |
| `auto_resolved` | Low risk, executed autonomously |
| `human_approved` | A human approved; execution in progress |
| `human_rejected` | A human rejected; no action taken |
| `resolved` | Approved by a human and executed successfully |
| `escalated` | Execution failed or was blocked by a guardrail; needs manual review |

## Architecture and Simulation Scope

*This is a portfolio project. To run locally without enterprise credentials, external systems are simulated behind the MCP tool interface:*

- **Investigation tools** (`query_active_directory`, `query_vpn_logs`, `query_email_headers`, `query_endpoint_scan_results`, and the other type-specific lookups) return synthetic data instead of querying a live directory, VPN, email gateway, or EDR platform.
- **Remediation tools** (`unlock_account`, `reset_user_password`, `force_mfa_reauth`, `suspend_account`, `quarantine_email`, `isolate_host`, `quarantine_file`, `revoke_tokens`, `monitor_account`) are stubs that return a success payload. No real identity or endpoint changes are made.
- **Jira synchronization** posts to a mock endpoint in the backend (`/api/issue/{ticket_id}/resolve`) instead of a live Atlassian instance.

The graph logic only depends on the MCP tool interface, so a real connector (Okta, Entra ID, a real SIEM) could replace a stub without changing the workflow.

## Components

| Component | Purpose |
|---|---|
| **backend** | FastAPI service: webhook ingestion, approval endpoints, CRUD, audit logging, Prometheus metrics, and the MCP tool server. |
| **frontend** | Streamlit UI for reviewing tickets and approving or rejecting proposed actions. Intentionally minimal. |
| **graph** | Workflow logic: LangGraph state machine, LLM synthesis, guardrails, Jira sync, and fallback handling. |
| **monitoring** | Prometheus, Loki, and Grafana with pre-provisioned dashboards. |
| **eval** | Evaluation set, runner, results, and failure analysis. |
| **simulate_alert.py** | Sends a synthetic alert (from `payload.json`) to the webhook. |

## Features

- FastAPI backend with Alembic migrations, async SQLAlchemy models, and Prometheus metrics
- LangGraph workflow with a human-in-the-loop interrupt and PostgreSQL-backed checkpointing
- Risk-based routing: low-risk actions execute autonomously, high-risk actions require approval
- Whitelist, protected-entity, and identity guardrails enforced before any action
- Audit log of every AI proposal, human decision, and execution result
- Background resumption of paused workflows through FastAPI `BackgroundTasks` (`tasks.py`)
- Observability through Prometheus metrics, Loki logs, and pre-provisioned Grafana dashboards
- Local containerized setup with Docker Compose
- CI pipeline (`.github/workflows/ci.yml`) running on every push

## Project Structure

```
gatekeeper/
├── .github/workflows/ci.yml
├── backend/
│   ├── alembic/ (env.py, versions/)
│   ├── tests/
│   ├── .env.example
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── crud.py
│   ├── database.py
│   ├── main.py
│   ├── mcp_server.py
│   ├── metrics.py
│   ├── models.py
│   ├── pyproject.toml
│   ├── schemas.py
│   ├── tasks.py
│   └── uv.lock
├── eval/
│   ├── eval_runner.py
│   ├── gatekeeper_eval_tickets.csv
│   ├── results.md
│   └── failure_analysis.md
├── frontend/
│   ├── Dockerfile
│   ├── app.py
│   ├── main.py
│   ├── pyproject.toml
│   └── uv.lock
├── graph/
│   ├── fallback.py
│   ├── guardrails.py
│   ├── jira_sync.py
│   ├── llm_schemas.py
│   ├── pyproject.toml
│   ├── state.py
│   ├── uv.lock
│   └── workflow.py
├── monitoring/
│   ├── grafana/provisioning/ (dashboards/, datasources/)
│   ├── loki/local-config.yaml
│   └── prometheus/prometheus.yml
├── docker-compose.yml
├── payload.json
└── simulate_alert.py
```

## Configuration

The backend reads its environment from `backend/.env` (see `docker-compose.yml`). Copy the template and fill in your key:

```bash
cp backend/.env.example backend/.env
```

```dotenv
# Backend
# Inside Docker use postgres:5432. If running the backend directly on the host, use localhost:5433.
DATABASE_URL=postgresql+asyncpg://admin:securepassword@postgres:5432/gatekeeper_db
# Inside Docker use mcpserver:9000. On the host, use localhost:9000.
MCP_INTERNAL_URL=http://mcpserver:9000/sse

# LLM (free key from https://console.groq.com)
GROQ_API_KEY=your_groq_api_key_here

# Jira sync (points at the built-in mock endpoint)
JIRA_API_URL=http://backend:8000/api
JIRA_API_KEY=mock_key
```

The frontend's `BACKEND_URL` and `MCP_URL` are set in `docker-compose.yml`. If you run the frontend outside Docker, set `BACKEND_URL=http://localhost:8000` and `MCP_URL=http://localhost:9000/sse`.

> The credentials above are development defaults from `docker-compose.yml`. The compose file also enables anonymous Grafana viewer access. This setup is for local use only.

## Prerequisites

| Requirement | Minimum version | How to obtain |
|---|---|---|
| **Python** | 3.11+ (the code uses `datetime.UTC`) | `pyenv install 3.11` or system package |
| **uv** | latest | `pip install uv` |
| **Docker** | 24.0+ | <https://docs.docker.com/get-docker/> |
| **Docker Compose** (v2 plugin) | 2.20+ | bundled with Docker Desktop |
| **Groq API key** | n/a | <https://console.groq.com> |
| **Git** | any | <https://git-scm.com/downloads> |

## Installation

```bash
git clone https://github.com/Arks-06/gatekeeper.git
cd gatekeeper
pip install uv
```

Install dependencies per component (each has its own `uv`-managed virtual environment):

```bash
cd backend && uv sync
cd ../frontend && uv sync
cd ../graph && uv sync
```

To build the Docker images instead:

```bash
docker compose build
```

## Usage

### Full stack with Docker Compose (recommended)

```bash
docker compose up --build -d
```

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| Frontend (Streamlit) | http://localhost:3000 |
| Grafana | http://localhost:4000 |
| Prometheus | http://localhost:9090 |
| Loki | http://localhost:3100 |
| MCP server | http://localhost:9000 |
| PostgreSQL | localhost:5433 |

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

### Local development without containers for the app

Run PostgreSQL in Docker, and the rest on the host (remember to switch the URLs in `.env` to `localhost`, as noted above):

```bash
docker compose up -d postgres

# Terminal 1: MCP tool server
cd backend && uv run python mcp_server.py

# Terminal 2: backend
cd backend && uv run fastapi dev main.py --port 8000

# Terminal 3: frontend
cd frontend && uv run streamlit run app.py --server.port=8501
```

The local frontend is then at http://localhost:8501.

### Send a test alert

```bash
uv run python simulate_alert.py
```

This posts the payload in `payload.json` to the webhook. The response includes a `thread_id`, which you can use to approve or reject a paused ticket:

```bash
curl -X POST http://localhost:8000/api/v1/tickets/<thread_id>/approve
curl -X POST http://localhost:8000/api/v1/tickets/<thread_id>/reject
```

Other useful endpoints: `GET /api/v1/graph/schema` (workflow as a Mermaid diagram) and `GET /api/v1/graph/state/{thread_id}` (current workflow state for a ticket).

## Testing and CI

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push:

- `ruff` for linting
- `mypy` for type checking
- `pytest` for unit tests

Run the same checks locally from the backend directory:

```bash
cd backend
uv run ruff check .
uv run mypy .
uv run pytest
```

## Evaluation

Gatekeeper was evaluated against a 16-ticket synthetic set covering all six alert types across four categories: clean low-risk, clean high-risk, ambiguous, and adversarial.

| Metric | Result |
|---|---|
| Outcome matched expected | 12 / 16 (75%) |
| Proposed action matched expected | 13 / 16 (81%) |
| Adversarial tickets blocked as expected | 2 / 3 |

The evaluation confirmed the protected-entity guardrail and found a real gap: the identity check only applies to password resets, so an unauthorized reporter's request went through when the model proposed a different action. It also surfaced a risk-calibration issue and run-to-run variance in borderline risk scores.

- Per-ticket results and limitations: [`eval/results.md`](eval/results.md)
- Failure analysis: [`eval/failure_analysis.md`](eval/failure_analysis.md)
- Test set and runner: [`eval/`](eval/)

To reproduce, start the stack and run `uv run python eval/eval_runner.py` from the repository root.

## Known Limitations

- **Identity guardrail scope.** The identity-mismatch check only covers `reset_user_password`. Other account-mutating actions are not covered by it.
- **Risk score consistency.** The LLM-generated risk score is not deterministic, so borderline tickets can land on either side of the 70-point threshold between runs.
- **MFA over-credit.** The risk prompt can over-weight a successful MFA when a login also comes from a new device or location.
- **No "no action needed" outcome.** The whitelist has no explicit benign-closure action for investigations that conclude nothing is wrong.
- **Simulated integrations.** All external systems are simulated, so evaluation results describe behavior on constructed scenarios, not real-world accuracy.
- **Small evaluation set.** 16 tickets exposes design gaps but is not large enough for the percentages to be statistically meaningful.