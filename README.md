# SQLite FTS5 Local Search Correctness Lab

A tiny, auditable correctness lab about SQLite full-text search versus simpler local search baselines.

Inspired by HN thread: https://news.ycombinator.com/item?id=41198422 ("SQLite FTS5 Extension")

## What HN users were debating

SQLite FTS5 is attractive as an **embedded/local search engine**:

- **"Good enough search in one SQLite file"** – useful for blogs, docs, apps, offline/client-side tools
- **WASM port with FTS5** – some HN users claim it's "the best general purpose client-side search engine currently on the market"
- **Custom tokenizers and auxiliary functions** – can do advanced stuff, rivalling Lucene (not completely – FTS5 does not store offsets, so highlighting is more expensive)
- **peewee ORM supports it directly** – easy integration in Python apps
- **"Pretend it's an LLM"** – one HN user joked about using FTS5 for legal document search and pretending it's an LLM

But FTS5 is **not automatically the same thing as Algolia / Elasticsearch / Meilisearch**:

- **Ranking with bm25 matters** – raw MATCH results without ranking can be noisy
- **Query syntax can surprise people** – FTS5 has its own query language, not just free text
- **Fuzzy search is not built in by default** – need spellfix extension or external handling
- **Tokenizer and non-English behavior need caveats** – the HN thread specifically calls out German/Swedish/Finnish compound words: searching for `angriff` won't match `Raketenangriff` with the default unicode61 tokenizer. Meilisearch has the same problem, no suffix search, tokenizer can't handle these languages
- **Exact substring search vs full-text token search are different** – FTS5 tokenizes, so it won't find substrings inside tokens (unless using trigram tokenizer, which inflates database size)
- **Database size and client-side delivery matter** – one HN user tried sql.js with FTS5 on a static site, database was too large for the web even with `detail=none` and `content=''`. sql.js-httpvfs (HTTP range requests) helps, and Pagefind is an alternative
- **Server vs embedded tradeoff** – Meilisearch is MIT licensed and theoretically embeddable in iOS, but it's Rust-based, geared toward Docker/server environments, not trivial to bundle client-side. SQLite+FTS5 is trivially embeddable everywhere

The point of this lab: **test the HN debate in a tiny reproducible way**. FTS5 can be a very useful embedded/local search tool, but ranking, tokenizer behavior, query syntax, exact substring matching, fuzzy search, non-English text, and no-result handling all matter.

## What this lab does

- Generates ~120 deterministic documents (blog posts, docs pages, notes, code snippets) with planted ground truth (seed 42)
- 20-35 planted queries covering: exact rare term, phrase, natural language, title/tag, version number, punctuation, unicode/accent, emoji, non-English caveat (German compound), misleading near-match, ranking-sensitive, negative/no-result
- Compares 6 methods:
  1. **python_substring_scan** – Python lowercased substring scan over title/tags/body
  2. **sqlite_like_scan** – SQLite `WHERE title/body/tags LIKE '%term%'`
  3. **sqlite_indexed_exact_title_or_tag** – B-tree indexed exact title/tag lookup (skip unsupported queries)
  4. **sqlite_fts5_match** – FTS5 `MATCH` query (skip if FTS5 unavailable)
  5. **sqlite_fts5_bm25** – FTS5 `MATCH` ordered by `bm25()` (skip if unavailable)
  6. **sqlite_fts5_snippet** – FTS5 snippet/highlight demo (skip if unavailable)
- Validates retrieval correctness **before** speed: top-1 hit rate, recall@3, precision@3, negative-query correctness, near-match failure count
- Measures: corpus generation time, SQLite build time, query time, database size, row count
- No external dependencies – Python stdlib only (`sqlite3`, `json`)
- No compilers, no package managers, no root installs, no Docker, no downloading repos, no network calls during benchmark

## Running it

```bash
python3 -m py_compile generate_corpus.py run_lab.py
python3 generate_corpus.py
python3 run_lab.py
```

Output:
- `RESULTS.md` – correctness tables, timing, skip matrix, FTS5 availability
- `results/results.json` – full machine-readable results
- `search.db` – SQLite database (gitignored)

## Results (summary)

See [RESULTS.md](RESULTS.md) for full tables.

Expected outcome: Python substring scan and SQLite LIKE find exact substrings (including inside German compound words) but have no ranking – misleading near-matches with many repeated terms can rank first. FTS5 with BM25 ranking generally does better on natural-language queries but fails on substring-inside-token cases (e.g., `angriff` in `Raketenangriff`) with the default unicode61 tokenizer – exactly as the HN thread warns. Exact title/tag B-tree lookup is fast and precise when applicable, but only works for exact matches.

## Why this lab is intentionally tiny

- A few hundred lines total
- Python stdlib only (`sqlite3`, `json`)
- No external downloads
- No package installs
- Deterministic, reproducible (seed 42)
- Correctness before speed
- Honest skip matrix – if FTS5 is not available in the Python sqlite3 build, skip those rows clearly with the exact error, don't fake results

The goal is not to prove SQLite FTS5 beats every search engine globally. The goal is to test, in a tiny auditable way, the specific claims from the HN debate: **FTS5 is a very useful embedded/local search tool, but ranking, tokenizer behavior, query syntax, and non-English text all have real caveats that affect correctness**.

## Related

- Code search retrieval lab: https://github.com/necat101/code-search-retrieval-benchmark-lab – compares grep/ripgrep/BM25/FTS5/semble for code search, HN thread "code search for agents"
- CSV edge-case lab: https://github.com/necat101/csv-edge-case-correctness-lab – CSV parsing edge cases, HN "a love letter to the CSV format"
- CSV command-line lab: https://github.com/necat101/csv-commandline-correctness-lab – CSV CLI tools, HN "Using command line to process CSV files"
- Shell JSON quoting lab: https://github.com/necat101/shell-json-quoting-correctness-lab – JSON generation in shell, HN jb/json.bash thread
- Regex engine benchmark: https://github.com/necat101/regex-engine-benchmark-lab
- Syntax-aware merge benchmark: https://github.com/necat101/syntax-aware-merge-correctness-benchmark-lab

---

_Correctness before speed. A fast search that misses the answer or ranks misleading results first is worse than a slow search that gets it right._
