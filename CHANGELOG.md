# Changelog

所有用户可见的功能、API、配置、数据迁移和部署行为变化都应记录在这里。

## Unreleased
- Added F015 technical documentation and workflow navigation: the app now bundles three hash-verified offline manuals under `/technical-docs`, moves work-package details and achievement cards beneath their owning package, synchronizes package selection with URL state, returns package pages to the home route, and exposes the approved read-only 12-workflow/68-work-package map through `/api/v1/research-workflow-map`.
- Updated the local-isolated target-stack deployment script to keep dependency installation locked while supporting explicit offline uv cache mode, to select the newest run by state-file update time instead of directory-name order, and to make HTTP readiness polling uniformly back off.
- Added F014 release-candidate blank SQLite generation: preview-by-default tooling now creates the fixed legacy compatibility asset only through application initialization/migrations, proves `sqlite-schema-contract-v1` diff zero, enforces exact system-row and zero-business-row invariants, preserves the explicit immutable source, rejects sidecars/path overlap/hidden databases, and narrows Docker database inputs without changing PostgreSQL/Alembic as the default stack.
- Fixed local-isolated deployment proxying for the Vue root legacy compatibility bridge, so `/_legacy` reaches FastAPI/Flask directly instead of looping through Nginx directory redirects and causing browser NetworkError.
- Fixed independent QA blockers: disclosure updates now persist their audit record and show visible Chinese save-failure feedback; successful markdown attachment uploads return contract-valid responses matching DB/artifact state; explicit directory/preview-rail deep links override persisted collapsed state; and missing Context errors render in stable Chinese.
- Completed B5 pre-delivery integration: audited SDD UI/API parity, confirmed canonical-only Context user paths, corrected stale native/compat wording, updated the legacy deep-link test to target the explicit `/_legacy` route, and added the B5 audit/evidence document.
- Added the B4 native context deletion saga with prepare/commit one-time tickets, impact snapshots, archive or confirmed permanent attachment branches, rollback/cleanup compensation, durable operation/outbox status, and a native deletion page with explicit Chinese gates and errors.

- Added canonical achievement-attachment upload, metadata, download, safe preview, and OOXML image APIs with controlled artifact paths, hash/size/signature checks, transactional event/audit writes, delete-file outbox semantics, and Chinese upload/preview/download states.
- Added B2 native disclosure preference persistence with CAS/idempotent upserts, persisted UI sessions, one-time completion authorization nonce, transactional completion writes, achievement-card creation/importance controls, and Chinese concurrent/authorization/validation feedback.
- Completed the read-only B1 native Context v5 workbench with real catalog/workflow grouping, URL-backed filters and disclosure state, invalid-work-package fallback, progress and achievement-card summaries, explicit empty/error states, responsive keyboard-reachable controls, and browser regression coverage.

- Added canonical `/api/v1` Context detail and achievement-card creation paths, normalized all native context frontend calls to `/api/v1`, retained the legacy achievement-card alias, and added a PostgreSQL-backed native `/contexts/:contextId` B0 workbench skeleton with summary, progress, directory, and detail regions.
- Added the one-command target-stack lifecycle script with Docker Compose as the default runtime, explicit local-isolated mode, parameterized local tools and ports, isolated runtime evidence, health/readiness checks, and safe stop/clean boundaries.
- Fixed workflow selection to enforce `expected_version` CAS before mutation, so stale writers return 409 and concurrent same-version selections produce one success, one version increment, and one event.
- Added the P3A1 native PostgreSQL-backed card edit, importance toggle, soft delete, workflow selection, and session/nonce-gated completion APIs with CAS row versions, append-only events, operation audits, stable requestId errors, and generated OpenAPI/TypeScript contracts.
- Declared required request DTO bodies for all five P3A1 mutation routes, hardened card update/delete CAS against concurrent writers, and retained cross-binding nonce plus expired/revoked session regression coverage.

- Declared the P2A API error statuses and shared problem schema in OpenAPI; every P2A error now carries a stable code, detail, and per-request opaque requestId without changing success response shapes.
- Added the P2A native FastAPI/Pydantic contracts for listing/creating contexts, listing complete 68-workflow snapshots, and creating achievement cards.
- Added SQLAlchemy 2 PostgreSQL repository/UoW persistence for contexts, initial workflows, achievement cards, card create events, and operation audit events while preserving legacy response shapes and stable error codes.
- Added Vue 3/Vite frontend workspace with npm lockfile and separated development proxy.
- Added Flask/Waitress WSGI composition root, production static-asset serving, health endpoint, and SPA deep-link fallback.
- Preserved the existing SQLite-backed Handler as an explicit legacy fallback while Vue uses JSON APIs for catalog, contexts, workflows, cards, and controlled completion.
- Added runnable Python/Vue CI checks and corrected pytest discovery for `apps/api/tests`.
- Added the approved FastAPI composition root with Pydantic catalog DTOs, health/readiness contracts, error mapping, OpenAPI output, and the same-origin legacy DOM compatibility mount.
- Added uv-locked FastAPI, Pydantic Settings, SQLAlchemy 2, Alembic, psycopg, Uvicorn, HTTPX, Ruff, and mypy toolchain.
- Added a PostgreSQL 16 Alembic baseline covering all 46 schema-v6 tables, documented indexes, immutable-audit triggers, and PostgreSQL-only readiness/migration configuration.
- Added a read-only SQLite v6 source inspection tool and tests; it cannot transform or write source data.
- Added Nginx, API/Web Dockerfiles, and isolated Docker Compose topology with PostgreSQL, migration, API, and static web services.
- Added the Vue 3 TypeScript entry, Router catch-all shell, TanStack Query client, Element Plus provider, and TypeScript same-origin DOM compatibility bridge.
- Added the native `/contexts` route for PostgreSQL-backed context creation, 68-workflow progress, and achievement-card creation through TanStack Query and Element Plus.
- Added a read-only SQLite-to-PostgreSQL rehearsal importer with type conversion, sequence reset, row-count checks, and canonical row hashes for all 46 v6 tables.
- Corrected Nginx and the transitional ASGI adapter to proxy and preserve `/_legacy` paths so deployed deep links return the compatibility document instead of the SPA shell.
- Added the native `/work-packages` route as the first TanStack Query + Element Plus page while other deep links retain the compatibility bridge.
- Added Vitest/Playwright frontend checks and deterministic FastAPI OpenAPI export to generated TypeScript contract types.
- Added Playwright global setup/teardown that starts Vite and force-cleans the process tree so local and CI runs exit reliably.
- Expanded GitHub Actions into Python quality/tests, frontend quality/E2E, and deployment configuration validation jobs.
