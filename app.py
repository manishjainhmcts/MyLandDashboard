import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime
import math
import os
import hmac

st.set_page_config(page_title="Dartford Land Finder", page_icon="🏡", layout="wide")
st.title("Dartford Land Finder")
st.caption("Private research dashboard · 15-mile radius · £200,000 land ceiling · four-bedroom home + separate private badminton hall")

# Authentication must be configured before public deployment.
password = st.secrets.get("APP_PASSWORD", os.environ.get("APP_PASSWORD", ""))
if not password:
    st.error("Private access is not configured. Set APP_PASSWORD in Streamlit secrets before using this app.")
    st.stop()
entered = st.text_input("Dashboard password", type="password")
if not hmac.compare_digest(entered, password):
    st.info("Enter your private password to continue.")
    st.stop()

st.warning("Prototype: records are stored in local SQLite and may be lost when free cloud hosting restarts. Export your CSV regularly; use a persistent cloud database before relying on this for long-term storage.")
DB = Path("land_sites.db")
conn = sqlite3.connect(DB)
conn.execute("""CREATE TABLE IF NOT EXISTS sites (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT, location TEXT, price REAL, area_acres REAL, latitude REAL, longitude REAL,
planning TEXT, green_belt TEXT, flood_risk TEXT, access TEXT, utilities TEXT,
listing_url TEXT, notes TEXT, added_at TEXT)""")
conn.commit()
DARTFORD_LAT, DARTFORD_LON = 51.4462, 0.2169

def miles(lat, lon):
    p1, p2 = math.radians(DARTFORD_LAT), math.radians(lat)
    dp, dl = math.radians(lat-DARTFORD_LAT), math.radians(lon-DARTFORD_LON)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 3958.8*2*math.atan2(math.sqrt(a), math.sqrt(1-a))

def load():
    df = pd.read_sql_query("SELECT * FROM sites ORDER BY added_at DESC", conn)
    if not df.empty:
        df["distance_miles"] = df.apply(lambda r: round(miles(r.latitude,r.longitude),1) if pd.notna(r.latitude) and pd.notna(r.longitude) else None, axis=1)
        df["within_budget"] = df.price <= 200000
        df["within_radius"] = df.distance_miles <= 15
        df["score"] = df.apply(lambda r: (40 if r.within_budget else 0) + (25 if r.within_radius else 0) + (20 if r.planning == "Residential permission" else 10 if r.planning == "Potential (unverified)" else 0) + (15 if pd.notna(r.area_acres) and r.area_acres >= .25 else 0), axis=1)
    return df

with st.sidebar:
    st.header("Search criteria")
    max_price = st.number_input("Maximum land price (£)", min_value=0, value=200000, step=10000)
    max_distance = st.slider("Radius from Dartford (miles)", 1, 30, 15)
    min_acres = st.number_input("Minimum plot size (acres)", min_value=0.0, value=0.25, step=0.05)
    st.markdown("**Build brief:** four-bedroom detached house and a separate, family-only badminton hall.")
    st.caption("Planning, access, site services and a high-clearance hall need independent verification.")

tab1, tab2, tab3, tab4 = st.tabs(["Explore plots", "Add a plot", "Planning & guidance", "Auction sources"])
with tab1:
    df = load()
    if df.empty:
        st.info("No listings entered yet. Use 'Add a plot' to start your shortlist. No live Rightmove or Zoopla feed is connected.")
    else:
        filtered = df[(df.price <= max_price) & (df.distance_miles <= max_distance) & (df.area_acres >= min_acres)].copy()
        c1,c2,c3 = st.columns(3)
        c1.metric("Matching plots",len(filtered))
        c2.metric("Lowest asking price", f"£{filtered.price.min():,.0f}" if len(filtered) else "—")
        c3.metric("Plots with residential permission", int((filtered.planning=="Residential permission").sum()))
        if len(filtered):
            st.map(filtered.rename(columns={"latitude":"lat","longitude":"lon"})[["lat","lon"]].dropna())
            columns=["name","location","price","area_acres","distance_miles","planning","green_belt","flood_risk","score","listing_url","notes"]
            st.dataframe(filtered[columns].sort_values("score",ascending=False), use_container_width=True, hide_index=True,
                         column_config={"listing_url":st.column_config.LinkColumn("Listing")})
        st.download_button("Export all saved plots (CSV)", df.to_csv(index=False).encode("utf-8"), "dartford_plots.csv", "text/csv")
        with st.expander("Delete a saved plot"):
            choices={f"{int(r.id)} · {r['name']}":int(r.id) for _,r in df.iterrows()}
            choice=st.selectbox("Select plot",list(choices))
            if st.button("Delete selected plot"):
                conn.execute("DELETE FROM sites WHERE id=?", (choices[choice],))
                conn.commit()
                st.rerun()
with tab2:
    st.subheader("Save a property listing")
    st.caption("Copy details from a listing you are authorised to view. Coordinates are required for the radius map.")
    with st.form("new_site"):
        name=st.text_input("Plot name / reference")
        location=st.text_input("Area / address")
        price=st.number_input("Asking price (£)",min_value=0,step=5000)
        area=st.number_input("Area (acres)",min_value=0.0,step=0.05,format="%.2f")
        lat=st.number_input("Latitude",value=51.4462,format="%.6f")
        lon=st.number_input("Longitude",value=0.2169,format="%.6f")
        planning=st.selectbox("Planning",["Unknown","Potential (unverified)","Residential permission","No residential permission"])
        green=st.selectbox("Green Belt",["Unknown","Yes","No"])
        flood=st.selectbox("Flood risk",["Unknown","Potential risk","No known risk (unverified)"])
        access=st.text_input("Road access")
        utilities=st.text_input("Utilities")
        url=st.text_input("Original listing URL")
        notes=st.text_area("Notes / concerns")
        save=st.form_submit_button("Save plot")
        if save:
            if not name.strip():
                st.error("Please enter a plot name.")
            elif url and not url.startswith(("https://","http://")):
                st.error("Listing URL must start with https:// or http://")
            else:
                conn.execute("""INSERT INTO sites (name,location,price,area_acres,latitude,longitude,planning,green_belt,flood_risk,access,utilities,listing_url,notes,added_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(name,location,price,area,lat,lon,planning,green,flood,access,utilities,url,notes,datetime.now().isoformat()))
                conn.commit()
                st.success("Plot saved. See Explore plots.")
with tab3:
    st.subheader("Checks before making an offer")
    st.markdown("""
    - **Planning:** Check the relevant local planning authority for residential consent and whether a tall, separate sports hall is acceptable.
    - **Green Belt and flood risk:** Confirm designations against official maps, not listing descriptions.
    - **Design:** Check badminton court run-offs and unobstructed clear height with a qualified designer.
    - **Budget:** £200,000 maximum land cost; up to £500,000 proposed build finance is not guaranteed.
    - **Due diligence:** Road access, services, covenants, trees, ground conditions and legal title.
    """)
    st.link_button("Planning Portal", "https://www.planningportal.co.uk/")
    st.link_button("Flood risk (GOV.UK)", "https://www.gov.uk/check-long-term-flood-risk")
    st.link_button("Dartford Borough Council", "https://www.dartford.gov.uk/")
    st.caption("Scores are rough screening aids, not evidence of planning permission or buildability.")

# Auction lots are separate source records linked to a saved plot, not duplicate plots.
conn.execute("""CREATE TABLE IF NOT EXISTS auction_sources (
id INTEGER PRIMARY KEY AUTOINCREMENT,
site_id INTEGER NOT NULL,
auction_house TEXT NOT NULL,
lot_reference TEXT,
guide_price REAL,
auction_date TEXT,
listing_url TEXT NOT NULL UNIQUE,
legal_pack_url TEXT,
notes TEXT,
created_at TEXT NOT NULL
)""")
conn.commit()
with tab4:
    st.subheader("Auction properties")
    st.caption("Clive Emson, Auction House, Allsop and Savills Auctions. Manual entries only; no live feed is connected.")
    st.markdown("[Clive Emson](https://www.cliveemson.co.uk/) · [Auction House](https://www.auctionhouse.co.uk/) · [Allsop](https://www.allsop.co.uk/) · [Savills Auctions](https://auctions.savills.co.uk/)")
    st.info("Auction guide prices are not sale prices. Check fees, legal packs, special conditions and planning before bidding.")
    sites=load()
    if sites.empty:
        st.warning("Add the plot under 'Add a plot' first, then attach its auction listing here.")
    else:
        labels={int(r.id):f"{r['name']} — {r['location']}" for _,r in sites.iterrows()}
        with st.form("auction_lot"):
            site_id=st.selectbox("Existing plot (one plot can have several auction listings)",list(labels),format_func=lambda k:labels[k])
            house=st.selectbox("Auction house",["Clive Emson","Auction House","Allsop","Savills Auctions","Other"])
            ref=st.text_input("Lot reference")
            guide=st.number_input("Guide price (£)",min_value=0,step=5000)
            date=st.text_input("Auction date (YYYY-MM-DD, optional)")
            url=st.text_input("Auction listing URL")
            legal=st.text_input("Legal pack URL (optional)")
            notes=st.text_area("Auction notes")
            submit=st.form_submit_button("Attach auction source")
        if submit:
            import re
            if not url.startswith(("https://","http://")):
                st.error("Enter a valid auction listing URL.")
            elif date and not re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}",date):
                st.error("Use YYYY-MM-DD for the auction date.")
            elif conn.execute("SELECT 1 FROM auction_sources WHERE listing_url=?",(url.strip(),)).fetchone():
                st.warning("This auction listing is already saved; it was not duplicated.")
            else:
                conn.execute("""INSERT INTO auction_sources
                    (site_id,auction_house,lot_reference,guide_price,auction_date,listing_url,legal_pack_url,notes,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (site_id,house,ref,guide,date,url.strip(),legal,notes,datetime.now().isoformat()))
                conn.commit()
                st.success("Auction source linked to the existing plot.")
        lots=pd.read_sql_query("""SELECT a.auction_house,a.lot_reference,a.guide_price,a.auction_date,
            a.listing_url,a.legal_pack_url,a.notes,s.name AS plot_name,s.location
            FROM auction_sources a JOIN sites s ON a.site_id=s.id ORDER BY a.created_at DESC""",conn)
        if not lots.empty:
            st.dataframe(lots,hide_index=True,use_container_width=True,
                column_config={"listing_url":st.column_config.LinkColumn("Auction listing"),
                               "legal_pack_url":st.column_config.LinkColumn("Legal pack")})
            st.download_button("Export auction sources CSV",lots.to_csv(index=False).encode(),"dartford_auction_sources.csv","text/csv")
