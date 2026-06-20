#!/usr/bin/env python3
"""
Zee5 EPG Generator
Fetches directly from gwapi.zee5.com/v1/epg using x-access-token

Token Setup:
  1. Browser-ல் zee5.com திறந்து login பண்ணு
  2. F12 → Application → Cookies → xaccesstoken copy பண்ணு
  3. GitHub Secret: ZEE5_TOKEN = <paste here>

Usage:
    python3 zee5_epg.py --token "eyJ..."
    python3 zee5_epg.py --days 3 --output epg.xml --gz
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

EPG_API  = "https://gwapi.zee5.com/v1/epg"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.zee5.com",
    "Referer": "https://www.zee5.com/livetv",
}

CHANNELS = [
    # Tamil
    {"id": "0-9-9z5383487", "tvg_id": "0-9-zeetamil",       "name": "Zee Tamil",              "lang": "ta", "group": "Zee5 Tamil"},
    {"id": "0-9-9z583533",  "tvg_id": "0-9-zeenewstamil",   "name": "Zee News Tamil",         "lang": "ta", "group": "Zee5 Tamil"},
    {"id": "0-9-224",       "tvg_id": "0-9-zeethirai",      "name": "Zee Thirai HD",          "lang": "ta", "group": "Zee5 Tamil"},
    # Telugu
    {"id": "0-9-9z5383485", "tvg_id": "0-9-zeetelugu",      "name": "Zee Telugu",             "lang": "te", "group": "Zee5 Telugu"},
    {"id": "0-9-9z5383488", "tvg_id": "0-9-zeecinemalu",    "name": "Zee Cinemalu",           "lang": "te", "group": "Zee5 Telugu"},
    {"id": "0-9-9z583538",  "tvg_id": "0-9-zeenewstelugu",  "name": "Zee News Telugu",        "lang": "te", "group": "Zee5 Telugu"},
    # Kannada
    {"id": "0-9-9z5383466", "tvg_id": "0-9-zeekannada",     "name": "Zee Kannada",            "lang": "kn", "group": "Zee5 Kannada"},
    {"id": "0-9-9z583537",  "tvg_id": "0-9-zeenewskannada", "name": "Zee News Kannada",       "lang": "kn", "group": "Zee5 Kannada"},
    # Malayalam
    {"id": "0-9-129",       "tvg_id": "0-9-zeekeralam",     "name": "Zee Keralam HD",         "lang": "ml", "group": "Zee5 Malayalam"},
    {"id": "0-9-9z583539",  "tvg_id": "0-9-zeenewsmala",    "name": "Zee News Malayalam",     "lang": "ml", "group": "Zee5 Malayalam"},
    # Marathi
    {"id": "0-9-9z5383486", "tvg_id": "0-9-zeemarathi",     "name": "Zee Marathi",            "lang": "mr", "group": "Zee5 Marathi"},
    {"id": "0-9-zeeyuva",   "tvg_id": "0-9-zeeyuva",        "name": "Zee Yuva",               "lang": "mr", "group": "Zee5 Marathi"},
    {"id": "0-9-zee24taas", "tvg_id": "0-9-zee24taas",      "name": "Zee 24 Taas",            "lang": "mr", "group": "Zee5 Marathi"},
    {"id": "0-9-zeetalkies","tvg_id": "0-9-zeetalkies",     "name": "Zee Talkies HD",         "lang": "mr", "group": "Zee5 Marathi"},
    {"id": "0-9-241",       "tvg_id": "0-9-zeepower",       "name": "Zee Power HD",           "lang": "mr", "group": "Zee5 Marathi"},
    # Bengali
    {"id": "0-9-9z5383484", "tvg_id": "0-9-zeebangla",      "name": "Zee Bangla",             "lang": "bn", "group": "Zee5 Bengali"},
    {"id": "0-9-zeebanglacinema","tvg_id":"0-9-zeebanglasonar","name":"Zee Bangla Sonar",     "lang": "bn", "group": "Zee5 Bengali"},
    {"id": "0-9-216",       "tvg_id": "0-9-zeebiskope",     "name": "Zee Biskope",            "lang": "bn", "group": "Zee5 Bengali"},
    {"id": "0-9-24ghantatv","tvg_id": "0-9-zee24ghanta",    "name": "Zee 24 Ghanta",          "lang": "bn", "group": "Zee5 Bengali"},
    {"id": "0-9-378",       "tvg_id": "0-9-tv9bangla",      "name": "TV9 Bangla",             "lang": "bn", "group": "Zee5 Bengali"},
    # Hindi
    {"id": "0-9-zeetv",     "tvg_id": "0-9-zeetv",          "name": "Zee TV",                 "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-zeetvhd",   "tvg_id": "0-9-zeetvhd",        "name": "Zee TV HD",              "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-zeecinema", "tvg_id": "0-9-zeecinema",      "name": "Zee Cinema",             "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-zeecinemahd","tvg_id":"0-9-zeecinemahd",    "name": "Zee Cinema HD",          "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-zeenews",   "tvg_id": "0-9-zeenews",        "name": "Zee News",               "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-zeebusiness","tvg_id":"0-9-zeebusiness",    "name": "Zee Business",           "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-andtv",     "tvg_id": "0-9-andtv",          "name": "&TV",                    "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-tvhd_0",    "tvg_id": "0-9-andtvhd",        "name": "&TV HD",                 "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-pictures",  "tvg_id": "0-9-andpictures",    "name": "&pictures",              "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-tvpictureshd","tvg_id":"0-9-andpictureshd", "name": "&pictures HD",           "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-zeeanmol",  "tvg_id": "0-9-zeeanmol",       "name": "Anmol TV",               "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-zeeanmolcinema","tvg_id":"0-9-anmolcinema", "name": "Anmol Cinema",           "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-bigganga",  "tvg_id": "0-9-anmolcinema2",   "name": "Anmol Cinema 2",         "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-bigmagic_1786965389","tvg_id":"0-9-bigmagic","name":"Big Magic",              "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-zeeaction", "tvg_id": "0-9-zeeaction",      "name": "Zee Action",             "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-176",       "tvg_id": "0-9-zeeclassic",     "name": "Zee Classic",            "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-zeeclassic","tvg_id": "0-9-zeebollywood",   "name": "Zee Bollywood",          "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-zing",      "tvg_id": "0-9-zing",           "name": "Zing",                   "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-zeehindustan","tvg_id":"0-9-zeebharat",     "name": "Zee Bharat",             "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-251",       "tvg_id": "0-9-tv9bharatvarsh", "name": "TV9 Bharatvarsh",        "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-255",       "tvg_id": "0-9-zeempcg",        "name": "Zee MP CG",              "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-259",       "tvg_id": "0-9-zeerajasthan",   "name": "Zee Rajasthan",          "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-261",       "tvg_id": "0-9-news9",          "name": "News 9",                 "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-zeebiharjharkhand","tvg_id":"0-9-zeebihar", "name": "Zee Bihar Jharkhand",    "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-zeemadhyapradeshchat","tvg_id":"0-9-zeempcg2","name":"Zee Madhya Pradesh CG", "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-zeekalinganews","tvg_id":"0-9-zeedelhi",    "name": "Zee Delhi NCR Haryana",  "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-zeerajasthannews","tvg_id":"0-9-zeerajnews","name":"Zee Rajasthan News",      "lang": "hi", "group": "Zee5 Hindi"},
    {"id": "0-9-channel_265145625","tvg_id":"0-9-zeenewsup","name":"Zee News UP UK",         "lang": "hi", "group": "Zee5 Hindi"},
    # Gujarati
    {"id": "0-9-zee24kalak","tvg_id": "0-9-zee24kalak",     "name": "Zee 24 Kalak",           "lang": "gu", "group": "Zee5 Gujarati"},
    {"id": "0-9-260",       "tvg_id": "0-9-tv9gujarati",    "name": "TV9 Gujarati",           "lang": "gu", "group": "Zee5 Gujarati"},
    # Odia
    {"id": "0-9-sarthaktv", "tvg_id": "0-9-zeesarthak",     "name": "Zee Sarthak",            "lang": "or", "group": "Zee5 Odia"},
    {"id": "0-9-394",       "tvg_id": "0-9-zeechitramandir","name": "Zee Chitramandir",       "lang": "or", "group": "Zee5 Odia"},
    # Punjabi
    {"id": "0-9-zeepunjabharyanahima","tvg_id":"0-9-zeepunjab","name":"Zee Punjab Haryana",   "lang": "pa", "group": "Zee5 Punjabi"},
    {"id": "0-9-215",       "tvg_id": "0-9-zeepunjabi",     "name": "Zee Punjabi",            "lang": "pa", "group": "Zee5 Punjabi"},
    # English
    {"id": "0-9-wion",      "tvg_id": "0-9-wion",           "name": "WION",                   "lang": "en", "group": "Zee5 English"},
    {"id": "0-9-zeecafehd", "tvg_id": "0-9-zeecafe",        "name": "Zee Café HD",            "lang": "en", "group": "Zee5 English"},
    {"id": "0-9-9z5543514", "tvg_id": "0-9-andprivehd",     "name": "&Privé HD",              "lang": "en", "group": "Zee5 English"},
    {"id": "0-9-channel_2105335046","tvg_id":"0-9-andflixhd","name":"&flix HD",               "lang": "en", "group": "Zee5 English"},
    {"id": "0-9-209",       "tvg_id": "0-9-andxplorHD",     "name": "&xplorHD",               "lang": "en", "group": "Zee5 English"},
    {"id": "0-9-348",       "tvg_id": "0-9-zeezest",        "name": "Zee Zest HD",            "lang": "en", "group": "Zee5 English"},
    # News
    {"id": "0-9-aajtak",    "tvg_id": "0-9-aajtak",         "name": "Aaj Tak",                "lang": "hi", "group": "Zee5 News"},
    {"id": "0-9-indiatoday","tvg_id": "0-9-indiatoday",     "name": "India Today",            "lang": "en", "group": "Zee5 News"},
    {"id": "0-9-258",       "tvg_id": "0-9-tv9telugu",      "name": "TV9 Telugu",             "lang": "te", "group": "Zee5 News"},
    {"id": "0-9-257",       "tvg_id": "0-9-tv9marathi",     "name": "TV9 Marathi",            "lang": "mr", "group": "Zee5 News"},
    {"id": "0-9-259",       "tvg_id": "0-9-tv9kannada",     "name": "TV9 Kannada",            "lang": "kn", "group": "Zee5 News"},
]

LANG_MAP = {
    "tamil":"ta","telugu":"te","kannada":"kn","hindi":"hi","marathi":"mr",
    "bengali":"bn","bangla":"bn","gujarati":"gu","english":"en","odia":"or","punjabi":"pa",
}
IST      = timezone(timedelta(hours=5, minutes=30))
IMG_BASE = "https://akamaividz2.zee5.com/image/upload/w_640,h_360/resources/"


def to_xmltv(iso_str: str) -> str:
    """Convert UTC ISO '2026-06-19T18:30:00Z' to IST XMLTV '20260620000000 +0530'"""
    try:
        s = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s).astimezone(IST)
        return dt.strftime("%Y%m%d%H%M%S") + " +0530"
    except Exception:
        return ""


def fetch_day(channels: list, day_offset: int, token: str) -> dict:
    """
    API response structure:
    {
      "items": [
        {
          "id": "0-9-9z5383487",   <- channel id
          "items": [               <- programmes
            {
              "title": "...",
              "start_time": "2026-06-19T18:30:00Z",  (UTC)
              "end_time":   "2026-06-19T19:00:00Z",  (UTC)
              "description": "...",
              "genres": [{"id":"Entertainment","value":"Entertainment"}],
              "list_image": "ZeeTamilXxx123.jpg"
            }
          ]
        }
      ]
    }
    """
    results = {}
    headers = {**HEADERS, "x-access-token": token}
    batch_size = 10

    for i in range(0, len(channels), batch_size):
        batch = channels[i:i+batch_size]
        params = urllib.parse.urlencode({
            "channels": ",".join(c["id"] for c in batch),
            "start": day_offset,
            "end": day_offset,
            "time_offset": "+05:30",
            "page_size": 100,
            "translation": "en",
            "country": "IN",
        })
        url = f"{EPG_API}?{params}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            # Top-level "items" = list of channels, each with nested "items" = programmes
            for ch_data in data.get("items", []):
                cid = ch_data.get("id", "")
                results[cid] = ch_data.get("items", [])
        except Exception as e:
            print(f"  [!] offset={day_offset} batch={i}: {e}", file=sys.stderr)
        time.sleep(0.2)
    return results


def build_epg(channels: list, days: int, token: str) -> ET.Element:
    root = ET.Element("tv")
    root.set("generator-info-name", "zee5-epg")
    root.set("source-info-name", "Zee5")
    root.set("source-info-url", "https://www.zee5.com/livetv")

    for ch in channels:
        el = ET.SubElement(root, "channel")
        el.set("id", ch["tvg_id"])
        dn = ET.SubElement(el, "display-name")
        dn.set("lang", ch["lang"])
        dn.text = ch["name"]
        ET.SubElement(el, "url").text = "https://www.zee5.com/livetv"

    id_map = {ch["id"]: ch for ch in channels}
    total  = 0

    for day in range(days):
        date = (datetime.now(IST) + timedelta(days=day)).strftime("%Y-%m-%d")
        print(f"\n  Day {day+1} ({date}):")
        data = fetch_day(channels, day, token)

        for ch_id, assets in data.items():
            meta = id_map.get(ch_id)
            if not meta:
                continue
            print(f"    {meta['name']}: {len(assets)} programmes")
            for item in assets:
                # Actual API fields from JSON response
                start_iso = item.get("start_time", "")
                end_iso   = item.get("end_time", "")
                title     = (item.get("title") or "").strip() or "Unknown"
                if not start_iso or not end_iso:
                    continue

                start_xmltv = to_xmltv(start_iso)
                end_xmltv   = to_xmltv(end_iso)
                if not start_xmltv or not end_xmltv:
                    continue

                prog = ET.SubElement(root, "programme")
                prog.set("start",   start_xmltv)
                prog.set("stop",    end_xmltv)
                prog.set("channel", meta["tvg_id"])

                t = ET.SubElement(prog, "title")
                t.set("lang", meta["lang"])
                t.text = title

                desc = (item.get("description") or "").strip()
                if desc:
                    d = ET.SubElement(prog, "desc")
                    d.set("lang", meta["lang"])
                    d.text = desc

                # genres: [{"id":"Entertainment","value":"Entertainment"}]
                genres = item.get("genres", [])
                if genres:
                    cat = ET.SubElement(prog, "category")
                    cat.set("lang", "en")
                    cat.text = genres[0].get("value", "")

                # list_image: "ZeeTamilXxx123.jpg"
                list_img = item.get("list_image", "")
                if list_img:
                    img_url = IMG_BASE + list_img if not list_img.startswith("http") else list_img
                    ET.SubElement(prog, "icon").set("src", img_url)

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
    parser.add_argument("--token",  default=os.environ.get("ZEE5_TOKEN",""), help="x-access-token (or set ZEE5_TOKEN env)")
    parser.add_argument("--days",   type=int, default=1)
    parser.add_argument("--output", default="zee5_epg.xml")
    parser.add_argument("--gz",     action="store_true")
    parser.add_argument("--lang",   default="")
    parser.add_argument("--list-channels", action="store_true")
    args = parser.parse_args()

    if args.list_channels:
        groups = {}
        for ch in CHANNELS:
            groups.setdefault(ch["group"], []).append(ch)
        for grp, items in sorted(groups.items()):
            print(f"\n── {grp} ──")
            for ch in items:
                print(f"  {ch['id']:<35} {ch['name']}")
        print(f"\nTotal: {len(CHANNELS)} channels")
        return

    if not args.token:
        print("[✗] Token required! Use --token or set ZEE5_TOKEN env variable")
        print("    Browser → zee5.com → F12 → Application → Cookies → xaccesstoken")
        sys.exit(1)

    if args.lang:
        langs = {LANG_MAP.get(l.strip().lower(), l.strip()) for l in args.lang.split(",")}
        filtered = [ch for ch in CHANNELS if ch["lang"] in langs]
        print(f"[*] Filter: {args.lang} → {len(filtered)} channels")
    else:
        filtered = CHANNELS
        print(f"[*] All {len(filtered)} Zee5 channels")

    days = max(1, min(7, args.days))
    print(f"[*] Fetching {days} day(s) ...\n")

    root    = build_epg(filtered, days, args.token)
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
