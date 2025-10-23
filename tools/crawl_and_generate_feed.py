#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from email.utils import format_datetime

BASE_URL = "https://www.jogadnes.cz/clanky/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FeedCrawler/1.0)"}
DAYS_BACK = 99

def fetch_article_links():
    r = requests.get(BASE_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    articles = soup.select("div.article-box a[href^='/']")
    links = ["https://www.jogadnes.cz" + a["href"] for a in articles if a.has_attr("href")]
    return list(dict.fromkeys(links))

def fetch_article_meta(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        title = soup.find("meta", property="og:title") or soup.find("title")
        desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name":"description"})
        time_tag = soup.find("time")
        pubdate = None
        if time_tag and time_tag.has_attr("datetime"):
            pubdate = time_tag["datetime"]
        elif time_tag:
            pubdate = time_tag.get_text(strip=True)
        title_text = title["content"].strip() if title and title.has_attr("content") else title.get_text(strip=True)
        desc_text = desc["content"].strip() if desc and desc.has_attr("content") else desc.get_text(strip=True)
        return {
            "title": title_text,
            "description": desc_text,
            "pubdate": normalize_pubdate(pubdate),
            "link": url
        }
    except Exception:
        return None

def normalize_pubdate(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        try:
            dt = datetime.strptime(value, "%d. %m. %Y")
        except Exception:
            return None
    return dt

def escape_xml(s):
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&apos;"))

def main():
    links = fetch_article_links()
    cutoff = datetime.utcnow() - timedelta(days=DAYS_BACK)
    items = []
    for url in links:
        meta = fetch_article_meta(url)
        if not meta or not meta["pubdate"]:
            continue
        if meta["pubdate"] < cutoff:
            continue
        items.append({
            "title": meta["title"],
            "link": meta["link"],
            "description": meta["description"],
            "pubDate": format_datetime(meta["pubdate"])
        })

    now = format_datetime(datetime.utcnow())
    parts = []
    parts.append('<?xml version="1.0" encoding="utf-8"?>')
    parts.append('<rss version="2.0">')
    parts.append('  <channel>')
    parts.append('    <title>Jóga Dnes — automatický feed</title>')
    parts.append('    <link>https://www.jogadnes.cz/clanky/</link>')
    parts.append('    <description>Automaticky generovaný RSS feed z posledních 99 dní</description>')
    parts.append('    <language>cs</language>')
    parts.append(f'    <lastBuildDate>{now}</lastBuildDate>')

    for it in items:
        parts.append('    <item>')
        parts.append(f'      <title>{escape_xml(it["title"])}</title>')
        parts.append(f'      <link>{escape_xml(it["link"])}</link>')
        parts.append(f'      <description>{escape_xml(it["description"])}</description>')
        parts.append(f'      <pubDate>{it["pubDate"]}</pubDate>')
        parts.append(f'      <guid isPermaLink="true">{escape_xml(it["link"])}</guid>')
        parts.append('    </item>')

    parts.append('  </channel>')
    parts.append('</rss>')

    with open("jogadnes.xml", "w", encoding="utf-8") as out:
        out.write("\n".join(parts))
    print(f"Wrote jogadnes.xml with {len(items)} items")

if __name__ == "__main__":
    main()

