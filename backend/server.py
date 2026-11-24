"""PyInstaller-friendly entry point for the FastAPI backend."""
from __future__ import annotations

import argparse
import os

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Indian Income Tax Calculator backend")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument("--data-dir", default=os.getenv("TAX_CALC_DATA_DIR"))
    parser.add_argument("--frontend-dist", default=os.getenv("FRONTEND_DIST"))
    args = parser.parse_args()

    if args.data_dir:
        os.environ["TAX_CALC_DATA_DIR"] = args.data_dir
    if args.frontend_dist:
        os.environ["FRONTEND_DIST"] = args.frontend_dist

    # Import app after env vars are set
    from app.main import app

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
