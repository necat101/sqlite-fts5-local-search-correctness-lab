#!/usr/bin/env python3
"""
generate_corpus.py – SQLite FTS5 search corpus generator

Deterministic local document corpus + query set with planted ground truth.
Seed: 42
"""
import json
import pathlib
import random

SEED = 42
random.seed(SEED)

CORPUS_PATH = pathlib.Path(__file__).parent / "corpus" / "corpus.json"
QUERIES_PATH = pathlib.Path(__file__).parent / "corpus" / "queries.json"

# Generate 120 documents
docs = []

def add_doc(doc_id, title, tags, body, category="blog"):
    docs.append({
        "id": doc_id,
        "title": title,
        "tags": tags,
        "body": body,
        "category": category,
    })

# Plant specific documents for ground-truth queries
# Q1: exact rare term
add_doc(1, "PostgreSQL WAL Archiving Guide", ["postgres", "database", "wal"],
    "Write-Ahead Log archiving in PostgreSQL requires careful configuration of archive_command. "
    "The wal_shipping_tool automates this process. Rare term: walrusmode42 appears only here.")

# Q2: phrase query
add_doc(2, "Rate Limiting in the Login Flow", ["auth", "security"],
    "Enforcing login rate limiting prevents brute force attacks. "
    "The token bucket algorithm is commonly used. "
    "Plant: 'login rate limiting enforced' phrase appears verbatim here.")

# Q3: natural language-ish
add_doc(3, "Refreshing Expired JWT Tokens", ["auth", "jwt"],
    "When a JWT access token expires, the client must use the refresh token to obtain a new access token. "
    "The refresh_expired_tokens function handles this. Plant: expired_tokens_refresh_99")

# Q4: title/tag query
add_doc(4, "UserSessionStore Implementation", ["python", "session"],
    "The UserSessionStore class manages user sessions in Redis. "
    "It provides get_session and set_session methods.")

# code-ish docs
add_doc(5, "API Client: login endpoint", ["api", "typescript"],
    "ApiClient.login() sends POST /api/auth/login with username and password. "
    "Returns a JWT token on success.")

add_doc(6, "Go Backend: loginHandler", ["api", "go"],
    "func loginHandler(w http.ResponseWriter, r *http.Request) validates credentials "
    "and issues a JWT. Related to POST /api/auth/login.")

# version number query
add_doc(7, "Release Notes v2.14.3", ["release"],
    "Version 2.14.3 fixes a critical bug in the query planner. "
    "Upgrade recommended. Plant version string: v2.14.3_build_881")

# punctuation query
add_doc(8, "Regex Patterns for Email Validation", ["regex"],
    "Common email pattern: user@example.com. Also handles user+tag@example.co.uk. "
    "Plant punctuation term: email-validator_v3.2.1")

# unicode / accent
add_doc(9, "Internationalization Guide", ["i18n", "unicode"],
    "Handle café, naïve, résumé, and other accented words correctly. "
    "Plant: café_naïve_résumé_token_77")

# emoji
add_doc(10, "Emoji in Commit Messages", ["git", "fun"],
    "Using emoji in commits: 🚀 deploy, 🐛 bugfix, ✨ feature. "
    "Plant: commit_emoji_rocket_88")

# non-English caveat (German compound)
add_doc(11, "German Compound Words and Search", ["search", "i18n", "de"],
    "German compound words like Raketenangriff (missile strike), "
    "Oberflächenangriff, Luftangriff cause tokenization problems. "
    "FTS5 with default tokenizer won't match 'angriff' inside 'Raketenangriff'. "
    "Plant: Raketenangriff_Kyiv_55")

# misleading near-match – wrong doc with many repeated terms
add_doc(12, "Login Page CSS Styling", ["css", "frontend"],
    "Login login login login login. Styling the login form with CSS. "
    "The login button, login input, login label. "
    "This document mentions 'login' many times but is NOT about rate limiting. "
    "No auth logic here, just CSS.")

# correct doc for login rate limiting (should rank above doc 12)
add_doc(13, "Auth Rate Limiting Deep Dive", ["auth", "security"],
    "Login rate limiting enforced via token bucket in the AuthMiddleware. "
    "Prevents brute force. The enforce_login_rate_limiting function is key. "
    "Plant: login_rate_limiting_enforced_exact")

# near-duplicate
add_doc(14, "User Session Store (Duplicate)", ["python", "session"],
    "The UserSessionStore class manages user sessions in Redis. "
    "Provides get_session and set_session. (Near-duplicate of doc 4)")

# version strings
add_doc(15, "Python Version Compatibility", ["python"],
    "Tested with Python 3.11.5, 3.12.3, and 3.13.0rc1. "
    "Plant: python_version_3_12_3_exact")

# hyphenated words
add_doc(16, "Full-Text Search Performance", ["search", "performance"],
    "Full-text search with SQLite FTS5. "
    "State-of-the-art BM25 ranking. Well-known trade-offs. "
    "Plant: full-text-search-hyphenated_66")

# code snippet
add_doc(17, "SQLite FTS5 Query Example", ["sqlite", "sql"],
    "SELECT * FROM docs WHERE docs MATCH 'rate NEAR/5 limiting'; "
    "Use bm25(docs) for ranking. Plant: fts5_match_bm25_demo_123")

# long document
add_doc(18, "Comprehensive Database Indexing Guide", ["database", "performance"],
    ("Database indexing improves query performance significantly. " * 20) +
    " B-tree indexes, covering indexes, partial indexes. "
    "Plant rare term buried deep: deep_index_token_xyz_999 " +
    ("More text about indexes and query planning. " * 20))

# negative query – nothing about "quantum"
# (no doc contains "quantum" – used for negative test)

# Fill out to ~120 docs with varied content
templates = [
    ("Blog: {topic} Best Practices", ["blog"], "Best practices for {topic}. Covers common pitfalls and recommended approaches. "),
    ("Docs: {topic} API Reference", ["docs", "api"], "API reference for {topic}. Parameters, return values, examples. "),
    ("Note: {topic} quick note", ["note"], "Quick note about {topic}. "),
    ("Code: {topic} snippet", ["code"], "Code snippet: function {func}() {{ /* {topic} */ }} "),
]
topics = [
    "caching", "logging", "testing", "deployment", "monitoring", "debugging",
    "authentication", "authorization", "database", "indexing", "query_optimization",
    "full_text_search", "tokenization", "ranking", "bm25", "inverted_index",
    "sqlite", "postgres", "redis", "nginx", "docker", "kubernetes",
    "react", "typescript", "python", "golang", "rust",
    "ci_cd", "git", "github_actions", "terraform",
]
doc_id = 19
for topic in topics:
    for title_tmpl, tags, body_tmpl in templates:
        if doc_id > 120:
            break
        title = title_tmpl.format(topic=topic.replace("_", " ").title(), func=topic)
        body = body_tmpl.format(topic=topic, func=topic) * random.randint(2, 5)
        # sprinkle in some terms that could be misleading near-matches
        if random.random() < 0.15:
            body += " login auth token session rate limit. "
        add_doc(doc_id, title, tags + [topic], body, "generated")
        doc_id += 1
    if doc_id > 120:
        break

# Ensure we have at least 120 docs
while len(docs) < 120:
    add_doc(doc_id, f"Generated Doc {doc_id}", ["generated"],
            f"Filler document {doc_id} about various topics. " * 5, "generated")
    doc_id += 1

print(f"Generated {len(docs)} documents")
print(f"ID range: {min(d['id'] for d in docs)} .. {max(d['id'] for d in docs)}")

# Build queries with ground truth
queries = [
    {
        "id": "q_exact_rare",
        "text": "walrusmode42",
        "category": "exact_rare",
        "expected_docs": [1],
        "expected_top": 1,
        "planted_term": "walrusmode42",
        "description": "Exact rare term – should find doc 1",
    },
    {
        "id": "q_phrase",
        "text": "\"login rate limiting enforced\"",
        "category": "phrase",
        "expected_docs": [13, 2],
        "expected_top": 13,
        "planted_term": "login rate limiting enforced",
        "description": "Phrase query – doc 13 is best match",
    },
    {
        "id": "q_natural_language",
        "text": "refresh expired tokens",
        "category": "natural_language",
        "expected_docs": [3],
        "expected_top": 3,
        "planted_term": "expired_tokens_refresh_99",
        "description": "Natural-language-ish query",
    },
    {
        "id": "q_exact_symbol",
        "text": "UserSessionStore",
        "category": "exact_symbol",
        "expected_docs": [4, 14],
        "expected_top": 4,
        "planted_term": "UserSessionStore",
        "description": "Exact symbol – docs 4 and 14, 4 is original",
    },
    {
        "id": "q_api_path",
        "text": "POST /api/auth/login",
        "category": "api_path",
        "expected_docs": [5, 6],
        "expected_top": 5,
        "planted_term": "POST /api/auth/login",
        "description": "API path query",
    },
    {
        "id": "q_version",
        "text": "v2.14.3_build_881",
        "category": "version",
        "expected_docs": [7],
        "expected_top": 7,
        "planted_term": "v2.14.3_build_881",
        "description": "Version number query",
    },
    {
        "id": "q_punctuation",
        "text": "email-validator_v3.2.1",
        "category": "punctuation",
        "expected_docs": [8],
        "expected_top": 8,
        "planted_term": "email-validator_v3.2.1",
        "description": "Punctuation-heavy term",
    },
    {
        "id": "q_unicode_accent",
        "text": "café naïve résumé",
        "category": "unicode",
        "expected_docs": [9],
        "expected_top": 9,
        "planted_term": "café_naïve_résumé_token_77",
        "description": "Unicode/accent query",
    },
    {
        "id": "q_emoji",
        "text": "🚀",
        "category": "unicode",
        "expected_docs": [10],
        "expected_top": 10,
        "planted_term": "commit_emoji_rocket_88",
        "description": "Emoji query",
    },
    {
        "id": "q_german_compound",
        "text": "angriff",
        "category": "non_english_caveat",
        "expected_docs": [11],
        "expected_top": 11,
        "planted_term": "Raketenangriff_Kyiv_55",
        "description": "German compound – 'angriff' inside 'Raketenangriff', FTS5 default tokenizer likely WON'T match (caveat)",
        "note": "FTS5 unicode61 tokenizer does NOT do compound splitting – this is expected to FAIL, documenting the HN discussed limitation",
        "expect_fts_fail": True,
    },
    {
        "id": "q_misleading_near_match",
        "text": "login rate limiting",
        "category": "noisy_near_match",
        "expected_docs": [13, 2],
        "expected_top": 13,
        "planted_term": "login_rate_limiting_enforced_exact",
        "description": "Misleading near-match: doc 12 mentions 'login' many times but is about CSS, NOT rate limiting. Correct answer is doc 13.",
        "misleading_doc": 12,
        "description2": "Ranker must NOT prefer doc 12 just because 'login' repeats",
    },
    {
        "id": "q_ranking_matters",
        "text": "login",
        "category": "ranking",
        "expected_docs": [13, 2, 5, 6, 12],
        "expected_top": 13,
        "description": "Ranking matters – doc 12 has many 'login' repeats but is CSS, doc 13 is actually about auth rate limiting",
        "misleading_doc": 12,
    },
    {
        "id": "q_hyphenated",
        "text": "full-text search",
        "category": "punctuation",
        "expected_docs": [16],
        "expected_top": 16,
        "planted_term": "full-text-search-hyphenated_66",
        "description": "Hyphenated words",
    },
    {
        "id": "q_code_snippet",
        "text": "fts5_match_bm25_demo_123",
        "category": "code",
        "expected_docs": [17],
        "expected_top": 17,
        "planted_term": "fts5_match_bm25_demo_123",
        "description": "Code-ish / FTS5 query syntax term",
    },
    {
        "id": "q_deep_token",
        "text": "deep_index_token_xyz_999",
        "category": "rare_exact",
        "expected_docs": [18],
        "expected_top": 18,
        "planted_term": "deep_index_token_xyz_999",
        "description": "Rare token buried deep in long document",
    },
    {
        "id": "q_python_version",
        "text": "python_version_3_12_3_exact",
        "category": "version",
        "expected_docs": [15],
        "expected_top": 15,
        "planted_term": "python_version_3_12_3_exact",
        "description": "Version string with underscores",
    },
    # Negative queries – should return nothing
    {
        "id": "q_negative_quantum",
        "text": "quantum_entanglement_cryptography_zzz",
        "category": "negative",
        "expected_docs": [],
        "expected_top": None,
        "description": "Negative – term does not exist in corpus, should return no results",
        "expect_no_results": True,
    },
    {
        "id": "q_negative_xyzzy",
        "text": "xyzzy_plugh_frotz_nonexistent",
        "category": "negative",
        "expected_docs": [],
        "expected_top": None,
        "description": "Negative – nonsense terms, no results expected",
        "expect_no_results": True,
    },
    # More natural queries hitting generated docs
    {
        "id": "q_caching",
        "text": "caching",
        "category": "natural_language",
        "expected_docs": [],  # will be filled by scanning
        "description": "Natural query: caching",
        "auto_ground_truth": "caching",
    },
    {
        "id": "q_sqlite",
        "text": "sqlite",
        "category": "exact_symbol",
        "expected_docs": [],
        "description": "Symbol query: sqlite",
        "auto_ground_truth": "sqlite",
    },
    {
        "id": "q_bm25",
        "text": "bm25",
        "category": "exact_symbol",
        "expected_docs": [],
        "description": "Symbol query: bm25",
        "auto_ground_truth": "bm25",
    },
]

# Auto-fill ground truth for auto_ground_truth queries
for q in queries:
    if "auto_ground_truth" in q:
        term = q["auto_ground_truth"].lower()
        matching = []
        for doc in docs:
            haystack = (doc["title"] + " " + " ".join(doc["tags"]) + " " + doc["body"]).lower()
            if term in haystack:
                matching.append(doc["id"])
        q["expected_docs"] = matching[:10]  # top 10
        q["expected_top"] = matching[0] if matching else None
        del q["auto_ground_truth"]

# Save
corpus_dir = CORPUS_PATH.parent
corpus_dir.mkdir(parents=True, exist_ok=True)

with open(CORPUS_PATH, "w", encoding="utf-8") as f:
    json.dump(docs, f, indent=2, ensure_ascii=False)

with open(QUERIES_PATH, "w", encoding="utf-8") as f:
    json.dump(queries, f, indent=2, ensure_ascii=False)

print(f"Corpus: {len(docs)} documents -> {CORPUS_PATH}")
print(f"Queries: {len(queries)} queries -> {QUERIES_PATH}")
print()
print("Query breakdown:")
from collections import Counter
cats = Counter(q["category"] for q in queries)
for cat, n in sorted(cats.items()):
    print(f"  {cat:20s} {n}")
