# Architecture

## Overview

The application is a local-first desktop/web system with a **pure Python tax engine** at its core.

```text
Frontend (React/TS)
    -> REST API (FastAPI)
        -> Tax Service (validation/orchestration)
            -> Tax Engine (pure Python, rule configs)
            -> SQLite (profiles/history)
            -> PDF Service (ReportLab)
```

## Components

### Frontend (`frontend/`)
- React + TypeScript + Vite
- Tailwind CSS for styling
- Recharts for visualizations
- Lucide icons
- Communicates with backend over `/api/*`

### Backend (`backend/app/`)
- **API routes**: tax calculation, comparison, rules, history, profiles, export, health.
- **Pydantic schemas**: request/response validation.
- **Services**: convert API payloads to engine inputs, persist history, generate PDFs.
- **Database**: SQLite via SQLAlchemy async; stores profiles and calculation history.
- **Core config**: data directory, DB URL, CORS.

### Tax Engine (`backend/app/tax_engine/`)
- Pure functions; no DB or HTTP dependencies.
- Rule-driven via JSON files in `rules/`.
- Outputs detailed breakdown for explainability.
- Handles regime-specific slabs, deductions, 87A, surcharge, cess, special-rate capital gains.

### Desktop (`desktop/`)
- Electron main process spawns the backend executable/script.
- Waits for `/api/health` before loading UI.
- Loads UI from local backend URL so frontend and API are same-origin.
- Stops backend on app exit.

## Data Flow

1. User enters inputs in UI.
2. UI sends `TaxCalculationRequest` to `/api/tax/calculate` or `/api/tax/compare`.
3. Backend validates input, converts to engine dataclasses.
4. Tax engine loads FY rules, computes regime(s), returns breakdown.
5. Backend optionally saves history to SQLite.
6. UI renders dashboard, comparison, charts, and explanation.
7. PDF export endpoint recalculates and returns a generated PDF.

## Packaging

- **Frontend**: Vite build to `frontend/dist`.
- **Backend**: PyInstaller bundles `server.py` + `app` + rule JSONs.
- **Electron**: packages frontend dist and backend bundle as extra resources; NSIS installer on Windows.
