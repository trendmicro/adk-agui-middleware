# Security Policy

## Supported Versions

Releases are published from `main`.

## Reporting a Vulnerability

- Please open a GitHub Security Advisory (preferred) or email the maintainers listed in `pyproject.toml`.
- We will acknowledge receipt within a reasonable time and coordinate a fix and disclosure timeline.

## Secrets and Credentials

- Do not commit secrets (tokens, passwords, API keys). Use environment variables or a secret manager.
- GitHub Secret Scanning is enabled for public repositories; please monitor and remediate alerts promptly.
- Optional pre-commit/CI tools like `gitleaks` can be added to block leaking secrets in PRs.

## Code Scanning

- CodeQL is configured to run on push/PR and a weekly schedule (see `.github/workflows/codeql.yml`).
- Bandit runs in CI; fix high severity findings before merging.

## Dependency Security

- Dependabot monitors ecosystem and GitHub Actions (see `.github/dependabot.yml`).
- Address security advisories under: Repository Settings → Security → Dependabot/Dependency alerts.

## Responsible Disclosure

We appreciate responsible disclosure and will make a best effort to fix security issues quickly and transparently.

