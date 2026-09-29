# Security policy

health-os stores medical data, so security reports get priority.

## Reporting a vulnerability

**Please do not open a public issue.** Report privately via GitHub:
[Security → Report a vulnerability](https://github.com/andronaft/health-os/security/advisories/new).

Include what an attacker could do, the steps to reproduce, and the affected version/commit.
Never attach real medical data — reproduce with the demo patient (`python -m seed.demo`) or
synthetic values.

You can expect an acknowledgement within 7 days. Once a fix is released, you will be credited
in the advisory unless you prefer otherwise.

## Supported versions

Only the latest commit on `main` receives security fixes.

## Scope

In scope, for example:
- a read tool or `sql_query` reaching data outside the approved views, or writing through the
  read-only role;
- pending/unverified values leaking into approved output;
- prompt injection in a document that makes the agent approve, write or exfiltrate data;
- a critical value that fails to alert, or a bypass of the drug-interaction / crisis guardrails;
- secrets or medical data ending up in logs, alerts or git.

Out of scope: vulnerabilities in the MCP client or model you connect, and setups that expose
Postgres to a network (the default binds to localhost only).

## Hardening checklist for users

- Keep the defaults: ports bound to `127.0.0.1`, `.env` out of git.
- Configure the `health_readonly` role (see `mcp_server/README.md`).
- Encrypt the disk; keep backups encrypted (`scripts/backup.sh` uses restic).
