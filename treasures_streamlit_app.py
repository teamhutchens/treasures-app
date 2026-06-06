#!/usr/bin/env python3
"""
Treasures - Daily Free Stuff Finder (Streamlit app)

Run locally:
    streamlit run treasures_streamlit_app.py
"""

from __future__ import annotations

import io
import re
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

APP_TITLE = "Treasures — Daily Free Stuff Finder"
APP_SUBTITLE = "Search curated sweepstakes, freebies, and test-and-keep offers from trusted source sites."

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}
TIMEOUT = 25
PAUSE_SECONDS = 0.75
MAX_ITEMS_PER_SOURCE = 60


@dataclass
class Source:
    name: str
    url: str
    category: str
    note: str


SOURCES = [
    Source(
        "Contest Reminder",
        "https://contestreminder.com/",
        "Sweepstakes",
        "Daily-updated sweepstakes directory and entry tracker."
    ),
    Source(
        "Contest Bee",
        "https://www.contestbee.com/",
        "Sweepstakes",
        "Curated daily sweepstakes and giveaway listings."
    ),
    Source(
        "Freebie Shark Sweepstakes",
        "https://www.freebieshark.com/category/sweepstakes",
        "Sweepstakes",
        "Sweepstakes-focused page with updated contest listings."
    ),
    Source(
        "The Freebie Guy Sweepstakes",
        "https://thefreebieguy.com/current-sweepstakes-and-giveaways/",
        "Sweepstakes",
        "Daily updated giveaways and sweepstakes listings."
    ),
    Source(
        "Daily Free Stuff USA",
        "https://dailyfreestuffusa.com/",
        "Freebies",
        "Free samples, giveaways, and product testing programs."
    ),
    Source(
        "TrySpree",
        "https://www.tryspree.com/",
        "Free Samples",
        "Community-driven free sample and freebie listings."
    ),
]

POSITIVE_KEYWORDS = [
    "sweepstakes", "giveaway", "win", "gift card", "free", "sample", "test & keep",
    "test and keep", "freebie", "prize", "voucher", "trip", "camera", "box",
    "macbook", "iphone", "galaxy", "gift", "cash"
]
NEGATIVE_KEYWORDS = [
    "privacy", "contact", "about", "terms", "faq", "policy", "login", "sign in",
    "newsletter", "facebook", "instagram", "pinterest", "reddit", "guide", "read more",
    "older posts", "menu", "submit", "community", "copyright", "subscribe", "forum rules"
]


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    return text.replace("\xa0", " ")



def looks_like_listing(text: str) -> bool:
    t = clean_text(text).lower()
    if len(t) < 8:
        return False
    if any(bad in t for bad in NEGATIVE_KEYWORDS):
        return False
    return any(ok in t for ok in POSITIVE_KEYWORDS)



def plausible_link(href: str, base_url: str) -> str | None:
    if not href:
        return None
    href = href.strip()
    if href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
        return None
    absolute = urljoin(base_url, href)
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"}:
        return None
    return absolute



def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return response.text



def scrape_source(source: Source) -> list[dict]:
    html = fetch_html(source.url)
    soup = BeautifulSoup(html, "html.parser")

    records = []
    seen = set()

    # Strategy 1: anchors
    for a in soup.find_all("a", href=True):
        title = clean_text(a.get_text(" "))
        link = plausible_link(a.get("href"), source.url)
        if not title or not link or not looks_like_listing(title):
            continue
        key = (title.lower(), link.lower())
        if key in seen:
            continue
        seen.add(key)
        records.append({
            "Source": source.name,
            "Source Category": source.category,
            "Item": title,
            "Link": link,
            "Notes": source.note,
        })
        if len(records) >= MAX_ITEMS_PER_SOURCE:
            break

    # Strategy 2: headings if needed
    if len(records) < 8:
        for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
            title = clean_text(tag.get_text(" "))
            if not title or not looks_like_listing(title):
                continue
            parent_link = tag.find_parent("a")
            link = plausible_link(parent_link.get("href"), source.url) if parent_link else source.url
            key = (title.lower(), (link or source.url).lower())
            if key in seen:
                continue
            seen.add(key)
            records.append({
                "Source": source.name,
                "Source Category": source.category,
                "Item": title,
                "Link": link or source.url,
                "Notes": source.note,
            })
            if len(records) >= MAX_ITEMS_PER_SOURCE:
                break

    return records



def scrape_selected_sources(selected_names: list[str]) -> tuple[pd.DataFrame, list[str]]:
    rows = []
    errors = []
    selected_sources = [s for s in SOURCES if s.name in selected_names]

    for source in selected_sources:
        try:
            results = scrape_source(source)
            rows.extend(results)
        except Exception as exc:
            errors.append(f"{source.name}: {exc}")
        time.sleep(PAUSE_SECONDS)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["Source", "Item", "Link"]).sort_values(["Source", "Item"])
    return df, errors



def to_excel_bytes(df: pd.DataFrame, selected_names: list[str]) -> bytes:
    output = io.BytesIO()
    source_df = pd.DataFrame([
        {
            "Source": s.name,
            "Type": s.category,
            "Site URL": s.url,
            "Notes": s.note,
            "Included in this run": "Yes" if s.name in selected_names else "No",
        }
        for s in SOURCES
    ])
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        source_df.to_excel(writer, index=False, sheet_name="Sources")
        if df.empty:
            pd.DataFrame(columns=["Source", "Source Category", "Item", "Link", "Notes"]).to_excel(
                writer, index=False, sheet_name="Finds"
            )
        else:
            df.to_excel(writer, index=False, sheet_name="Finds")
    output.seek(0)
    return output.getvalue()



def style_dataframe_for_display(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    display_df = df.copy()
    display_df["Open"] = display_df["Link"].apply(lambda x: f"[Open item]({x})")
    return display_df[["Source", "Source Category", "Item", "Open", "Notes"]]


st.set_page_config(page_title="Treasures", page_icon="💎", layout="wide")

st.title(APP_TITLE)
st.caption(APP_SUBTITLE)

with st.sidebar:
    st.header("Controls")
    selected_names = st.multiselect(
        "Choose one or more source sites",
        options=[s.name for s in SOURCES],
        default=[s.name for s in SOURCES],
    )
    contains_text = st.text_input("Filter item names contains", placeholder="e.g., gift card, macbook, trip")
    category_filter = st.multiselect(
        "Filter by category",
        options=sorted({s.category for s in SOURCES}),
        default=[]
    )
    run = st.button("Run Treasures Finder", type="primary", use_container_width=True)

st.markdown("### Source Sites")
source_overview = pd.DataFrame([
    {"Source": s.name, "Type": s.category, "Site URL": s.url, "What it covers": s.note}
    for s in SOURCES
])
st.dataframe(source_overview, use_container_width=True, hide_index=True)

if run:
    if not selected_names:
        st.warning("Choose at least one source site to run the finder.")
    else:
        with st.spinner("Searching selected sites for free stuff and sweepstakes..."):
            df, errors = scrape_selected_sources(selected_names)

        if category_filter:
            df = df[df["Source Category"].isin(category_filter)] if not df.empty else df
        if contains_text and not df.empty:
            df = df[df["Item"].str.contains(contains_text, case=False, na=False)]

        st.markdown("### Results")
        st.metric("Items found", 0 if df.empty else len(df))

        if errors:
            st.error("Some sources could not be read in this run:")
            for err in errors:
                st.write(f"- {err}")

        if df.empty:
            st.info("No items matched your selection or filters.")
        else:
            st.dataframe(
                style_dataframe_for_display(df),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Open": st.column_config.LinkColumn("Open", display_text="Open item"),
                },
            )

        excel_bytes = to_excel_bytes(df, selected_names)
        st.download_button(
            label="Download treasures.xlsx",
            data=excel_bytes,
            file_name="treasures.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

st.markdown("---")
st.markdown(
    "**Tips:** Select all sources for a broad scan, then filter by terms like **gift card**, **trip**, **MacBook**, or **sample**."
)
