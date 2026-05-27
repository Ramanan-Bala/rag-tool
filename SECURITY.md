# Security Policy

## Reporting an issue

If you find a security issue in repo-rag, please report it privately so it can be addressed before public disclosure.

Please do not open a public GitHub issue for security reports.

Email: `<your.email@example.com>`

We aim to acknowledge reports within 7 days and to ship a fix or mitigation as quickly as possible.

## Supported versions

During the 0.x development phase, only the latest minor release is supported with security fixes. Once 1.0 ships, the latest two minor releases will receive security updates.

## Scope

In scope:

- The `repo-rag` Python package and its CLI.
- The MCP server (`rag mcp-server`).
- The official Docker image at `ghcr.io/<YOUR_GITHUB_USERNAME>/repo-rag`.
- The git hook installer.

Out of scope:

- Third-party MCP clients (please report to the client maintainers).
- Bugs in upstream dependencies (`fastembed`, `lancedb`, `mcp`, etc.) - please report directly to those projects.
