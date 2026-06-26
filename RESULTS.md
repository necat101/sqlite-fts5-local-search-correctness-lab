# SQLite FTS5 Local Search – Results

Generated: 2026-06-26T00:58:55Z

## Environment

- Python: 3.12.3
- SQLite: 3.45.1
- Platform: Linux-6.17.0-1009-aws-x86_64-with-glibc2.39
- FTS5 available: True
- Documents: 120
- Queries: 21
- Database size: 90112 bytes
- Build time: 61.24 ms

## Correctness Summary


| Method | Queries | Top-1 Hit | Recall@3 | Precision@3 | Misleading↑ | Avg ms/query |
|--------|---------|-----------|----------|-------------|-------------|--------------|
| python_substring_scan | 21 | 15/21 | 0.92 | 0.97 | 2 | 3.88 |
| sqlite_like_scan | 21 | 17/21 | 0.87 | 0.87 | 2 | 0.69 |
| sqlite_indexed_exact_title_or_tag | 12 (+9 skipped) | 3/12 | 0.31 | 0.42 | 0 | 0.58 |
| sqlite_fts5_match | 20 (+1 skipped) | 17/20 | 0.92 | 0.95 | 2 | 0.53 |
| sqlite_fts5_bm25 | 20 (+1 skipped) | 15/20 | 0.87 | 0.93 | 1 | 0.57 |
| sqlite_fts5_snippet | 20 (+1 skipped) | 17/20 | 0.87 | 0.90 | 2 | 0.60 |

## Query Categories

- api_path: 1
- code: 1
- exact_rare: 1
- exact_symbol: 3
- natural_language: 2
- negative: 2
- noisy_near_match: 1
- non_english_caveat: 1
- phrase: 1
- punctuation: 2
- ranking: 1
- rare_exact: 1
- unicode: 2
- version: 2

## Tool versions / skip matrix


| Tool | Status |
|------|--------|
| Python sqlite3 | 3.45.1 |
| SQLite FTS5 | available |
| Algolia / Elasticsearch / Meilisearch | not installed – out of scope (server-side, not embedded) |
| ripgrep / jq / datasette | not installed – skipped honestly |

## Commands run

```
python3 -m py_compile generate_corpus.py run_lab.py
python3 generate_corpus.py
python3 run_lab.py
```

## Limitations


- Synthetic corpus only, seed 42 – real-world documents are messier
- Small corpus (~120 docs) – ranking behavior changes at scale
- FTS5 unicode61 tokenizer only – no ICU, no stemming, no compound-word splitting
- No fuzzy search – FTS5 does not include fuzzy matching by default
- No phrase slop / proximity tuning – simple MATCH queries only
- No spelling correction
- Database size includes full content – FTS5 contentless / external content tables not tested
- Client-side / WASM delivery size not measured
- No relevance judgment beyond planted ground truth – real search quality needs human labels

---

_Correctness before speed. A fast search that misses the answer or ranks misleading results first is worse than a slow search that gets it right._
