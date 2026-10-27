# Dartford Land Finder — private Streamlit prototype

## Run locally
1. Install Python 3.10+.
2. Run `pip install -r requirements.txt`.
3. Set an environment variable `APP_PASSWORD` to a strong unique password.
4. Run `streamlit run app.py`.

## Free cloud deployment
1. Create a **private** GitHub repository containing `app.py` and `requirements.txt`.
2. Deploy it using Streamlit Community Cloud (check current free-tier availability and policies).
3. In Streamlit app settings → Secrets, add `APP_PASSWORD = "your-unique-strong-password"`.
4. Do not share the app URL or password. Password protection in this prototype is a basic single-user gate, not full identity management.
5. Local SQLite is **ephemeral on many cloud hosts**. Export CSV regularly. For reliable persistence, replace SQLite with Supabase or another managed database.

## Included
- Single-user password gate
- Manual property entry and deletion
- Price, plot size and Dartford radius filters
- Map, scoring, listing links and CSV export
- Planning due diligence checklist

## Not included
- Live Rightmove / Zoopla data ingestion, scheduled searches or email alerts
- Verified planning permissions, flood status, Green Belt boundaries or development costs
- Production-grade authentication, backup and persistent cloud storage

Only connect listing feeds when permitted by the data provider.

## Auction sources update
The new Auction sources tab links auction lots to existing plot records. It prevents exact duplicate auction URLs and allows multiple auction-house references for one plot. It does **not** yet automatically detect duplicate plots entered separately under Add a plot. No auction data feed, daily automation, or cloud deployment is connected. SQLite storage may be temporary on free cloud hosts.
