import re
import time
from urllib.parse import urljoin, urlparse

import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="Treasures", page_icon="💎", layout="wide")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}
TIMEOUT = 20
PAUSE_SECONDS = 0.75
MAX_ITEMS_PER_SOURCE = 40

SOURCES = [
    {
        "name": "Contest Reminder",
        "type": "Sweepstakes",
        "url": "https://contestreminder.com/",
        "note": "Daily-updated sweepstakes directory and entry tracker."
    },
    {
        "name": "Contest Bee",
        "type": "Sweepstakes",
        "url": "https://www.contestbee.com/",
        "note": "Curated daily sweepstakes and giveaway listings."
    },
    {
        "name": "Freebie Shark Sweepstakes",
        "type": "Sweepstakes",
        "url": "https://www.freebieshark.com/category/sweepstakes",
        "note": "Sweepstakes-focused page with updated contest listings."
    },
    {
        "name": "The Freebie Guy",
        "type": "Sweepstakes",
        "url": "https://thefreebieguy.com/current-sweepstakes-and-giveaways/",
        "note": "Daily updated giveaways and sweepstakes listings."
    },
    {
        "name": "Daily Free Stuff USA",
        "type": "Freebies",
        "url": "https://dailyfreestuffusa.com/",
        "note": "Free samples, giveaways, and product testing programs."
    },
    {
        "name": "TrySpree",
        "type": "Free Samples",
        "url": "https://www.tryspree.com/",
        "note": "Community-driven free sample and freebie listings."
    },
]

POSITIVE_KEYWORDS = [
    "sweepstakes", "giveaway", "win", "gift card", "free", "sample", "test & keep",
    "test and keep", "freebie", "prize", "voucher", "trip", "camera", "box",
    "macbook", "iphone", "galaxy", "cash", "vacation", "holiday"
]
NEGATIVE_KEYWORDS = [
    "privacy", "contact", "about", "terms", "faq", "policy", "login", "sign in",
    "newsletter", "facebook", "instagram", "pinterest", "reddit", "guide", "read more",
    "older posts", "menu", "submit", "community", "copyright", "subscribe", "forum rules"
]

FALLBACK_ITEMS = [
    {
        "Source": "Daily Free Stuff USA",
        "Source Type": "Freebies",
        "Item": "Win a $500 CVS Gift Card",
        "Link": "https://dailyfreestuffusa.com/",
        "Notes": "Fallback item shown if a live scrape does not return results."
    },
    {
        "Source": "Daily Free Stuff USA",
        "Source Type": "Freebies",
        "Item": "Win an iPhone 15 Pro",
        "Link": "https://dailyfreestuffusa.com/",
        "Notes": "Fallback item shown if a live scrape does not return results."
    },
    {
        "Source": "Contest Bee",
        "Source Type": "Sweepstakes",
        "Item": "FUJIFILM instax Capture the Joy Tour Sweepstakes",
        "Link": "https://www.contestbee.com/",
        "Notes": "Fallback item shown if a live scrape does not return results."
    },
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


@st.cache_data(show_spinner=False, ttl=1800)
def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return response.text



def scrape_source(source: dict) -> tuple[list[dict], str | None]:
    try:
        html = fetch_html(source["url"])
        soup = BeautifulSoup(html, "html.parser")

        records = []
        seen = set()

        for a in soup.find_all("a", href=True):
            title = clean_text(a.get_text(" "))
            link = plausible_link(a.get("href"), source["url"])
            if not title or not link or not looks_like_listing(title):
                continue
            key = (title.lower(), link.lower())
            if key in seen:
                continue
            seen.add(key)
            records.append(
                {
                    "Source": source["name"],
                    "Source Type": source["type"],
                    "Item": title,
                    "Link": link,
                    "Notes": source["note"],
                }
            )
            if len(records) >= MAX_ITEMS_PER_SOURCE:
                break

        if len(records) < 5:
            for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
                title = clean_text(tag.get_text(" "))
                if not title or not looks_like_listing(title):
                    continue
                parent_link = tag.find_parent("a")
                link = plausible_link(parent_link.get("href"), source["url"]) if parent_link else source["url"]
                key = (title.lower(), (link or source["url"]).lower())
                if key in seen:
                    continue
                seen.add(key)
                records.append(
                    {
                        "Source": source["name"],
                        "Source Type": source["type"],
                        "Item": title,
                        "Link": link or source["url"],
                        "Notes": source["note"],
                    }
                )
                if len(records) >= MAX_ITEMS_PER_SOURCE:
                    break

        return records, None
    except Exception as exc:
        return [], f"{source['name']}: {exc}"



def run_scrape(selected_sources: list[dict]) -> tuple[list[dict], list[str]]:
    rows = []
    errors = []
    for source in selected_sources:
        source_rows, err = scrape_source(source)
        rows.extend(source_rows)
        if err:
            errors.append(err)
        time.sleep(PAUSE_SECONDS)

    # Dedupe
    deduped = []
    seen = set()
    for row in rows:
        key = (row["Source"].lower(), row["Item"].lower(), row["Link"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped, errors


st.title("💎 Treasures — Daily Free Stuff Finder")
st.caption("Live scraping version. Select source sites, scrape fresh listings, and filter the results.")

with st.sidebar:
    st.header("Controls")
    selected_names = st.multiselect(
        "Choose source sites",
        options=[s["name"] for s in SOURCES],
        default=[s["name"] for s in SOURCES],
    )
    source_type_filter = st.multiselect(
        "Filter by source type",
        options=sorted({s["type"] for s in SOURCES}),
        default=[],
    )
    search = st.text_input("Filter item text", placeholder="gift card, iphone, travel, sample")
    scrape_now = st.button("Run live scrape", type="primary", use_container_width=True)

st.markdown("## 🌐 Source Sites")
for source in SOURCES:
    st.markdown(f"**{source['name']}** — {source['type']}")
    st.markdown(source["url"])
    st.caption(source["note"])

st.divider()

if scrape_now:
    selected_sources = [s for s in SOURCES if s["name"] in selected_names]
    if not selected_sources:
        st.warning("Choose at least one source site, then run the scrape.")
        st.stop()

    with st.spinner("Scraping live listings from selected sites..."):
        rows, errors = run_scrape(selected_sources)

    if not rows:
        rows = FALLBACK_ITEMS.copy()
        st.info("The live scrape did not return items just now, so fallback sample results are being shown.")

    if source_type_filter:
        rows = [r for r in rows if r["Source Type"] in source_type_filter]
    if search:
        rows = [r for r in rows if search.lower() in r["Item"].lower()]

    st.markdown("## 🔍 Scraped Results")
    st.write(f"Items shown: {len(rows)}")

    if errors:
        st.warning("Some sources returned errors during this run:")
        for err in errors:
            st.write(f"- {err}")

    if rows:
        for row in rows:
            st.markdown(f"**{row['Item']}**")
            st.write(f"Source: {row['Source']} | Type: {row['Source Type']}")
            st.markdown(row["Link"])
            st.caption(row["Notes"])
            st.write("")
    else:
        st.info("No results matched your filters.")
else:
    st.info("Select source sites and click **Run live scrape** to pull fresh listings.")

st.divider()
st.caption("Tip: If a site changes its layout, the scraper may need small adjustments. This version keeps dependencies minimal for easier deployment.")
