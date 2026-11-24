# Contributing

Thank you for contributing to the Indian Income Tax Calculator.

## Development Principles

- **Correctness first** for tax calculations. Any tax-rule change must include tests and source references.
- **Transparency**: explain assumptions, edge cases, and verification status.
- **Privacy**: do not add unnecessary collection/storage of sensitive personal data (PAN, Aadhaar, etc.).
- **Maintainability**: keep the tax engine pure and independent from UI/DB.

## Setup

1. Clone the repo.
2. Backend:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   PYTHONPATH=. pytest tests -q
   ```
3. Frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Making Tax Rule Changes

1. Update the relevant FY config in `backend/app/tax_engine/rules/`.
2. Add/update engine logic only if rule structure requires it.
3. Add unit tests in `backend/tests/unit/` with verified expected values.
4. Document sources and any assumptions in `docs/TAX_METHODOLOGY.md`.
5. If a rule cannot be verified, mark it as `requires_verification` in config and UI/docs.

## Pull Requests

- Keep PRs focused.
- Include tests for behavior changes.
- Update docs/README for user-facing changes.
- Do not commit build artifacts, local DBs, or secrets.

## Reporting Issues

Please include:
- Financial year / assessment year
- Regime (old/new/compare)
- Input values (redact personal info)
- Expected vs actual result
- Source/reference for expected rule
