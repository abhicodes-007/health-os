# Health OS MCP server

Gives Claude Desktop/Code read-only access to the database through approved views.

## Run

```bash
cd health-os
.venv/bin/python -m mcp_server.server   # stdio transport
```

## Connecting to Claude Desktop

In `~/Library/Application Support/Claude/claude_desktop_config.json` (replace
`${PROJECT_ROOT}` with the absolute path to your `health-os` checkout):

```json
{
  "mcpServers": {
    "health-os": {
      "command": "${PROJECT_ROOT}/.venv/bin/python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "${PROJECT_ROOT}"
    }
  }
}
```

After this, the chat understands prompts like "show the health summary", "cholesterol
trend over 2 years", "what is pending review", "what are the active diagnoses".

## Tools

| Tool | What it does |
|---|---|
| get_health_summary | deterministic summary (profile/allergies/diagnoses/medications/how recent labs are) |
| query_observations | values of an observation over N days; >90 days → weekly aggregation |
| get_timeline | chronology of health events |
| get_medications / get_diagnoses / get_allergies | current entities via approved views |
| list_pending_reviews | review queue (NOT approved) |
| sql_query | arbitrary READ-ONLY SELECT (read-only tx + 5s timeout, SELECT/WITH only) |

## Guardrails (in code, not in the prompt)

- **separate login role `health_readonly`** for reads (READONLY_DATABASE_URL): at the DB
  privilege level it sees ONLY approved views + the users stub; observations/audit_log/staging/
  critical_thresholds — permission denied; any write — ReadOnlySqlTransaction;
- reads go only through `v_*` approved views → the agent never sees unverified extraction;
- response limits (≤200 rows, aggregation over 90 days) → don't burn the context;
- sql_query in a read-only transaction + statement_timeout (5s);
- critical/pending values are visible only in `list_pending_reviews`, not in approved output;
- write tools (stage_lab_panel, record_*, approve_*) run on the main connection,
  approve is a separate explicit action (guardrail: create ≠ approve).

## Setting up the readonly role
```bash
# fill in READONLY_DB_PASSWORD and READONLY_DATABASE_URL in .env, then:
.venv/bin/alembic upgrade head
.venv/bin/python -m scripts.setup_readonly   # enables LOGIN + password
```
If it is not configured, reads go through the main connection (protection stays at the code
level: read-only tx in sql_query), but without DB-level isolation.
