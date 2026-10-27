# Supabase deployment checklist

This branch replaces local SQLite with persistent Supabase storage. **Do not merge until Streamlit secrets are configured.**

1. Open the Streamlit Community Cloud app dashboard, select the Dartford Land Finder app, and open **Settings → Secrets**.
2. Add the following TOML (replace placeholders privately; do not put secrets in GitHub):
   ```toml
   APP_PASSWORD = "choose-a-strong-private-password"
   SUPABASE_URL = "https://kvitdeeaiwnhsgrnzipg.supabase.co"
   SUPABASE_SERVICE_ROLE_KEY = "your-private-service-role-or-secret-key"
   ```
3. Obtain the server-side service-role key in Supabase project settings under API keys. Keep it confidential: it bypasses row-level security. Never expose it in public code or browser JavaScript.
4. The tables `sites` and `auction_sources` already exist in the Supabase project. They have RLS enabled and no public access policies.
5. After secrets are saved, merge the PR into `main`. Streamlit Community Cloud should rebuild from the GitHub default branch.
6. Test password entry, adding a test plot, refreshing, deleting, and attaching an auction source.

**Data migration:** Existing SQLite data is not automatically copied. Export CSV from the current live app before switching if you have saved listings.

**Not included:** automatic Rightmove/Zoopla/auction feeds, planning checks, or background refresh. The dashboard is a manual research tool.

**Security:** This is a simple single-password private dashboard, not multi-user authentication. Supabase credentials remain server-side.
