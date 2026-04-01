---
name: ptgen
description: Use when you have Douban subject IDs or IMDb IDs and need to look up ratings, metadata (director, cast, genre, year, type), or distinguish movie vs TV series for those IDs
---

# PtGen — Movie & TV Metadata Lookup

Query Douban and IMDb ratings, cast, genre, and other metadata via the PtGen API.

## Script Location

All paths below are relative to this skill's base directory (provided by the agent harness at load time).

```
scripts/ptgen.py
```

Run with: `python3 <skill_base_dir>/scripts/ptgen.py`

## Usage

### By Douban ID

```bash
# Single
python3 scripts/ptgen.py --douban 1291546

# Batch
python3 scripts/ptgen.py --douban 1291546 1302425 1393859
```

### By IMDb ID

```bash
# Single
python3 scripts/ptgen.py --imdb tt0108052

# Batch
python3 scripts/ptgen.py --imdb tt0108052 tt32897959
```

### Output Formats

```bash
# Table (default) — human and agent readable
python3 scripts/ptgen.py --douban 1291546

# JSON — for piping or programmatic use
python3 scripts/ptgen.py --douban 1291546 --json
```

## Returned Fields

| Field | Description |
|-------|-------------|
| `type` | `movie` or `tv` — derived from `episodes` (Douban) or `@type` (IMDb) |
| `title` | Chinese title (Douban) or English name (IMDb) |
| `foreign_title` | Original/English title |
| `year` | Release year |
| `episodes` | Episode count (non-empty = TV series) |
| `duration` | Runtime |
| `genre` | Genre list |
| `region` | Production region (Douban only) |
| `douban_rating` | Douban score (0-10), null if unavailable |
| `imdb_rating` | IMDb score (0-10), null if unavailable |
| `douban_votes` | Douban rating count |
| `imdb_votes` | IMDb rating count |
| `imdb_id` | IMDb ID (e.g. tt0108052) |
| `douban_link` | Douban URL |
| `director` | Director names (up to 3) |
| `cast` | Cast names (up to 5) |
| `introduction` | Synopsis (up to 200 chars) |

## How It Works

1. Tries PtGen CDN static files first (`cdn.ourhelp.club/ptgen/<site>/<id>.json`)
2. Falls back to PtGen API (`api.ourhelp.club/infogen`) on 404
3. Batch queries run in parallel (8 workers)

## Determining Movie vs TV

- **Douban source**: `episodes` field non-empty → TV, empty → movie
- **IMDb source**: `@type` field is `TVSeries`/`TVMiniSeries` → TV, otherwise → movie

## Common Patterns

```bash
# Check if something is a movie or TV show
python3 scripts/ptgen.py --douban 36963690 --json | python3 -c "import sys,json;d=json.load(sys.stdin);print(d[0]['type'])"

# Get just the Douban rating
python3 scripts/ptgen.py --douban 36963690 --json | python3 -c "import sys,json;d=json.load(sys.stdin);print(d[0]['douban_rating'])"

# Batch lookup and filter high-rated movies
python3 scripts/ptgen.py --douban 1291546 1302425 1393859 --json | python3 -c "
import sys,json
for r in json.load(sys.stdin):
    if r.get('douban_rating') and r['douban_rating'] >= 8.0:
        print(f\"{r['douban_rating']:.1f} {r['title']} ({r['year']}) [{r['type']}]\")
"
```
