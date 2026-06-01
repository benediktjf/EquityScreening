# Screenshot Guide

This project is API-first, so the most useful portfolio screenshots are the CLI table, the FastAPI docs page, and one JSON response.

## Recommended Screenshots

1. **CLI screen output**

   ```bash
   python run_screen.py --limit 10
   ```

   Save as: `docs/screenshots/cli-screen.png`

2. **FastAPI interactive docs**

   ```bash
   uvicorn euro_equity_intelligence.api:app --reload
   ```

   Open `http://127.0.0.1:8000/docs` and capture the endpoint list.

   Save as: `docs/screenshots/api-docs.png`

3. **Single company JSON response**

   Open `http://127.0.0.1:8000/companies/ASML.AS` or run:

   ```bash
   curl "http://127.0.0.1:8000/companies/ASML.AS"
   ```

   Save as: `docs/screenshots/company-json.png`

## macOS Screenshot Tips

- Press `Cmd + Shift + 4` to select an area.
- Press `Cmd + Shift + 5` for screenshot options.
- Keep terminal width wide enough for the CLI table before capturing.

## Notes

Screenshots are intentionally not committed by default because live `yfinance` output changes over time. The `docs/screenshots/` folder exists as the target location for fresh captures.
