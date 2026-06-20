#!/usr/bin/env python3
"""
Zee5 EPG Generator
Direct from gwapi.zee5.com/v1/epg

Usage:
    python3 zee5_epg.py
    python3 zee5_epg.py --days 7
    python3 zee5_epg.py --lang tamil
    python3 zee5_epg.py --output epg.xml --gz
    python3 zee5_epg.py --list-channels
"""

import argparse
import gzip
import json
import os
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from xml.dom import minidom
import xml.etree.ElementTree as ET

# ── Zee5 EPG API ──────────────────────────────────────────────
# Format: https://gwapi.zee5.com/v1/epg?channels=0-9-zeetv&start=0&end=0&page_size=100
# start/end = day offset from today (0=today, 1=tomorrow, -1=yesterday)
EPG_API = "https://gwapi.zee5.com/v1/epg"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.zee5.com",
    "Referer": "https://www.zee5.com/livetv",
}

# ── Zee5 Channels (site_id format: 0-9-<id>) ─────────────────
CHANNELS = [
    # Tamil
    {"id": "0-9-9z5383487", "tvg_id": "zee5-zeetamil",       "name": "Zee Tamil",           "lang": "ta", "group": "Zee5 Tamil",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-9z5383487/list/150x150/zeetamil150x150.png"},
    {"id": "0-9-9z5383488", "tvg_id": "zee5-zeecinemalu",     "name": "Zee Cinemalu",        "lang": "te", "group": "Zee5 Telugu",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-9z5383488/list/150x150/zeecinemalu150x150.png"},
    {"id": "0-9-9z5383485", "tvg_id": "zee5-zeetelugu",       "name": "Zee Telugu",          "lang": "te", "group": "Zee5 Telugu",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-9z5383485/list/150x150/zeetelugu150x150.png"},
    {"id": "0-9-9z5383486", "tvg_id": "zee5-zeemarathi",      "name": "Zee Marathi",         "lang": "mr", "group": "Zee5 Marathi",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-9z5383486/list/150x150/zeemarathi150x150.png"},
    {"id": "0-9-9z5383466", "tvg_id": "zee5-zeekannada",      "name": "Zee Kannada",         "lang": "kn", "group": "Zee5 Kannada",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-9z5383466/list/150x150/zeekannada150x150.png"},

    # Hindi
    {"id": "0-9-zeetv",     "tvg_id": "zee5-zeetv",           "name": "Zee TV",              "lang": "hi", "group": "Zee5 Hindi",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-zeetv/list/150x150/zeetv150x150.png"},
    {"id": "0-9-zeecin",    "tvg_id": "zee5-zeecinema",       "name": "Zee Cinema",          "lang": "hi", "group": "Zee5 Hindi",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-zeecin/list/150x150/zeecinema150x150.png"},
    {"id": "0-9-zeebiz",    "tvg_id": "zee5-zeebusiness",     "name": "Zee Business",        "lang": "hi", "group": "Zee5 Hindi",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-zeebiz/list/150x150/zeebusiness150x150.png"},
    {"id": "0-9-zeenews",   "tvg_id": "zee5-zeenews",         "name": "Zee News",            "lang": "hi", "group": "Zee5 Hindi",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-zeenews/list/150x150/zeenews150x150.png"},
    {"id": "0-9-251",       "tvg_id": "zee5-zeebiharjharkhand","name": "Zee Bihar Jharkhand", "lang": "hi", "group": "Zee5 Hindi",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-251/list/150x150/zeebiharjharkhand150x150.png"},
    {"id": "0-9-255",       "tvg_id": "zee5-zeempcg",         "name": "Zee MP CG",           "lang": "hi", "group": "Zee5 Hindi",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-255/list/150x150/zeempcg150x150.png"},
    {"id": "0-9-259",       "tvg_id": "zee5-zeerajasthan",    "name": "Zee Rajasthan",       "lang": "hi", "group": "Zee5 Hindi",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-259/list/150x150/zeerajasthan150x150.png"},
    {"id": "0-9-261",       "tvg_id": "zee5-zeedelhi",        "name": "Zee Delhi NCR Haryana","lang": "hi", "group": "Zee5 Hindi",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-261/list/150x150/zeedelhi150x150.png"},
    {"id": "0-9-zeeyuva",   "tvg_id": "zee5-zeeyuva",         "name": "Zee Yuva",            "lang": "mr", "group": "Zee5 Marathi",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-zeeyuva/list/150x150/zeeyuva150x150.png"},
    {"id": "0-9-zeeanu",    "tvg_id": "zee5-zeeanmol",        "name": "Zee Anmol",           "lang": "hi", "group": "Zee5 Hindi",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-zeeanu/list/150x150/zeeanmol150x150.png"},
    {"id": "0-9-9z543514",  "tvg_id": "zee5-zeepunjab",       "name": "Zee Punjab",          "lang": "pa", "group": "Zee5 Punjabi",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-9z543514/list/150x150/zeepunjab150x150.png"},
    {"id": "0-9-zeesal",    "tvg_id": "zee5-zeesarthak",      "name": "Zee Sarthak",         "lang": "or", "group": "Zee5 Odia",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-zeesal/list/150x150/zeesarthak150x150.png"},

    # English
    {"id": "0-9-wion",      "tvg_id": "zee5-wion",            "name": "WION",                "lang": "en", "group": "Zee5 English",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-wion/list/150x150/wion150x150.png"},
    {"id": "0-9-zlcfty",    "tvg_id": "zee5-zee-cafe",        "name": "Zee Cafe",            "lang": "en", "group": "Zee5 English",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-zlcfty/list/150x150/zeecafe150x150.png"},
    {"id": "0-9-&pictures", "tvg_id": "zee5-andpictures",     "name": "&pictures",           "lang": "hi", "group": "Zee5 Hindi",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-%26pictures/list/150x150/andpictures150x150.png"},
    {"id": "0-9-andtv",     "tvg_id": "zee5-andtv",           "name": "&TV",                 "lang": "hi", "group": "Zee5 Hindi",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-andtv/list/150x150/andtv150x150.png"},

    # News
    {"id": "0-9-aajtak",    "tvg_id": "zee5-aajtak",          "name": "Aaj Tak",             "lang": "hi", "group": "Zee5 News",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-aajtak/list/150x150/aajtak150x150.png"},
    {"id": "0-9-indiatoday","tvg_id": "zee5-indiatoday",      "name": "India Today",         "lang": "en", "group": "Zee5 News",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-indiatoday/list/150x150/indiatoday150x150.png"},
    {"id": "0-9-9z583533",  "tvg_id": "zee5-zeenewstamil",    "name": "Zee News Tamil",      "lang": "ta", "group": "Zee5 Tamil",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-9z583533/list/150x150/zeenewstamil150x150.png"},
    {"id": "0-9-9z5817234", "tvg_id": "zee5-zeealwan",        "name": "Zee Alwan HD",        "lang": "ar", "group": "Zee5 Arabic",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-9z5817234/list/150x150/zeealwan150x150.png"},
    {"id": "0-9-9z5817235", "tvg_id": "zee5-zeeaflam",        "name": "Zee Aflam HD",        "lang": "ar", "group": "Zee5 Arabic",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-9z5817235/list/150x150/zeeaflam150x150.png"},
    {"id": "0-9-9z5825786", "tvg_id": "zee5-zeeone",          "name": "Zee One",             "lang": "hi", "group": "Zee5 International",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-9z5825786/list/150x150/zeeone150x150.png"},

    # Bangla
    {"id": "0-9-zeebangla", "tvg_id": "zee5-zeebangla",       "name": "Zee Bangla",          "lang": "bn", "group": "Zee5 Bangla",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-zeebangla/list/150x150/zeebangla150x150.png"},
    {"id": "0-9-zbsn",      "tvg_id": "zee5-zeebanglasonar",  "name": "Zee Bangla Sonar",    "lang": "bn", "group": "Zee5 Bangla",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-zbsn/list/150x150/zeebanglasonar150x150.png"},

    # Gujarati
    {"id": "0-9-zeekalak",  "tvg_id": "zee5-zee24kalak",      "name": "Zee 24 Kalak",        "lang": "gu", "group": "Zee5 Gujarati",
     "icon": "https://akamaividz2.zee5.com/image/upload/w_100,h_100/resources/0-9-zeekalak/list/150x150/zee24kalak150x150.png"},
]

LANG_MAP = {
    "tamil": "ta", "telugu": "te", "kannada": "kn", "hindi": "hi",
    "marathi": "mr", "bangla": "bn", "bengali": "bn", "gujarati": "gu",
    "english": "en", "odia": "or", "punjabi": "pa", "arabic": "ar",
}

IST = timezone(timedelta(hours=5, minutes=30))


def to_xmltv_time(unix_ts: int) -> str:
    dt = datetime.fromtimestamp(unix_ts, tz=IST)
    return dt.strftime("%Y%m%d%H%M%S") + " +0530"


def fetch_epg_day(channel_ids: list, day_offset: int) -> dict:
    """Fetch EPG for multiple channels for one day. Returns {channel_id: [programmes]}"""
    # Zee5 API accepts multiple channels comma-separated — batch 10 at a time
    results = {}
    batch_size = 10
    for i in range(0, len(channel_ids), batch_size):
        batch = channel_ids[i:i+batch_size]
        channels_param = ",".join(b["id"] for b in batch)
        params = urllib.parse.urlencode({
            "channels": channels_param,
            "start": day_offset,
            "end": day_offset,
            "time_offset": "+05:30",
            "page_size": 100,
            "translation": "en",
            "country": "IN",
        })
        url = f"{EPG_API}?{params}"
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            # Response: {"channel_list": [{"id": ..., "assets": [...]}]}
            for ch_data in data.get("channel_list", []):
                ch_id = ch_data.get("id", "")
                results[ch_id] = ch_data.get("assets", [])
        except Exception as e:
            print(f"    [!] batch offset={day_offset}: {e}", file=sys.stderr)
        time.sleep(0.2)
    return results


def build_epg(channels: list, days: int = 1) -> ET.Element:
    root = ET.Element("tv")
    root.set("generator-info-name", "zee5-epg")
    root.set("source-info-name", "Zee5")
    root.set("source-info-url", "https://www.zee5.com/livetv")

    # Channel entries
    for ch in channels:
        ch_el = ET.SubElement(root, "channel")
        ch_el.set("id", ch["tvg_id"])
        dn = ET.SubElement(ch_el, "display-name")
        dn.set("lang", ch["lang"])
        dn.text = ch["name"]
        ET.SubElement(ch_el, "icon").set("src", ch["icon"])
        ET.SubElement(ch_el, "url").text = "https://www.zee5.com/livetv"

    # Programme entries
    total = 0
    id_to_meta = {ch["id"]: ch for ch in channels}

    for day_offset in range(days):
        date_str = (datetime.now(IST) + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        print(f"\n  Day {day_offset+1} ({date_str}):")
        day_data = fetch_epg_day(channels, day_offset)

        for ch_id, assets in day_data.items():
            meta = id_to_meta.get(ch_id)
            if not meta:
                continue
            print(f"    [{ch_id}] {meta['name']}: {len(assets)} programmes")

            for item in assets:
                start_ts = item.get("start_timestamp") or item.get("broadcast_start_time") or item.get("start")
                end_ts   = item.get("end_timestamp")   or item.get("broadcast_end_time")   or item.get("end")
                title    = item.get("title", "").strip() or item.get("asset_title", "").strip() or "Unknown"

                if not start_ts or not end_ts:
                    continue

                prog = ET.SubElement(root, "programme")
                prog.set("start",   to_xmltv_time(int(start_ts)))
                prog.set("stop",    to_xmltv_time(int(end_ts)))
                prog.set("channel", meta["tvg_id"])

                t = ET.SubElement(prog, "title")
                t.set("lang", meta["lang"])
                t.text = title

                desc = item.get("description", "").strip() or item.get("asset_desc", "").strip()
                if desc:
                    d = ET.SubElement(prog, "desc")
                    d.set("lang", meta["lang"])
                    d.text = desc

                genre = item.get("genre", [])
                if genre:
                    cat = ET.SubElement(prog, "category")
                    cat.set("lang", "en")
                    cat.text = genre[0] if isinstance(genre, list) else str(genre)

                img = item.get("image_url") or item.get("thumbnail") or item.get("image")
                if img:
                    ET.SubElement(prog, "icon").set("src", img)

                total += 1

    print(f"\n[✓] Total programmes: {total}")
    return root


def prettify(element: ET.Element) -> str:
    raw = ET.tostring(element, encoding="unicode")
    dom = minidom.parseString(raw)
    lines = dom.toprettyxml(indent="  ").split("\n")
    lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Zee5 EPG Generator")
    parser.add_argument("--days",          type=int, default=1)
    parser.add_argument("--output",        default="zee5_epg.xml")
    parser.add_argument("--gz",            action="store_true")
    parser.add_argument("--lang",          default="", help="Filter: tamil,telugu,kannada,hindi,marathi,bangla,english")
    parser.add_argument("--list-channels", action="store_true")
    args = parser.parse_args()

    if args.list_channels:
        groups = {}
        for ch in CHANNELS:
            groups.setdefault(ch["group"], []).append(ch)
        for grp, items in sorted(groups.items()):
            print(f"\n── {grp} ──")
            for ch in items:
                print(f"  {ch['id']:<25} {ch['name']}")
        print(f"\nTotal: {len(CHANNELS)} channels")
        return

    # Filter by language
    if args.lang:
        langs = {LANG_MAP.get(l.strip().lower(), l.strip()) for l in args.lang.split(",")}
        filtered = [ch for ch in CHANNELS if ch["lang"] in langs]
        print(f"[*] Filter: {args.lang} → {len(filtered)} channels")
    else:
        filtered = CHANNELS
        print(f"[*] All {len(filtered)} Zee5 channels")

    days = max(1, min(7, args.days))
    print(f"[*] Fetching {days} day(s) from gwapi.zee5.com ...\n")

    root    = build_epg(filtered, days=days)
    xml_str = prettify(root)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(xml_str)
    print(f"[✓] Saved: {args.output} ({os.path.getsize(args.output)//1024} KB)")

    if args.gz:
        gz = args.output + ".gz"
        with gzip.open(gz, "wb") as f:
            f.write(xml_str.encode())
        print(f"[✓] Saved: {gz} ({os.path.getsize(gz)//1024} KB)")


if __name__ == "__main__":
    main()
