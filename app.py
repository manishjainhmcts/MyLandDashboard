import os
import hmac
import math
from datetime import date
from urllib.parse import quote
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Dartford Land Finder", page_icon="🏡", layout="wide")
st.title("Dartford Land Finder")
st.caption("Private land research · Dartford 15-mile radius · £200,000 land budget · four-bedroom home + private badminton hall")

def setting(name):
    return st.secrets.get(name, os.environ.get(name, ""))

password = setting("APP_PASSWORD")
if not password:
    st.error("Set APP_PASSWORD in Streamlit app secrets before use.")
    st.stop()
if not hmac.compare_digest(st.text_input("Dashboard password", type="password"), password):
    st.info("Enter your private password to continue.")
    st.stop()

api_url = setting("SUPABASE_URL").rstrip("/")
api_key = setting("SUPABASE_SERVICE_ROLE_KEY")
if not api_url.startswith("https://") or not api_key:
    st.error("Supabase connection not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in Streamlit secrets.")
    st.stop()

def api(table, method="GET", params=None, payload=None):
    headers = {"apikey": api_key, "Content-Type": "application/json", "Prefer": "return=representation"}
    # Modern sb_secret_* API keys are not JWTs and must not be used as Bearer tokens.
    if not api_key.startswith("sb_secret_"):
        headers["Authorization"] = "Bearer " + api_key
    response = requests.request(method, api_url + "/rest/v1/" + table, headers=headers, params=params, json=payload, timeout=20)
    response.raise_for_status()
    return response.json() if response.content else []

def get_rows(table, params=None):
    return api(table, params={"select": "*", "order": "created_at.desc", **(params or {})})

def distance(lat, lon):
    lat1, lon1 = 51.4462, 0.2169
    a = math.sin(math.radians(lat-lat1)/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat))*math.sin(math.radians(lon-lon1)/2)**2
    return 3958.8 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def listings():
    df = pd.DataFrame(get_rows("sites"))
    if not df.empty:
        df["distance_miles"] = df.apply(lambda r: round(distance(float(r.latitude), float(r.longitude)), 1), axis=1)
        df["score"] = df.apply(lambda r: (40 if r.price <= 200000 else 0) + (25 if r.distance_miles <= 15 else 0) + (20 if r.planning == "Residential permission" else 10 if r.planning == "Potential (unverified)" else 0) + (15 if r.area_acres >= .25 else 0), axis=1)
    return df

with st.sidebar:
    st.header("Search criteria")
    max_price = st.number_input("Maximum land price (£)", min_value=0, value=200000, step=10000)
    max_distance = st.slider("Radius from Dartford (miles)", 1, 30, 15)
    min_acres = st.number_input("Minimum plot size (acres)", min_value=0.0, value=0.25, step=0.05)
    st.caption("Planning, flood risk, Green Belt and suitability for a separate sports hall require independent checks.")

try:
    sites = listings()
except requests.HTTPError as exc:
    status = exc.response.status_code if exc.response is not None else "unknown"
    st.error(f"Supabase API returned HTTP {status}. Check SUPABASE_URL and the private API key in Streamlit secrets. For a new Supabase secret key, use the sb_secret_... value; for a legacy key, use service_role.")
    st.stop()
except requests.RequestException:
    st.error("Network connection to Supabase failed. Verify SUPABASE_URL and try again.")
    st.stop()

explore, add, guidance, auctions, discovery = st.tabs(["Explore plots", "Add a plot", "Planning & guidance", "Auction sources", "Find land"])
with explore:
    if sites.empty:
        st.info("No plots saved yet. No automatic Rightmove, Zoopla or auction feed is connected.")
    else:
        filtered = sites[(sites.price <= max_price) & (sites.distance_miles <= max_distance) & (sites.area_acres >= min_acres)]
        a,b,c = st.columns(3)
        a.metric("Matching plots", len(filtered))
        b.metric("Lowest asking price", f"£{filtered.price.min():,.0f}" if len(filtered) else "—")
        c.metric("Residential permission", int((filtered.planning == "Residential permission").sum()))
        if len(filtered):
            st.map(filtered.rename(columns={"latitude": "lat", "longitude": "lon"})[["lat", "lon"]])
            cols = ["name","location","price","area_acres","distance_miles","planning","green_belt","flood_risk","score","listing_url","notes"]
            st.dataframe(filtered[cols].sort_values("score", ascending=False), use_container_width=True, hide_index=True, column_config={"listing_url": st.column_config.LinkColumn("Listing")})
        st.download_button("Export plots CSV", sites.to_csv(index=False), "dartford_plots.csv", "text/csv")
        with st.expander("Delete saved plot"):
            choices = {f"{int(r.id)} · {r['name']}": int(r.id) for _,r in sites.iterrows()}
            chosen = st.selectbox("Plot", list(choices))
            if st.button("Delete selected plot"):
                try:
                    api("sites", "DELETE", {"id": "eq." + str(choices[chosen])})
                    st.rerun()
                except requests.RequestException as e:
                    st.error("Delete failed; please try again.")

with add:
    with st.form("new_site"):
        name = st.text_input("Plot name / reference")
        location = st.text_input("Area / address")
        price = st.number_input("Asking price (£)", min_value=0, step=5000)
        acres = st.number_input("Area (acres)", min_value=0.0, step=0.05, format="%.2f")
        lat = st.number_input("Latitude", value=51.4462, format="%.6f")
        lon = st.number_input("Longitude", value=0.2169, format="%.6f")
        planning = st.selectbox("Planning", ["Unknown","Potential (unverified)","Residential permission","No residential permission"])
        green = st.selectbox("Green Belt", ["Unknown","Yes","No"])
        flood = st.selectbox("Flood risk", ["Unknown","Potential risk","No known risk (unverified)"])
        access = st.text_input("Road access")
        utilities = st.text_input("Utilities")
        url = st.text_input("Original listing URL")
        notes = st.text_area("Notes / concerns")
        submitted = st.form_submit_button("Save plot")
    if submitted:
        if not name.strip():
            st.error("Enter a plot name.")
        elif url and not url.startswith(("https://","http://")):
            st.error("Listing URL must start with http:// or https://")
        else:
            record = dict(name=name.strip(),location=location,price=price,area_acres=acres,latitude=lat,longitude=lon,planning=planning,green_belt=green,flood_risk=flood,access=access,utilities=utilities,listing_url=url.strip() or None,notes=notes)
            try:
                api("sites", "POST", payload=record)
                st.success("Plot saved to Supabase.")
            except requests.HTTPError as e:
                st.error("Could not save plot. Check for a duplicate listing URL.")

with guidance:
    st.markdown("""
    - **Planning:** Verify residential consent and permission for a separate tall sports hall.
    - **Green Belt and flood risk:** Check official maps independently.
    - **Site suitability:** Confirm access, utilities, covenants, ground conditions and badminton hall clearances.
    - **Budget:** £200,000 land ceiling; build finance is not guaranteed.
    """)
    st.link_button("Planning Portal", "https://www.planningportal.co.uk/")
    st.link_button("GOV.UK flood risk", "https://www.gov.uk/check-long-term-flood-risk")
    st.link_button("Dartford Borough Council", "https://www.dartford.gov.uk/")
    st.caption("Scores are screening aids, not evidence of buildability.")

with auctions:
    st.caption("Manual auction records only. No live feed is connected.")
    st.markdown("[Clive Emson](https://www.cliveemson.co.uk/) · [Auction House](https://www.auctionhouse.co.uk/) · [Allsop](https://www.allsop.co.uk/) · [Savills Auctions](https://auctions.savills.co.uk/)")
    st.warning("Auction guide prices are not sale prices; check fees and legal packs.")
    if sites.empty:
        st.info("Add a plot first, then link auction listings.")
    else:
        labels = {int(r.id): f"{r['name']} — {r['location']}" for _,r in sites.iterrows()}
        with st.form("auction"):
            site_id = st.selectbox("Existing plot", list(labels), format_func=lambda k: labels[k])
            house = st.selectbox("Auction house", ["Clive Emson","Auction House","Allsop","Savills Auctions","Other"])
            lot = st.text_input("Lot reference")
            guide = st.number_input("Guide price (£)", min_value=0, step=5000)
            auction_date = st.date_input("Auction date", value=None)
            listing_url = st.text_input("Auction listing URL")
            legal_url = st.text_input("Legal pack URL")
            auction_notes = st.text_area("Auction notes")
            save = st.form_submit_button("Attach auction source")
        if save:
            if not listing_url.startswith(("https://","http://")):
                st.error("Enter a valid auction URL.")
            else:
                record = dict(site_id=site_id,auction_house=house,lot_reference=lot,guide_price=guide,auction_date=auction_date.isoformat() if auction_date else None,listing_url=listing_url.strip(),legal_pack_url=legal_url or None,notes=auction_notes)
                try:
                    api("auction_sources", "POST", payload=record)
                    st.success("Auction source saved.")
                except requests.HTTPError:
                    st.error("Could not save auction listing; it may already exist.")
        try:
            lots = pd.DataFrame(get_rows("auction_sources"))
            if not lots.empty:
                st.dataframe(lots, use_container_width=True, hide_index=True, column_config={"listing_url": st.column_config.LinkColumn("Auction listing"),"legal_pack_url": st.column_config.LinkColumn("Legal pack")})
                st.download_button("Export auction CSV", lots.to_csv(index=False), "dartford_auction_sources.csv", "text/csv")
        except requests.RequestException:
            st.error("Could not load auction records.")

with discovery:
    st.subheader("Find land around Dartford")
    st.caption("Research leads and source searches; not a live listing feed. Check prices, availability, exact location and planning before making decisions.")
    sources = [
        ("Clive Emson — Dartford auction catalogue", "https://www.cliveemson.co.uk/properties/kent/dartford/"),
        ("PrimeLocation — Dartford land", "https://www.primelocation.com/for-sale/farms-land/dartford/"),
        ("Robinson & Hall — Valley Road building plot", "https://www.robinsonandhallauctions.co.uk/property/building-plot-to-the-rear-of-8-valley-road-dartford-kent-da1-3pj/"),
        ("Barney Estates — Rowhill Road land", "https://www.barneyestates.co.uk/property/land-off-rowhill-road-dartford-kent-da2-7qq/"),
        ("EIG — Kent land auctions", "https://www.eigpropertyauctions.co.uk/search/site-land/kent"),
        ("OnTheMarket — Kent auction land", "https://www.onthemarket.com/auction/farms-land/kent/"),
    ]
    for label, link in sources:
        st.markdown(f"- [{label}]({link})")
    st.info("Promising search leads include Stock Lane, Wilmington (advertised around £80,000, approximately two-thirds acre) and Valley Road, Dartford (auction guide £65,000+, consent only for a one-bedroom bungalow). These may be unavailable or unsuitable. Verify everything at source.")
    st.warning("No scheduled imports are active. Automatic updates require a permitted API, feed or data-sharing arrangement; we do not scrape Rightmove or Zoopla.")
