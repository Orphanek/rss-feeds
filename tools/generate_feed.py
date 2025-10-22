#!/usr/bin/env python3
import argparse
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from email.utils import format_datetime
import sys

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FeedGenerator/1.0)"}

def fetch_meta(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        title_tag = soup.find("meta", property="og:title") or soup.find("title")
        desc_tag = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name":"description"})
        time_tag = soup.find("time")
        pubdate = None
        if time_tag and time_tag.has_attr("datetime"):
            pubdate = time_tag["datetime"]
        title = (title_tag["content"].strip() if getattr(title_tag, "has_attr", lambda x: False)("content")
                 else (title_tag.get_text(strip=True) if title_tag else ""))
        desc = (desc_tag["content"].strip() if getattr(desc_tag, "has_attr", lambda x: False)("content")
                else (desc_tag.get_text(strip=True) if desc_tag else ""))
        return {"title": title or url, "description": desc or "", "pubdate": pubdate}
    except Exception:
        return {"title": url, "description": "", "pubdate": None}

def normalize_pubdate(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return format_datetime(dt)
    except Exception:
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(value)
            return format_datetime(dt)
        except Exception:
            return None

def escape_xml(s):
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&apos;"))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--urls-file", required=True)
    p.add_argument("--output-file", default="jogadnes.xml")
    p.add_argument("--title", default="Jóga Dnes — vlastní feed")
    p.add_argument("--link", default="https://www.jogadnes.cz/")
    p.add_argument("--description", default="Automaticky vygenerovaný statický RSS feed")
    args = p.parse_args()

    try:
        with open(args.urls_file, "r", encoding="utf-8") as fh:
            urls = [line.strip() for line in fh if line.strip() and not line.strip().startswith("#")]
    except FileNotFoundError:
        print(f"URLs file not found: {args.urls_file}", file=sys.stderr)
        sys.exit(1)

    items = []
    for url in urls[:50]:
        meta = fetch_meta(url)
        pub = normalize_pubdate(meta.get("pubdate"))
        items.append({
            "title": meta.get("title") or url,
            "link": url,
            "description": meta.get("description") or "",
            "pubDate": pub or format_datetime(datetime.utcnow())
        })

    now = format_datetime(datetime.utcnow())
    parts = []
    parts.append('<?xml version="1.0" encoding="utf-8"?>')
    parts.append('<rss version="2.0">')
    parts.append('  <channel>')
    parts.append(f'    <title>{args.title}</title>')
    parts.append(f'    <link>{args.link}</link>')
    parts.append(f'    <description>{args.description}</description>')
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

    with open(args.output_file, "w", encoding="utf-8") as out:
        out.write("\n".join(parts))
    print(f"Wrote {args.output_file} with {len(items)} items")

if __name__ == "__main__":
    main()
