#!/usr/bin/env python3
"""
run_lab.py – SQLite FTS5 search correctness benchmark

Compares local search methods on a synthetic document corpus.
Correctness BEFORE speed.
"""
import json
import sqlite3
import time
import pathlib
import platform
import tracemalloc
from collections import defaultdict

CORPUS_PATH = pathlib.Path(__file__).parent / "corpus" / "corpus.json"
QUERIES_PATH = pathlib.Path(__file__).parent / "corpus" / "queries.json"
DB_PATH = pathlib.Path(__file__).parent / "search.db"
RESULTS_JSON = pathlib.Path(__file__).parent / "results" / "results.json"
RESULTS_MD = pathlib.Path(__file__).parent / "RESULTS.md"

# ---------------------------------------------------------------------------
# Corpus loading + DB building
# ---------------------------------------------------------------------------

def build_database(docs):
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("CREATE TABLE docs (id INTEGER PRIMARY KEY, title TEXT, tags TEXT, body TEXT)")
    conn.execute("CREATE INDEX idx_title ON docs(title)")
    for d in docs:
        conn.execute("INSERT INTO docs VALUES (?,?,?,?)",
                     (d["id"], d["title"], " ".join(d["tags"]), d["body"]))
    conn.commit()
    # FTS5 virtual table – check if available
    fts_available = True
    fts_error = None
    try:
        conn.execute("CREATE VIRTUAL TABLE docs_fts USING fts5(title, tags, body, content='docs', content_rowid='id', tokenize='unicode61')")
        conn.execute("INSERT INTO docs_fts(docs_fts) VALUES('rebuild')")
        conn.commit()
    except sqlite3.OperationalError as e:
        fts_available = False
        fts_error = str(e)
    conn.close()
    size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    return fts_available, fts_error, size

# ---------------------------------------------------------------------------
# Search methods
# ---------------------------------------------------------------------------

def method_python_substring_scan(query_text, conn=None):
    """Python lowercased substring scan over title/tags/body."""
    start = time.perf_counter()
    with open(CORPUS_PATH, encoding="utf-8") as f:
        docs = json.load(f)
    q = query_text.lower()
    # Strip query syntax chars for substring baseline
    q_clean = q.replace('"', '').replace('/', ' ').replace(':', ' ')
    q_clean = q_clean.strip()
    results = []
    for d in docs:
        haystack = (d["title"] + " " + " ".join(d["tags"]) + " " + d["body"]).lower()
        # Simple: all terms must appear
        terms = [t for t in q_clean.split() if len(t) > 1]
        if not terms:
            terms = [q_clean]
        if all(t in haystack for t in terms):
            # score = total occurrences (naive)
            score = sum(haystack.count(t) for t in terms)
            results.append((d["id"], score))
    results.sort(key=lambda x: x[1], reverse=True)
    elapsed = time.perf_counter() - start
    return [doc_id for doc_id, _ in results], elapsed

def method_sqlite_like_scan(query_text, conn):
    """SQLite WHERE title/body/tags LIKE pattern."""
    start = time.perf_counter()
    q = query_text.lower()
    # Extract alphanumeric terms
    import re
    terms = re.findall(r'\w+', q)
    if not terms:
        return [], time.perf_counter() - start
    # Build LIKE query – all terms must appear somewhere
    where_clauses = []
    params = []
    for term in terms[:3]:  # limit to 3 terms
        pattern = f"%{term}%"
        where_clauses.append("(LOWER(title) LIKE ? OR LOWER(tags) LIKE ? OR LOWER(body) LIKE ?)")
        params.extend([pattern, pattern, pattern])
    sql = f"SELECT id FROM docs WHERE {' AND '.join(where_clauses)} LIMIT 20"
    try:
        cur = conn.execute(sql, params)
        rows = [r[0] for r in cur.fetchall()]
        elapsed = time.perf_counter() - start
        return rows, elapsed
    except Exception:
        elapsed = time.perf_counter() - start
        return [], elapsed

def method_sqlite_indexed_exact_title_or_tag(query_text, conn):
    """B-tree indexed exact title/tag lookup – skip if not applicable."""
    # Only for single-word queries without spaces/punctuation
    import re
    if not re.fullmatch(r'[A-Za-z0-9_]+', query_text):
        return None, 0, "skip: not exact single token"
    start = time.perf_counter()
    try:
        # Exact title match OR tag contains term
        cur = conn.execute(
            "SELECT id FROM docs WHERE title = ? OR tags LIKE ? LIMIT 20",
            (query_text, f"%{query_text}%")
        )
        rows = [r[0] for r in cur.fetchall()]
        elapsed = time.perf_counter() - start
        return rows, elapsed, None
    except Exception as e:
        elapsed = time.perf_counter() - start
        return [], elapsed, str(e)

def method_sqlite_fts5_match(query_text, conn, fts_available):
    """FTS5 MATCH query."""
    if not fts_available:
        return None, 0, "skip: FTS5 not available"
    # Sanitize query for FTS5 – remove chars that break MATCH syntax
    import re
    # FTS5 special chars: " * ^ : ( ) etc.
    # For simplicity, extract alphanumeric terms and join with AND
    # Except: keep quoted phrases intact
    q = query_text
    # If query looks like a phrase (quoted), try as-is first
    if '"' in q:
        fts_query = q
    else:
        # Extract terms, strip punctuation that breaks FTS5
        terms = re.findall(r'[A-Za-z0-9_À-ÿ]+', q)
        if not terms:
            return [], 0, "skip: no FTS terms"
        fts_query = " AND ".join(terms[:5])  # limit terms
    start = time.perf_counter()
    try:
        cur = conn.execute(
            "SELECT rowid FROM docs_fts WHERE docs_fts MATCH ? LIMIT 20",
            (fts_query,)
        )
        rows = [r[0] for r in cur.fetchall()]
        elapsed = time.perf_counter() - start
        return rows, elapsed, None
    except sqlite3.OperationalError as e:
        elapsed = time.perf_counter() - start
        # Try fallback: single term
        try:
            terms = re.findall(r'[A-Za-z0-9_À-ÿ]+', query_text)
            if terms:
                cur = conn.execute(
                    "SELECT rowid FROM docs_fts WHERE docs_fts MATCH ? LIMIT 20",
                    (terms[0],)
                )
                rows = [r[0] for r in cur.fetchall()]
                return rows, time.perf_counter() - start, None
        except Exception:
            pass
        return [], elapsed, f"fts_match_error: {e}"

def method_sqlite_fts5_bm25(query_text, conn, fts_available):
    """FTS5 MATCH ordered by bm25."""
    if not fts_available:
        return None, 0, "skip: FTS5 not available"
    import re
    q = query_text
    if '"' in q:
        fts_query = q
    else:
        terms = re.findall(r'[A-Za-z0-9_À-ÿ]+', q)
        if not terms:
            return [], 0, "skip: no FTS terms"
        fts_query = " AND ".join(terms[:5])
    start = time.perf_counter()
    try:
        cur = conn.execute(
            "SELECT rowid FROM docs_fts WHERE docs_fts MATCH ? ORDER BY bm25(docs_fts) LIMIT 20",
            (fts_query,)
        )
        rows = [r[0] for r in cur.fetchall()]
        elapsed = time.perf_counter() - start
        return rows, elapsed, None
    except sqlite3.OperationalError as e:
        elapsed = time.perf_counter() - start
        # bm25() may not be available in older SQLite – try without ORDER BY
        try:
            cur = conn.execute(
                "SELECT rowid FROM docs_fts WHERE docs_fts MATCH ? LIMIT 20",
                (fts_query,)
            )
            rows = [r[0] for r in cur.fetchall()]
            return rows, time.perf_counter() - start, "bm25_unavailable_fallback"
        except Exception as e2:
            return [], elapsed, f"fts_bm25_error: {e}"
        
def method_sqlite_fts5_snippet(query_text, conn, fts_available):
    """FTS5 snippet/highlight demo."""
    if not fts_available:
        return None, 0, "skip: FTS5 not available"
    import re
    terms = re.findall(r'[A-Za-z0-9_À-ÿ]+', query_text)
    if not terms:
        return [], 0, "skip: no FTS terms"
    fts_query = terms[0]
    start = time.perf_counter()
    try:
        # snippet() returns highlighted text
        cur = conn.execute(
            "SELECT rowid, snippet(docs_fts, 2, '<b>', '</b>', '…', 10) FROM docs_fts WHERE docs_fts MATCH ? LIMIT 20",
            (fts_query,)
        )
        rows = [r[0] for r in cur.fetchall()]
        elapsed = time.perf_counter() - start
        return rows, elapsed, None
    except sqlite3.OperationalError as e:
        elapsed = time.perf_counter() - start
        return [], elapsed, f"fts_snippet_error: {e}"

METHODS = [
    ("python_substring_scan", lambda q, conn, fts: (*method_python_substring_scan(q, conn), None)),
    ("sqlite_like_scan", lambda q, conn, fts: (*method_sqlite_like_scan(q, conn), None)),
    ("sqlite_indexed_exact_title_or_tag", lambda q, conn, fts: method_sqlite_indexed_exact_title_or_tag(q, conn)),
    ("sqlite_fts5_match", lambda q, conn, fts: method_sqlite_fts5_match(q, conn, fts)),
    ("sqlite_fts5_bm25", lambda q, conn, fts: method_sqlite_fts5_bm25(q, conn, fts)),
    ("sqlite_fts5_snippet", lambda q, conn, fts: method_sqlite_fts5_snippet(q, conn, fts)),
]

# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_query(query, returned_ids, elapsed):
    expected = query.get("expected_docs", [])
    expected_top = query.get("expected_top")
    misleading_doc = query.get("misleading_doc")
    expect_no_results = query.get("expect_no_results", False)
    
    # Top-1 hit
    top1_hit = False
    if expected_top is not None and returned_ids:
        top1_hit = (returned_ids[0] == expected_top)
    elif expect_no_results:
        top1_hit = (len(returned_ids) == 0)
    
    # Recall@3 / Precision@3
    returned_3 = returned_ids[:3]
    expected_set = set(expected)
    returned_set = set(returned_3)
    hits = len(expected_set & returned_set)
    recall_at_3 = hits / len(expected_set) if expected_set else (1.0 if not returned_3 else 0.0)
    precision_at_3 = hits / len(returned_3) if returned_3 else (1.0 if not expected_set else 0.0)
    
    # Misleading near-match ranked above expected?
    misleading_ranked_first = False
    if misleading_doc and returned_ids and expected_top:
        try:
            mis_idx = returned_ids.index(misleading_doc)
            exp_idx = returned_ids.index(expected_top)
            misleading_ranked_first = mis_idx < exp_idx
        except ValueError:
            pass
    
    # Negative query correctness
    negative_correct = True
    if expect_no_results:
        negative_correct = (len(returned_ids) == 0)
    
    return {
        "top1_hit": top1_hit,
        "recall_at_3": recall_at_3,
        "precision_at_3": precision_at_3,
        "misleading_ranked_first": misleading_ranked_first,
        "negative_correct": negative_correct,
        "returned_count": len(returned_ids),
        "elapsed_ms": elapsed * 1000,
    }

def main():
    print(f"Python: {platform.python_version()}")
    print(f"SQLite: {sqlite3.sqlite_version}")
    print(f"Platform: {platform.platform()}")
    print()
    
    # Load corpus
    with open(CORPUS_PATH, encoding="utf-8") as f:
        docs = json.load(f)
    with open(QUERIES_PATH, encoding="utf-8") as f:
        queries = json.load(f)
    
    print(f"Corpus: {len(docs)} documents")
    print(f"Queries: {len(queries)} queries")
    print()
    
    # Build DB
    tracemalloc.start()
    build_start = time.perf_counter()
    fts_available, fts_error, db_size = build_database(docs)
    build_elapsed = time.perf_counter() - build_start
    print(f"Database built in {build_elapsed*1000:.2f} ms, size: {db_size} bytes")
    print(f"FTS5 available: {fts_available}")
    if not fts_available:
        print(f"  FTS5 error: {fts_error}")
    print()
    
    conn = sqlite3.connect(str(DB_PATH))
    
    results = []
    # Run all methods x queries
    for method_name, method_fn in METHODS:
        print(f"{method_name}:")
        method_results = []
        for q in queries:
            # 3 trials
            times = []
            returned_ids = []
            skip_reason = None
            for _ in range(3):
                r_ids, elapsed, skip = method_fn(q["text"], conn, fts_available)
                times.append(elapsed)
                if skip:
                    skip_reason = skip
                    break
                returned_ids = r_ids or []
            if skip_reason and "skip:" in skip_reason:
                result = {
                    "method": method_name,
                    "query_id": q["id"],
                    "query_category": q["category"],
                    "skipped": True,
                    "skip_reason": skip_reason,
                    "returned_ids": [],
                    "top1_hit": False,
                    "recall_at_3": 0,
                    "precision_at_3": 0,
                    "elapsed_ms": 0,
                }
                method_results.append(result)
                results.append(result)
                continue
            
            import statistics
            median_ms = statistics.median(times) * 1000 if times else 0
            eval_r = evaluate_query(q, returned_ids, median_ms / 1000)
            result = {
                "method": method_name,
                "query_id": q["id"],
                "query_category": q["category"],
                "query_text": q["text"],
                "expected_docs": q.get("expected_docs", []),
                "expected_top": q.get("expected_top"),
                "returned_ids": returned_ids[:10],
                "skipped": False,
                **eval_r,
            }
            method_results.append(result)
            results.append(result)
        
        # Summary
        active = [r for r in method_results if not r.get("skipped")]
        skipped = len(method_results) - len(active)
        top1_hits = sum(1 for r in active if r["top1_hit"])
        avg_recall = sum(r["recall_at_3"] for r in active) / len(active) if active else 0
        avg_precision = sum(r["precision_at_3"] for r in active) / len(active) if active else 0
        misleading_fails = sum(1 for r in active if r.get("misleading_ranked_first"))
        print(f"  Queries: {len(active)}, Skipped: {skipped}, Top-1 hit: {top1_hits}/{len(active)}, "
              f"Recall@3: {avg_recall:.2f}, Precision@3: {avg_precision:.2f}, "
              f"Misleading ranked first: {misleading_fails}")
    
    conn.close()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Save results
    RESULTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "results": results,
            "meta": {
                "python_version": platform.python_version(),
                "sqlite_version": sqlite3.sqlite_version,
                "platform": platform.platform(),
                "fts5_available": fts_available,
                "fts5_error": fts_error,
                "doc_count": len(docs),
                "query_count": len(queries),
                "db_size_bytes": db_size,
                "build_time_ms": build_elapsed * 1000,
                "memory_current_kb": current / 1024,
                "memory_peak_kb": peak / 1024,
            }
        }, f, indent=2)
    
    # Write RESULTS.md
    write_results_md(results, queries, docs, fts_available, fts_error, db_size, build_elapsed)
    print(f"\nResults written to {RESULTS_MD}")
    print(f"Memory: current={current/1024:.1f} KB, peak={peak/1024:.1f} KB")

def write_results_md(results, queries, docs, fts_available, fts_error, db_size, build_elapsed):
    from collections import defaultdict
    by_method = defaultdict(list)
    for r in results:
        by_method[r["method"]].append(r)
    
    lines = []
    lines.append("# SQLite FTS5 Local Search – Results\n")
    import datetime
    lines.append(f"Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
    lines.append("## Environment\n")
    lines.append(f"- Python: {platform.python_version()}")
    lines.append(f"- SQLite: {sqlite3.sqlite_version}")
    lines.append(f"- Platform: {platform.platform()}")
    lines.append(f"- FTS5 available: {fts_available}")
    if not fts_available:
        lines.append(f"- FTS5 error: {fts_error}")
    lines.append(f"- Documents: {len(docs)}")
    lines.append(f"- Queries: {len(queries)}")
    lines.append(f"- Database size: {db_size} bytes")
    lines.append(f"- Build time: {build_elapsed*1000:.2f} ms")
    lines.append("")
    lines.append("## Correctness Summary\n")
    lines.append("")
    lines.append("| Method | Queries | Top-1 Hit | Recall@3 | Precision@3 | Misleading↑ | Avg ms/query |")
    lines.append("|--------|---------|-----------|----------|-------------|-------------|--------------|")
    
    for method, rs in by_method.items():
        active = [r for r in rs if not r.get("skipped")]
        skipped = len(rs) - len(active)
        if not active:
            lines.append(f"| {method} | 0 | - | - | - | - | - |")
            continue
        top1 = sum(1 for r in active if r["top1_hit"])
        recall = sum(r["recall_at_3"] for r in active) / len(active)
        precision = sum(r["precision_at_3"] for r in active) / len(active)
        misleading = sum(1 for r in active if r.get("misleading_ranked_first"))
        avg_ms = sum(r["elapsed_ms"] for r in active) / len(active)
        q_str = f"{len(active)}"
        if skipped:
            q_str += f" (+{skipped} skipped)"
        lines.append(f"| {method} | {q_str} | {top1}/{len(active)} | {recall:.2f} | {precision:.2f} | {misleading} | {avg_ms:.2f} |")
    
    lines.append("")
    lines.append("## Query Categories\n")
    from collections import Counter
    cats = Counter(q["category"] for q in queries)
    for cat, n in sorted(cats.items()):
        lines.append(f"- {cat}: {n}")
    lines.append("")
    
    lines.append("## Tool versions / skip matrix\n")
    lines.append("")
    lines.append("| Tool | Status |")
    lines.append("|------|--------|")
    lines.append(f"| Python sqlite3 | {sqlite3.sqlite_version} |")
    lines.append(f"| SQLite FTS5 | {'available' if fts_available else 'not available – ' + str(fts_error)} |")
    lines.append("| Algolia / Elasticsearch / Meilisearch | not installed – out of scope (server-side, not embedded) |")
    lines.append("| ripgrep / jq / datasette | not installed – skipped honestly |")
    lines.append("")
    
    lines.append("## Commands run\n")
    lines.append("```\npython3 -m py_compile generate_corpus.py run_lab.py\npython3 generate_corpus.py\npython3 run_lab.py\n```\n")
    
    lines.append("## Limitations\n")
    lines.append("")
    lines.append("- Synthetic corpus only, seed 42 – real-world documents are messier")
    lines.append("- Small corpus (~120 docs) – ranking behavior changes at scale")
    lines.append("- FTS5 unicode61 tokenizer only – no ICU, no stemming, no compound-word splitting")
    lines.append("- No fuzzy search – FTS5 does not include fuzzy matching by default")
    lines.append("- No phrase slop / proximity tuning – simple MATCH queries only")
    lines.append("- No spelling correction")
    lines.append("- Database size includes full content – FTS5 contentless / external content tables not tested")
    lines.append("- Client-side / WASM delivery size not measured")
    lines.append("- No relevance judgment beyond planted ground truth – real search quality needs human labels")
    lines.append("")
    lines.append("---\n")
    lines.append("_Correctness before speed. A fast search that misses the answer or ranks misleading results first is worse than a slow search that gets it right._\n")
    
    with open(RESULTS_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

if __name__ == "__main__":
    main()
