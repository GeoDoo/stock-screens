# Cursor Rules — stock-screens (Project-Specific)

These rules apply to **this repo**: FastAPI backend (Python) + React/TS frontend + SQLite. They are designed around this project’s biggest risks: **API contract drift**, **provider variability/rate limits**, **finance-model correctness**, **async safety**, and **UI minimalism**.

## TDD Policy (Mandatory)
- **Backend**: add/modify pytest tests **first** (service-level preferred; API-level when contract changes).
- **Frontend**: add/modify vitest tests **first** for:
  - normalizers (`normalizeStockData`, etc.)
  - hooks that orchestrate fetch flows (if added)
  - components only when behavior matters
- Every change must have a failing test on the old code and passing on the new code.

## Regression Tests (Project-Specific)
All bugfixes must add a regression test for the exact failure mode:
- **Contract drift**: add tests asserting backend response shape + frontend normalizer/type expectations.
- **Provider failure**: test fallback logic (429/“premium”/not found) with deterministic mocks.
- **Missing financial history**: test the valuation/scenario paths return a clean error (not crash).
- **Async safety**: test sync provider calls are executed off the event loop (backend) when relevant.

## Finance/Model Guardrails (Non-negotiable)
- Always enforce: **discount_rate > terminal_growth_rate** in any DCF path (valuation/scenarios/MC-full).
- Never silently “invent” critical inputs:
  - If a fallback is used (tax rate, cost of debt floor, shares), the API response must clearly label it (e.g. `*_source: provider|fallback|user`).
- CapEx sign convention is fixed in this repo:
  - Ratios are **positive** as “% of revenue”
  - FCF uses `- capex`
  - Never double-negate.
- If historical series are missing/empty, return a **user-actionable error** (400) rather than crashing.

## Providers + Rate Limits (Rules)
- Provider calls must be:
  - isolated behind provider interfaces (`FMPProvider`, `YahooProvider`, `MassiveProvider`)
  - deterministic in tests (mock providers / mock HTTP)
- Rate limiter correctness:
  - don’t record calls before success unless explicitly tracking “attempts vs successes”
  - never let rate-limiter drift silently change UI behavior.

## Backend Architecture Rules (FastAPI)
- `main.py` should stay a thin wiring layer; new endpoints go into routers/modules if they’re not trivial.
- Avoid blocking I/O in `async def` endpoints:
  - any `yfinance` sync access must run via executor / provider method.
- Standardize errors:
  - consistent JSON shape `{ detail, code }`
  - 400 only for validation/user input
  - 429 for rate limits
  - 500 for unexpected errors

## Frontend Rules (React/TS)
- `App.tsx` must not grow further:
  - new network flows must go into a dedicated API layer or hooks.
- All API responses must pass through normalizers at the boundary.
- Types must match backend reality (OpenAPI is source-of-truth):
  - treat optional fields as optional (e.g. validation `impacts` until backend is unified).
- Minimal UI/UX:
  - prefer progressive disclosure (advanced options hidden)
  - warnings near fields (WACC missing, extreme margins, provider limited)
  - no noisy UI: calm colors, small components, consistent spacing.

## KISS/DRY Rules (Practical for this repo)
- KISS: prefer explicit code for valuation flows (clarity > abstraction).
- DRY only when there are ≥3 identical call-sites (common here: fetch error handling, provider selection, response normalization).
- When introducing helpers:
  - keep signatures small
  - keep tests at the feature level (don’t over-test helpers).

## Definition of Done (stock-screens)
- Backend: pytest green (new tests added for new behavior)
- Frontend: vitest green AND `npm run build` passes (tests alone don’t guarantee ship)
- No API contract drift: types + normalizers aligned
- No event-loop blocking introduced in backend
- UX states present: loading/error/empty for new flows

## GitHub Flow (Rebase-Only Standard)
- **Branch from `main`** for every change: `feat/...`, `fix/...`, `chore/...`, `refactor/...`.
- Keep branches **small and short-lived** (aim: merge within 1–2 days).
- Open a PR early (draft is fine) and keep it focused (one behavior change per PR).

- **Rebase-only integration**
  - Keep your branch up to date by rebasing on `main` frequently.
  - Maintain **linear history**: no merge commits, no squash merges.
  - Before final push: interactive rebase to clean commits (drop noise, fix messages), but **do not rewrite history** after review starts unless agreed.
  - Use `--force-with-lease` only when rebasing a PR branch.

- **Required before PR is approved/landed**
  - Backend: `pytest` passes
  - Frontend: `vitest` passes AND `npm run build` passes
  - No API contract drift (types/normalizers updated if backend changed)
  - Regression test included for bugfixes

- **PR description must include**
  - **What changed** (user-visible)
  - **Why** (bug/feature)
  - **How tested** (commands + key tests)
  - **Risk** (contracts, provider fallback, rate-limit behavior)

- After landing: pull `main` and do a quick smoke run.