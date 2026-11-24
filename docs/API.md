# API Documentation

Base URL (dev): `http://127.0.0.1:8000`

## Health

### `GET /api/health`
Returns app status.

## Tax

### `GET /api/tax/years`
Returns supported financial years.

### `GET /api/tax/rules/{financial_year}`
Returns rule config for a financial year (e.g. `2026-27`).

### `POST /api/tax/calculate`
Calculates tax for the requested regime (`old`, `new`, or `compare`).

Request body: `TaxCalculationRequest` (see `backend/app/schemas/tax.py`).

### `POST /api/tax/compare`
Compares old vs new regime. Same request body; regime forced to compare.

### `POST /api/tax/export`
Returns a PDF report (`application/pdf`).

## History

### `GET /api/tax/history?limit=50`
List saved calculations.

### `GET /api/tax/history/{id}`
Get saved calculation input + result.

### `DELETE /api/tax/history/{id}`
Delete saved calculation.

## Profiles

### `GET /api/profiles`
List taxpayer profiles.

### `POST /api/profiles`
Create profile.

### `PUT /api/profiles/{id}`
Update profile.

### `DELETE /api/profiles/{id}`
Delete profile.
