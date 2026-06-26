# VERIFY.md – Fresh Clone Verification

This file proves the repository works end-to-end from a clean checkout.

## Clone

```
$ git clone https://github.com/necat101/sqlite-fts5-local-search-correctness-lab.git fts5-verify
Cloning into 'fts5-verify'...
```

## Compile check

```
$ cd fts5-verify
$ python3 -m py_compile generate_corpus.py run_lab.py
$ echo $?
0
```

**py_compile exit code: 0** – both scripts are syntax-valid.

## Generate corpus

```
$ python3 generate_corpus.py
Generated 120 documents
ID range: 1 .. 120
Corpus: 120 documents -> corpus/corpus.json
Queries: 21 queries -> corpus/queries.json

Query breakdown:
  api_path              1
  code                  1
  exact_rare            1
  exact_symbol          3
  natural_language      2
  negative              2
  noisy_near_match      1
  non_english_caveat    1
  phrase                1
  punctuation           2
  ranking               1
  rare_exact            1
  unicode               2
  version               2
```

## Run benchmark

```
$ python3 run_lab.py
Python: 3.12.3
SQLite: 3.45.1
Platform: Linux-6.17.0-1009-aws-x86_64-with-glibc2.39

Corpus: 120 documents
Queries: 21 queries

Database built in 58.22 ms, size: 90112 bytes
FTS5 available: True

python_substring_scan:
  Queries: 21, Skipped: 0, Top-1 hit: 15/21, Recall@3: 0.92, Precision@3: 0.97, Misleading ranked first: 2
sqlite_like_scan:
  Queries: 21, Skipped: 0, Top-1 hit: 17/21, Recall@3: 0.87, Precision@3: 0.87, Misleading ranked first: 2
sqlite_indexed_exact_title_or_tag:
  Queries: 12, Skipped: 9, Top-1 hit: 3/12, Recall@3: 0.31, Precision@3: 0.42, Misleading ranked first: 0
sqlite_fts5_match:
  Queries: 20, Skipped: 1, Top-1 hit: 17/20, Recall@3: 0.92, Precision@3: 0.95, Misleading ranked first: 2
sqlite_fts5_bm25:
  Queries: 20, Skipped: 1, Top-1 hit: 15/20, Recall@3: 0.87, Precision@3: 0.93, Misleading ranked first: 1
sqlite_fts5_snippet:
  Queries: 20, Skipped: 1, Top-1 hit: 17/20, Recall@3: 0.87, Precision@3: 0.90, Misleading ranked first: 2

Results written to RESULTS.md
Memory: current=505.7 KB, peak=713.5 KB
Done.
```

**Exit code: 0**

## Verification Summary

- ✅ Repository clones successfully from GitHub
- ✅ `python3 -m py_compile generate_corpus.py run_lab.py` → exit code 0
- ✅ `python3 generate_corpus.py` → 120 documents, 21 queries generated, exit code 0
- ✅ `python3 run_lab.py` → all 21 queries × 6 methods tested, exit code 0
- ✅ RESULTS.md generated with correctness and timing tables
- ✅ results/results.json written (full machine-readable output)
- ✅ search.db created (90 KB, FTS5 enabled)
- ✅ Correctness results match expected: FTS5 MATCH 17/20 top-1, BM25 15/20 top-1, SQLite LIKE 17/21, Python substring 15/21 – ranking and tokenizer caveats visible as expected

## Environment (verification run)

- Python: 3.12.3
- SQLite: 3.45.1
- Platform: Linux-6.17.0-1009-aws-x86_64-with-glibc2.39
- FTS5: available

## Files in repo

```
generate_corpus.py   14768 bytes
run_lab.py           20118 bytes
README.md             6556 bytes
RESULTS.md            2373 bytes
.gitignore              70 bytes
VERIFY.md          (this file)
```

Total: ~44 KB

No external dependencies beyond Python stdlib (sqlite3, json). No network calls during benchmark. No downloads. Corpus generated locally with fixed seed (42).

---

Verified: 2026-06-26T01:08:00Z
Commit: 262811ae3c2d6897ff7d1a6a2bea8f071be800b2
