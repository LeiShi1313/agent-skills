#!/usr/bin/env python3
"""Query movie/TV metadata and ratings from PtGen (Douban/IMDb)."""
import argparse
import json
import sys
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

CDN_BASE = "https://cdn.ourhelp.club/ptgen"
API_BASE = "https://api.ourhelp.club/infogen"


def fetch_json(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def query_one(site, sid):
    """Query a single ID. Try CDN first, fall back to API."""
    try:
        return fetch_json(f"{CDN_BASE}/{site}/{sid}.json")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            try:
                return fetch_json(f"{API_BASE}?site={site}&sid={sid}", timeout=15)
            except Exception:
                return None
        return None
    except Exception:
        return None


def normalize(data, site, sid):
    """Extract a flat dict of useful fields from PtGen response."""
    if not data:
        return {"query_site": site, "query_id": sid, "error": "not_found"}

    is_douban = site == "douban"

    # Title: douban uses chinese_title/foreign_title, imdb uses name
    if is_douban:
        title = data.get("chinese_title", "") or data.get("foreign_title", "")
        foreign_title = data.get("foreign_title", "")
    else:
        title = data.get("name", "") or ""
        foreign_title = title

    # Type: douban has episodes field, imdb has @type
    if is_douban:
        episodes = data.get("episodes", "")
        media_type = "tv" if episodes else "movie"
    else:
        at_type = data.get("@type", "")
        media_type = "tv" if at_type in ("TVSeries", "TVMiniSeries", "TVEpisode") else "movie"
        episodes = ""

    # Duration: imdb uses ISO 8601 (PT3H15M), douban uses Chinese (137分钟)
    duration = data.get("duration", "") or ""

    # Director/cast: douban uses director/cast, imdb uses directors/actors
    directors = data.get("director", []) or data.get("directors", []) or []
    cast = data.get("cast", []) or data.get("actors", []) or []

    # Region: douban only
    region = data.get("region", []) or []

    return {
        "query_site": site,
        "query_id": sid,
        "title": title,
        "foreign_title": foreign_title,
        "year": data.get("year", "") or data.get("datePublished", "")[:4],
        "type": media_type,
        "episodes": episodes,
        "duration": duration,
        "genre": data.get("genre", []),
        "region": region,
        "douban_rating": data.get("douban_rating_average", None),
        "douban_votes": data.get("douban_votes", ""),
        "douban_link": data.get("douban_link", ""),
        "imdb_rating": data.get("imdb_rating_average", None),
        "imdb_votes": data.get("imdb_votes", None),
        "imdb_id": data.get("imdb_id", "") or (sid if not is_douban else ""),
        "director": [d.get("name", "") for d in directors][:3],
        "cast": [c.get("name", "") for c in cast][:5],
        "introduction": (data.get("introduction", "") or data.get("description", "") or "")[:200],
    }


def query_batch(site, ids):
    """Query multiple IDs in parallel."""
    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(query_one, site, sid): sid for sid in ids}
        for f in as_completed(futures):
            sid = futures[f]
            data = f.result()
            results.append(normalize(data, site, sid))
    # Preserve input order
    order = {sid: i for i, sid in enumerate(ids)}
    results.sort(key=lambda r: order.get(r["query_id"], 0))
    return results


def fmt_table(results):
    """Format results as a human/agent-readable table."""
    lines = []
    hdr = f"{'类型':<4} | {'豆瓣':>4} | {'IMDB':>4} | {'集数':<4} | {'名称':<30} | {'年份':<4} | {'类别':<18} | {'地区':<10} | {'时长':<12} | {'导演':<16} | {'ID':<12}"
    lines.append(hdr)
    lines.append("-" * len(hdr))
    for r in results:
        if "error" in r:
            lines.append(f"{'?':<4} | {'':>4} | {'':>4} | {'':4} | {'[未找到]':<30} | {'':4} | {'':18} | {'':10} | {'':12} | {'':16} | {r['query_id']:<12}")
            continue
        db_val = r.get("douban_rating")
        db = f"{float(db_val):.1f}" if db_val is not None and db_val != 0 else ""
        imdb_val = r.get("imdb_rating")
        imdb = f"{float(imdb_val):.1f}" if imdb_val is not None and imdb_val != 0 else ""
        genre = ", ".join(r.get("genre", []))[:18]
        region = ", ".join(r.get("region", []))[:10]
        director = ", ".join(r.get("director", []))[:16]
        title = (r.get("title", "") or "")[:30]
        duration = (r.get("duration", "") or "")[:12]
        episodes = r.get("episodes", "") or ""
        tp = r.get("type", "")
        lines.append(
            f"{tp:<4} | {db:>4} | {imdb:>4} | {episodes:<4} | {title:<30} | {r.get('year',''):<4} | {genre:<18} | {region:<10} | {duration:<12} | {director:<16} | {r['query_id']:<12}"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Query PtGen for movie/TV metadata and ratings")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--douban", nargs="+", metavar="ID", help="Douban subject ID(s)")
    group.add_argument("--imdb", nargs="+", metavar="ID", help="IMDb ID(s), e.g. tt1234567")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--table", action="store_true", help="Output as table (default)")
    args = parser.parse_args()

    if args.douban:
        site, ids = "douban", args.douban
    else:
        site, ids = "imdb", [i.lstrip("t") if i.startswith("tt") else i for i in args.imdb]
        # PtGen uses numeric IMDb IDs without 'tt' prefix — keep as-is, it varies;
        # actually PtGen expects the full tt-prefixed ID for imdb site
        ids = args.imdb

    results = query_batch(site, ids)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(fmt_table(results))


if __name__ == "__main__":
    main()
