# Indian Income Tax Calculator

A production-oriented, offline-capable **Indian Income Tax Calculator** desktop application for **FY 2026-27 (AY 2027-28)**. It compares the **Old** and **New** tax regimes, explains the calculation step by step, supports common deductions/capital gains, saves history locally, and exports PDF reports.

> **Disclaimer:** This application provides tax estimates for informational purposes only. It is **not** professional tax, legal, or financial advice. Tax rules are complex and subject to interpretation and change. Verify calculations against official Income Tax Department guidance or consult a qualified tax professional before filing.

## Screenshots

_Screenshots should be captured after running the app (desktop/web). Suggested captures: Dashboard, Income Inputs, Deductions, Comparison, Explanation, History._

- `docs/screenshots/dashboard.png` (add after running)
- `docs/screenshots/comparison.png`
- `docs/screenshots/explanation.png`

## Features

- **Old vs New Regime comparison** with recommended regime and savings.
- **Detailed income inputs**: salary, house property, capital gains, business/professional, other sources.
- **Deductions & exemptions**: 80C, 80D, 80G, 80TTA, 80TTB, 80CCD(1B), employer 80CCD(2), HRA, home loan interest (regime-aware eligibility).
- **Tax engine**: slab tax, 87A rebate, marginal relief, surcharge, marginal relief (approximate for high-income edge cases), 4% cess, 288B rounding.
- **Step-by-step explanation** of how tax was computed.
- **Visual dashboard**: income distribution, deduction breakdown, old vs new charts.
- **Profiles & history**: save taxpayer profiles and calculation history in local SQLite.
- **PDF export** of calculation/comparison report.
- **Dark/light mode** modern UI.
- **Offline-first**: no external APIs required for calculation.
- **Desktop packaging**: Electron + PyInstaller backend, Windows installer build scripts/workflow.

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts, Lucide React |
| Backend | Python, FastAPI, Pydantic, Uvicorn |
| Tax Engine | Pure Python, rule-driven JSON configs |
| Database | SQLite + SQLAlchemy (async) |
| PDF | ReportLab |
| Desktop | Electron, electron-builder |
| Backend packaging | PyInstaller |
| Tests | Pytest, FastAPI TestClient |

## Repository Structure

```text
indian-income-tax-calculator/
├── frontend/                  # React + TS + Vite UI
├── backend/
│   ├── app/
│   │   ├── api/routes/        # FastAPI endpoints
│   │   ├── core/              # config
│   │   ├── database/          # SQLAlchemy async DB
│   │   ├── models/            # ORM models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # tax/PDF/history services
│   │   └── tax_engine/        # pure calculation engine
│   │       └── rules/         # FY rule configs (JSON)
│   ├── tests/unit/            # tax engine tests
│   ├── tests/integration/     # API tests
│   ├── server.py              # PyInstaller entry point
│   └── pyinstaller_backend.spec
├── desktop/                   # Electron main/preload/builder config
├── scripts/                   # build scripts
├── docs/                      # architecture, tax methodology, API
├── exe/                       # Windows installer output (gitignored binaries)
└── .github/workflows/         # CI and Windows build workflow
```

## Architecture

```text
+---------------------------+        HTTP/JSON        +------------------------------+
|   React + TS Frontend     | <--------------------> | FastAPI Backend              |
|   Dashboard / Forms /     |   /api/tax/*           |  /api/tax/calculate          |
|   Charts / Explanation    |   /api/profiles/*      |  /api/tax/compare            |
+-------------+-------------+   /api/tax/history/*   |  /api/tax/export             |
              |                                      |  /api/tax/rules/{fy}         |
              |                                      +---------------+--------------+
              |                                                      |
              |                                      +---------------v--------------+
              |                                      | Pure Tax Engine              |
              |                                      | - regime calculators         |
              |                                      | - deductions/capital gains   |
              |                                      | - 87A/surcharge/cess         |
              |                                      | - explainable breakdown      |
              |                                      | - FY JSON rule configs       |
              |                                      +---------------+--------------+
              |                                                      |
              |                                      +---------------v--------------+
              |                                      | SQLite (local)               |
              |                                      | profiles + calculation       |
              |                                      | history                      |
              |                                      +------------------------------+
              |
+-------------v-------------+
| Electron Desktop Shell    |
| spawns backend, loads UI  |
| packages Windows installer|
+---------------------------+
```

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- npm 10+

### Backend

```bash
cd backend
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows
# .venv\Scripts\activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: `http://127.0.0.1:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite dev server: `http://127.0.0.1:5173` (proxies `/api` to backend).

### Run Tests

```bash
cd backend
source .venv/bin/activate  # or Windows equivalent
PYTHONPATH=. pytest tests -q
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/tax/years` | Supported financial years |
| GET | `/api/tax/rules/{financial_year}` | Rule config for FY |
| POST | `/api/tax/calculate` | Calculate tax (old/new/compare via request) |
| POST | `/api/tax/compare` | Compare old vs new regime |
| POST | `/api/tax/export` | Export PDF report |
| GET | `/api/tax/history` | Calculation history |
| GET | `/api/tax/history/{id}` | History item detail |
| DELETE | `/api/tax/history/{id}` | Delete history item |
| GET | `/api/profiles` | List profiles |
| POST | `/api/profiles` | Create profile |
| PUT | `/api/profiles/{id}` | Update profile |
| DELETE | `/api/profiles/{id}` | Delete profile |

## Building the Windows Executable

> **Environment note:** A genuine Windows `.exe` installer must be built on Windows (or a Windows CI runner). This Linux sandbox was used to implement and validate code/tests and to produce a Linux PyInstaller backend bundle as packaging validation.

### Windows (local)

```powershell
./scripts/build_windows.ps1
```

Output: `exe/Indian-Income-Tax-Calculator-Setup-<version>.exe`

### GitHub Actions

Run the `Build Windows Installer` workflow (`.github/workflows/build-windows.yml`) on `windows-latest`. The installer is uploaded as an artifact and copied to `exe/` in the workflow workspace.

### Linux backend bundle validation

```bash
./scripts/build_frontend.sh
./scripts/build_backend_linux.sh
```

## Tax Calculation Methodology

See [docs/TAX_METHODOLOGY.md](docs/TAX_METHODOLOGY.md) for details.

**Supported FY:** 2026-27 (AY 2027-28) initial config. Rules are stored in `backend/app/tax_engine/rules/fy_2026_27.json`.

Key implemented rules (verify before filing):
- New regime slabs: 0-4L Nil, 4-8L 5%, 8-12L 10%, 12-16L 15%, 16-20L 20%, 20-24L 25%, >24L 30%.
- Old regime slabs by age category.
- Standard deduction: ₹75,000 (new), ₹50,000 (old).
- 87A rebate with marginal relief (new regime) and old-regime rebate.
- 4% Health & Education cess.
- Surcharge with marginal relief (approximate in complex high-income edge cases).
- Capital gains: 111A, 112A, property LTCG, other LTCG/STCG, debt MF post-2023 slab treatment.
- Regime-aware deductions and HRA/home-loan treatment.

## Known Limitations

- **Estimator only**; not a filing tool.
- Capital gains rules are simplified for common cases; complex scenarios (carry-forward losses, set-off rules, exemptions under 54/54EC/54F, detailed grandfathering, etc.) require professional review.
- Surcharge marginal relief is approximated in some high-income/special-income combinations; verify edge cases.
- 80G is simplified to user-entered eligible donation amount; category-specific 80G limits need manual verification.
- The app does not store PAN/Aadhaar and should not be used to collect unnecessary sensitive data.
- Windows `.exe` installer generation requires Windows/electron-builder Windows runner.

## Privacy

- Data is stored locally in SQLite.
- No PAN/Aadhaar fields.
- No cloud sync by default.
- Calculations run locally.

## License

MIT — see [LICENSE](LICENSE).
