# Treasures — Streamlit Web App

This is a Streamlit web app version of the **Daily Free Stuff Finder**.

## Files
- `treasures_streamlit_app.py` — main Streamlit app
- `requirements_treasures_streamlit.txt` — Python package list

## Run locally
```bash
pip install -r requirements_treasures_streamlit.txt
streamlit run treasures_streamlit_app.py
```

## What it does
- Searches the configured source sites for likely listings
- Displays findings in a web UI
- Lets you filter results by source category and keyword
- Exports the current run to `treasures.xlsx`

## Included sources
- Contest Reminder
- Contest Bee
- Freebie Shark Sweepstakes
- The Freebie Guy Sweepstakes
- Daily Free Stuff USA
- TrySpree

## Notes
- The app is designed to run with internet access.
- Because source site layouts can change, the keyword filters and scraping logic may occasionally need tuning.
- Respect site terms and avoid excessive automated request volume.
