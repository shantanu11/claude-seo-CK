#!/usr/bin/env python3
"""
Batch SEO analysis - analyze 50+ URLs at once.

Supports multiple analysis modes:
  page    - On-page SEO (title, meta, headings, links, schema, images)
  content - E-E-A-T / content quality (readability, author, dates, depth)
  geo     - AI citation readiness (Q&A structure, entities, citability)
  all     - All of the above combined

Usage:
    python page_batch.py --urls "url1,url2" --mode page --json
    python page_batch.py --batch urls.txt --mode content --workers 5 --json
    python page_batch.py --batch urls.txt --mode all --workers 5 --save results.json
    python page_batch.py --batch urls.txt --mode geo --json
"""

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from urllib.parse import urlparse

try:
    from fetch_page import fetch_page
    from parse_html import parse_html
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fetch_page import fetch_page
    from parse_html import parse_html

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


MAX_URLS = 500
VALID_MODES = ("page", "content", "geo", "all")


# ─── Content Analysis Helpers ────────────────────────────────────────────────

def _flesch_reading_ease(text: str) -> float:
    """Approximate Flesch Reading Ease score."""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    words = re.findall(r'\b\w+\b', text)
    if not sentences or not words:
        return 0.0
    syllables = sum(_count_syllables(w) for w in words)
    asl = len(words) / len(sentences)
    asw = syllables / len(words)
    return round(206.835 - 1.015 * asl - 84.6 * asw, 1)


def _count_syllables(word: str) -> int:
    word = word.lower().strip()
    if len(word) <= 3:
        return 1
    word = re.sub(r'(?:es|ed|e)$', '', word) or word
    vowels = re.findall(r'[aeiouy]+', word)
    return max(1, len(vowels))


def _reading_level(score: float) -> str:
    if score >= 80:
        return "Easy"
    elif score >= 60:
        return "Standard"
    elif score >= 40:
        return "Difficult"
    return "Very Difficult"


def analyze_content(html: str, url: str) -> dict:
    """E-E-A-T / content quality analysis from raw HTML."""
    result = {
        "readability_score": 0,
        "reading_level": "Unknown",
        "sentence_count": 0,
        "avg_sentence_length": 0,
        "paragraph_count": 0,
        "has_author": False,
        "author_name": None,
        "has_publish_date": False,
        "has_update_date": False,
        "has_sources": False,
        "external_citation_count": 0,
        "list_count": 0,
        "table_count": 0,
        "content_to_html_ratio": 0,
        "boilerplate_ratio": 0,
    }

    if not BeautifulSoup:
        return result

    soup = BeautifulSoup(html, "html.parser")

    # Extract main content text
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)

    # Readability
    if text:
        result["readability_score"] = _flesch_reading_ease(text)
        result["reading_level"] = _reading_level(result["readability_score"])

    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    result["sentence_count"] = len(sentences)
    words = re.findall(r'\b\w+\b', text)
    result["avg_sentence_length"] = round(len(words) / max(len(sentences), 1), 1)

    # Paragraph count
    result["paragraph_count"] = len(soup.find_all("p"))

    # Author detection
    author_patterns = [
        soup.find("meta", {"name": "author"}),
        soup.find("meta", {"property": "article:author"}),
        soup.find(class_=re.compile(r'author', re.I)),
        soup.find(rel="author"),
    ]
    for a in author_patterns:
        if a:
            result["has_author"] = True
            result["author_name"] = a.get("content") or a.get_text(strip=True) or None
            if result["author_name"]:
                result["author_name"] = result["author_name"][:100]
            break

    # Dates
    date_meta = soup.find("meta", {"property": "article:published_time"})
    if date_meta:
        result["has_publish_date"] = True
    time_tag = soup.find("time", {"datetime": True})
    if time_tag:
        result["has_publish_date"] = True

    mod_meta = soup.find("meta", {"property": "article:modified_time"})
    if mod_meta:
        result["has_update_date"] = True

    # External citations
    base_domain = urlparse(url).netloc
    ext_links = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if href.startswith("http") and urlparse(href).netloc != base_domain:
            ext_links.append(href)
    result["external_citation_count"] = len(ext_links)
    result["has_sources"] = len(ext_links) >= 2

    # Structural elements
    result["list_count"] = len(soup.find_all(["ul", "ol"]))
    result["table_count"] = len(soup.find_all("table"))

    # Content-to-HTML ratio
    html_len = len(html)
    text_len = len(text)
    result["content_to_html_ratio"] = round((text_len / max(html_len, 1)) * 100, 1)

    return result


# ─── GEO Analysis Helpers ────────────────────────────────────────────────────

def analyze_geo(html: str, seo_data: dict, url: str) -> dict:
    """AI citation readiness / GEO analysis from raw HTML + parsed SEO data."""
    result = {
        "citability_score": 0,
        "has_qa_format": False,
        "qa_pairs_count": 0,
        "has_definition_patterns": False,
        "has_answer_first": False,
        "has_stats_with_sources": False,
        "stat_claims_count": 0,
        "entity_clarity": "low",
        "has_faq_schema": False,
        "has_howto_content": False,
        "passage_count": 0,
        "citable_passages": 0,
        "has_structured_lists": False,
        "has_comparison_table": False,
    }

    if not BeautifulSoup:
        return result

    soup = BeautifulSoup(html, "html.parser")

    # Remove non-content
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)

    # Q&A pattern detection
    qa_patterns = re.findall(
        r'(?:^|\n)\s*(?:Q[:.]|What|How|Why|When|Where|Who|Can|Is|Does|Do|Should|Which)\s*.+\?',
        text, re.IGNORECASE | re.MULTILINE
    )
    result["qa_pairs_count"] = len(qa_patterns)
    result["has_qa_format"] = len(qa_patterns) >= 2

    # Definition patterns ("X is ...", "X refers to ...")
    def_patterns = re.findall(
        r'(?:^|\.\s+)[A-Z][^.]{5,60}\s+(?:is|are|refers? to|means?|defines?)\s+[^.]{10,}',
        text
    )
    result["has_definition_patterns"] = len(def_patterns) >= 1

    # Answer-first: first paragraph after H1 contains a direct statement
    h1 = soup.find("h1")
    if h1:
        next_p = h1.find_next("p")
        if next_p:
            first_text = next_p.get_text(strip=True)
            # Answer-first = first paragraph is substantive (not just "Read on..." fluff)
            if len(first_text) > 50 and not re.match(r'^(In this|Read on|Welcome|Click)', first_text):
                result["has_answer_first"] = True

    # Statistics with sources
    stat_pattern = re.findall(r'\d+(?:\.\d+)?%|\$[\d,.]+|\d{1,3}(?:,\d{3})+', text)
    result["stat_claims_count"] = len(stat_pattern)
    # Has sourced stats = has numbers + has external links nearby
    result["has_stats_with_sources"] = len(stat_pattern) >= 2 and (seo_data.get("external_links", 0) >= 2)

    # Entity clarity: does the page clearly name its subject in title + H1?
    title = seo_data.get("title") or ""
    h1_list = seo_data.get("h1") or []
    h1_text = h1_list[0] if h1_list else ""
    if title and h1_text:
        # Check overlap between title and H1
        title_words = set(title.lower().split())
        h1_words = set(h1_text.lower().split())
        overlap = len(title_words & h1_words)
        if overlap >= 2:
            result["entity_clarity"] = "high"
        elif overlap >= 1:
            result["entity_clarity"] = "medium"

    # FAQ schema
    schema_types = seo_data.get("schema_types", [])
    result["has_faq_schema"] = "FAQPage" in schema_types

    # How-to content
    how_to_headings = [
        h for h in (seo_data.get("h2", []) if isinstance(seo_data.get("h2"), list)
                     else [f"h2x{seo_data.get('h2_count', 0)}"])
        if isinstance(h, str) and re.search(r'how to|step|guide', h, re.I)
    ]
    result["has_howto_content"] = len(how_to_headings) >= 1

    # Citable passages: paragraphs between 40-200 words that make a standalone claim
    paragraphs = soup.find_all("p")
    result["passage_count"] = len(paragraphs)
    citable = 0
    for p in paragraphs:
        p_text = p.get_text(strip=True)
        word_count = len(p_text.split())
        if 30 <= word_count <= 200:
            citable += 1
    result["citable_passages"] = citable

    # Structured lists
    lists = soup.find_all(["ul", "ol"])
    result["has_structured_lists"] = len(lists) >= 2

    # Comparison tables
    tables = soup.find_all("table")
    result["has_comparison_table"] = len(tables) >= 1

    # Citability score (0-100)
    score = 0
    if result["has_answer_first"]:
        score += 15
    if result["has_qa_format"]:
        score += 15
    if result["has_definition_patterns"]:
        score += 10
    if result["has_stats_with_sources"]:
        score += 10
    if result["entity_clarity"] == "high":
        score += 15
    elif result["entity_clarity"] == "medium":
        score += 8
    if result["has_faq_schema"]:
        score += 5
    if result["citable_passages"] >= 5:
        score += 15
    elif result["citable_passages"] >= 2:
        score += 8
    if result["has_structured_lists"]:
        score += 5
    if result["has_comparison_table"]:
        score += 5
    if result["stat_claims_count"] >= 3:
        score += 5
    result["citability_score"] = min(100, score)

    return result


# ─── Unified Page Analyzer ───────────────────────────────────────────────────

def analyze_page(url: str, mode: str = "page", timeout: int = 30) -> dict:
    """
    Fetch and analyze a single page.

    Args:
        url: URL to analyze.
        mode: 'page', 'content', 'geo', or 'all'.
        timeout: Fetch timeout.
    """
    result = {
        "url": url,
        "mode": mode,
        "status_code": None,
        "error": None,
        "seo": None,
        "content": None,
        "geo": None,
        "issues": [],
        "score": None,
    }

    # Fetch
    fetched = fetch_page(url, timeout=timeout)
    if fetched.get("error"):
        result["error"] = fetched["error"]
        return result

    result["status_code"] = fetched.get("status_code")
    html = fetched.get("content", "")

    if not html:
        result["error"] = "Empty response"
        return result

    if result["status_code"] and result["status_code"] >= 400:
        result["error"] = f"HTTP {result['status_code']}"
        return result

    # Parse base SEO elements (always needed)
    seo = parse_html(html, base_url=url)
    seo_summary = {
        "title": seo.get("title"),
        "title_length": len(seo["title"]) if seo.get("title") else 0,
        "meta_description": seo.get("meta_description"),
        "meta_description_length": len(seo["meta_description"]) if seo.get("meta_description") else 0,
        "meta_robots": seo.get("meta_robots"),
        "canonical": seo.get("canonical"),
        "h1": seo.get("h1", []),
        "h1_count": len(seo.get("h1", [])),
        "h2": seo.get("h2", []),
        "h2_count": len(seo.get("h2", [])),
        "h3_count": len(seo.get("h3", [])),
        "word_count": seo.get("word_count", 0),
        "images_total": len(seo.get("images", [])),
        "images_missing_alt": sum(
            1 for img in seo.get("images", [])
            if not img.get("alt") or img["alt"].strip() == ""
        ),
        "internal_links": len(seo.get("links", {}).get("internal", [])),
        "external_links": len(seo.get("links", {}).get("external", [])),
        "schema_types": [
            s.get("@type", "unknown") for s in seo.get("schema", []) if isinstance(s, dict)
        ],
        "has_og": bool(seo.get("open_graph")),
        "has_twitter_card": bool(seo.get("twitter_card")),
        "hreflang_count": len(seo.get("hreflang", [])),
    }

    if fetched.get("redirect_chain"):
        seo_summary["redirected_to"] = fetched["url"]
        seo_summary["redirect_hops"] = len(fetched["redirect_chain"])

    result["seo"] = seo_summary

    # ── Page issues (always run) ─────────────────────────────────────────
    issues = []
    s = seo_summary

    if not s["title"]:
        issues.append({"severity": "critical", "type": "page", "issue": "Missing title tag"})
    elif s["title_length"] < 20:
        issues.append({"severity": "high", "type": "page", "issue": f"Title too short ({s['title_length']} chars)"})
    elif s["title_length"] > 60:
        issues.append({"severity": "medium", "type": "page", "issue": f"Title too long ({s['title_length']} chars)"})

    if not s["meta_description"]:
        issues.append({"severity": "high", "type": "page", "issue": "Missing meta description"})
    elif s["meta_description_length"] > 160:
        issues.append({"severity": "medium", "type": "page", "issue": f"Meta description too long ({s['meta_description_length']} chars)"})

    if s["h1_count"] == 0:
        issues.append({"severity": "critical", "type": "page", "issue": "Missing H1 tag"})
    elif s["h1_count"] > 1:
        issues.append({"severity": "medium", "type": "page", "issue": f"Multiple H1 tags ({s['h1_count']})"})

    if s["word_count"] < 100:
        issues.append({"severity": "critical", "type": "page", "issue": f"Thin content ({s['word_count']} words)"})
    elif s["word_count"] < 300:
        issues.append({"severity": "high", "type": "page", "issue": f"Low word count ({s['word_count']} words)"})

    if s["images_missing_alt"] > 0:
        issues.append({"severity": "medium", "type": "page", "issue": f"{s['images_missing_alt']} image(s) missing alt"})

    if not s["canonical"]:
        issues.append({"severity": "medium", "type": "page", "issue": "Missing canonical tag"})

    if not s["schema_types"]:
        issues.append({"severity": "low", "type": "page", "issue": "No structured data"})

    if s["internal_links"] == 0:
        issues.append({"severity": "high", "type": "page", "issue": "No internal links (orphan page)"})

    robots = s.get("meta_robots") or ""
    if "noindex" in robots.lower():
        issues.append({"severity": "critical", "type": "page", "issue": "Page is noindex"})

    # ── Content analysis ─────────────────────────────────────────────────
    if mode in ("content", "all"):
        content_data = analyze_content(html, url)
        result["content"] = content_data

        if content_data["readability_score"] < 30:
            issues.append({"severity": "high", "type": "content", "issue": f"Very poor readability ({content_data['readability_score']})"})
        elif content_data["readability_score"] < 50:
            issues.append({"severity": "medium", "type": "content", "issue": f"Difficult readability ({content_data['readability_score']})"})

        if not content_data["has_author"]:
            issues.append({"severity": "high", "type": "content", "issue": "No author attribution (E-E-A-T)"})

        if not content_data["has_publish_date"]:
            issues.append({"severity": "medium", "type": "content", "issue": "No publish date"})

        if not content_data["has_update_date"]:
            issues.append({"severity": "low", "type": "content", "issue": "No last-updated date"})

        if content_data["external_citation_count"] == 0:
            issues.append({"severity": "medium", "type": "content", "issue": "No external citations/sources"})

        if content_data["content_to_html_ratio"] < 10:
            issues.append({"severity": "high", "type": "content", "issue": f"Low content-to-HTML ratio ({content_data['content_to_html_ratio']}%)"})

        if content_data["paragraph_count"] < 3:
            issues.append({"severity": "medium", "type": "content", "issue": f"Very few paragraphs ({content_data['paragraph_count']})"})

        if content_data["avg_sentence_length"] > 30:
            issues.append({"severity": "medium", "type": "content", "issue": f"Long avg sentence length ({content_data['avg_sentence_length']} words)"})

    # ── GEO analysis ─────────────────────────────────────────────────────
    if mode in ("geo", "all"):
        geo_data = analyze_geo(html, seo_summary, url)
        result["geo"] = geo_data

        if geo_data["citability_score"] < 30:
            issues.append({"severity": "high", "type": "geo", "issue": f"Very low AI citability ({geo_data['citability_score']}/100)"})
        elif geo_data["citability_score"] < 50:
            issues.append({"severity": "medium", "type": "geo", "issue": f"Low AI citability ({geo_data['citability_score']}/100)"})

        if not geo_data["has_answer_first"]:
            issues.append({"severity": "medium", "type": "geo", "issue": "No answer-first format after H1"})

        if geo_data["entity_clarity"] == "low":
            issues.append({"severity": "high", "type": "geo", "issue": "Low entity clarity (title/H1 mismatch)"})

        if geo_data["citable_passages"] < 3:
            issues.append({"severity": "medium", "type": "geo", "issue": f"Few citable passages ({geo_data['citable_passages']})"})

        if not geo_data["has_structured_lists"]:
            issues.append({"severity": "low", "type": "geo", "issue": "No structured lists for AI parsing"})

        if geo_data["stat_claims_count"] == 0:
            issues.append({"severity": "low", "type": "geo", "issue": "No statistics/data points"})

    result["issues"] = issues

    # Score: 100 - deductions
    deductions = 0
    for i in issues:
        if i["severity"] == "critical":
            deductions += 20
        elif i["severity"] == "high":
            deductions += 10
        elif i["severity"] == "medium":
            deductions += 5
        else:
            deductions += 2
    result["score"] = max(0, 100 - deductions)

    return result


# ─── Batch Runner ────────────────────────────────────────────────────────────

def batch_analyze(
    urls: list,
    mode: str = "page",
    workers: int = 3,
    delay: float = 0.3,
    timeout: int = 30,
    save_path: Optional[str] = None,
) -> dict:
    """Batch analyze multiple URLs with concurrency and progress tracking."""
    workers = max(1, min(workers, 10))
    total = len(urls)
    start_time = time.time()

    output = {
        "total": total,
        "mode": mode,
        "workers": workers,
        "results": [],
        "summary": {
            "analyzed": 0, "errors": 0, "avg_score": 0,
            "critical_issues": 0, "high_issues": 0,
            "medium_issues": 0, "low_issues": 0,
            "pages_missing_title": 0, "pages_missing_h1": 0,
            "pages_missing_meta_desc": 0, "pages_thin_content": 0,
            "pages_noindex": 0,
        },
        "elapsed_seconds": 0,
    }

    if mode in ("content", "all"):
        output["summary"].update({
            "pages_no_author": 0, "avg_readability": 0,
            "pages_no_dates": 0, "pages_no_citations": 0,
        })
    if mode in ("geo", "all"):
        output["summary"].update({
            "avg_citability": 0, "pages_low_citability": 0,
            "pages_no_answer_first": 0, "pages_low_entity_clarity": 0,
        })

    completed = [0]
    lock = threading.Lock()

    def _progress(url, idx):
        elapsed = time.time() - start_time
        rate = idx / elapsed if elapsed > 0 else 0
        remaining = (total - idx) / rate if rate > 0 else 0
        pct = (idx / total) * 100
        print(f"  [{idx}/{total}] {pct:.0f}% | {url[:55]}... | ETA: {remaining/60:.1f}min", file=sys.stderr)

    def _save():
        if save_path:
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(output, f, indent=2, ensure_ascii=False)
            except IOError:
                pass

    ordered = [None] * total

    def _worker(idx, url):
        return idx, analyze_page(url.strip(), mode=mode, timeout=timeout)

    mode_label = {"page": "Page SEO", "content": "Content/E-E-A-T", "geo": "GEO/AI Citation", "all": "Full Analysis"}
    print(f"=== Batch {mode_label.get(mode, mode)}: {total} URLs, {workers} workers ===", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for i, url in enumerate(urls):
            url = url.strip()
            if not url:
                continue
            future = executor.submit(_worker, i, url)
            futures[future] = i
            if i < total - 1:
                time.sleep(delay)

        for future in as_completed(futures):
            idx, r = future.result()
            ordered[idx] = r
            with lock:
                completed[0] += 1
                _progress(r.get("url", ""), completed[0])
                if completed[0] % 10 == 0:
                    output["results"] = [x for x in ordered if x is not None]
                    _save()

    output["results"] = [x for x in ordered if x is not None]

    # Aggregate summary
    scores, readability_scores, citability_scores = [], [], []
    for r in output["results"]:
        if r.get("error"):
            output["summary"]["errors"] += 1
        else:
            output["summary"]["analyzed"] += 1
            if r.get("score") is not None:
                scores.append(r["score"])

        for issue in r.get("issues", []):
            sev = issue.get("severity", "")
            output["summary"][f"{sev}_issues"] = output["summary"].get(f"{sev}_issues", 0) + 1

        seo = r.get("seo") or {}
        if not seo.get("title"):
            output["summary"]["pages_missing_title"] += 1
        if seo.get("h1_count", 0) == 0:
            output["summary"]["pages_missing_h1"] += 1
        if not seo.get("meta_description"):
            output["summary"]["pages_missing_meta_desc"] += 1
        if seo.get("word_count", 0) < 100:
            output["summary"]["pages_thin_content"] += 1
        if "noindex" in (seo.get("meta_robots") or "").lower():
            output["summary"]["pages_noindex"] += 1

        # Content summary
        content = r.get("content") or {}
        if mode in ("content", "all") and content:
            if content.get("readability_score"):
                readability_scores.append(content["readability_score"])
            if not content.get("has_author"):
                output["summary"]["pages_no_author"] = output["summary"].get("pages_no_author", 0) + 1
            if not content.get("has_publish_date"):
                output["summary"]["pages_no_dates"] = output["summary"].get("pages_no_dates", 0) + 1
            if content.get("external_citation_count", 0) == 0:
                output["summary"]["pages_no_citations"] = output["summary"].get("pages_no_citations", 0) + 1

        # GEO summary
        geo = r.get("geo") or {}
        if mode in ("geo", "all") and geo:
            if geo.get("citability_score") is not None:
                citability_scores.append(geo["citability_score"])
            if geo.get("citability_score", 0) < 40:
                output["summary"]["pages_low_citability"] = output["summary"].get("pages_low_citability", 0) + 1
            if not geo.get("has_answer_first"):
                output["summary"]["pages_no_answer_first"] = output["summary"].get("pages_no_answer_first", 0) + 1
            if geo.get("entity_clarity") == "low":
                output["summary"]["pages_low_entity_clarity"] = output["summary"].get("pages_low_entity_clarity", 0) + 1

    output["summary"]["avg_score"] = round(sum(scores) / len(scores), 1) if scores else 0
    if readability_scores:
        output["summary"]["avg_readability"] = round(sum(readability_scores) / len(readability_scores), 1)
    if citability_scores:
        output["summary"]["avg_citability"] = round(sum(citability_scores) / len(citability_scores), 1)

    output["elapsed_seconds"] = round(time.time() - start_time, 1)
    _save()

    print(
        f"\n  Done: {total} URLs in {output['elapsed_seconds']}s | "
        f"Avg Score: {output['summary']['avg_score']}/100 | "
        f"Errors: {output['summary']['errors']}",
        file=sys.stderr,
    )

    return output


# ─── Output ──────────────────────────────────────────────────────────────────

def print_summary(output: dict):
    """Print human-readable summary."""
    s = output.get("summary", {})
    mode = output.get("mode", "page")
    mode_label = {"page": "Page SEO", "content": "Content/E-E-A-T", "geo": "GEO/AI Citation", "all": "Full"}

    print(f"=== Batch {mode_label.get(mode, mode)} Results ===")
    print(f"Total: {output.get('total', 0)} | Analyzed: {s.get('analyzed', 0)} | Errors: {s.get('errors', 0)}")
    print(f"Average Score: {s.get('avg_score', 0)}/100 | Time: {output.get('elapsed_seconds', 0)}s")
    print()

    print(f"Issues: {s.get('critical_issues', 0)} critical, {s.get('high_issues', 0)} high, "
          f"{s.get('medium_issues', 0)} medium, {s.get('low_issues', 0)} low")
    print(f"Missing: title={s.get('pages_missing_title',0)} | H1={s.get('pages_missing_h1',0)} | "
          f"meta desc={s.get('pages_missing_meta_desc',0)} | thin={s.get('pages_thin_content',0)} | noindex={s.get('pages_noindex',0)}")

    if mode in ("content", "all"):
        print(f"Content: avg readability={s.get('avg_readability',0)} | "
              f"no author={s.get('pages_no_author',0)} | no dates={s.get('pages_no_dates',0)} | "
              f"no citations={s.get('pages_no_citations',0)}")

    if mode in ("geo", "all"):
        print(f"GEO: avg citability={s.get('avg_citability',0)}/100 | "
              f"low citability={s.get('pages_low_citability',0)} | "
              f"no answer-first={s.get('pages_no_answer_first',0)} | "
              f"low entity clarity={s.get('pages_low_entity_clarity',0)}")
    print()

    # Header based on mode
    if mode == "geo":
        print(f"{'Score':>5}  {'Cite':>5}  {'Words':>6}  {'Issues':>6}  URL")
        print(f"{'─'*5}  {'─'*5}  {'─'*6}  {'─'*6}  {'─'*50}")
    elif mode == "content":
        print(f"{'Score':>5}  {'Read':>5}  {'Words':>6}  {'Issues':>6}  URL")
        print(f"{'─'*5}  {'─'*5}  {'─'*6}  {'─'*6}  {'─'*50}")
    elif mode == "all":
        print(f"{'Score':>5}  {'Read':>5}  {'Cite':>5}  {'Words':>6}  {'Issues':>6}  URL")
        print(f"{'─'*5}  {'─'*5}  {'─'*5}  {'─'*6}  {'─'*6}  {'─'*50}")
    else:
        print(f"{'Score':>5}  {'Status':>6}  {'Words':>6}  {'Issues':>6}  URL")
        print(f"{'─'*5}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*50}")

    results = output.get("results", [])
    sorted_results = sorted(results, key=lambda r: r.get("score") or 0)

    for r in sorted_results:
        score = r.get("score")
        score_str = f"{score:>5}" if score is not None else "  ERR"
        wc = (r.get("seo") or {}).get("word_count", 0)
        n_issues = len(r.get("issues", []))
        url = r.get("url", "")[:60]

        if mode == "geo":
            cite = (r.get("geo") or {}).get("citability_score", 0)
            print(f"{score_str}  {cite:>5}  {wc:>6}  {n_issues:>6}  {url}")
        elif mode == "content":
            read = (r.get("content") or {}).get("readability_score", 0)
            print(f"{score_str}  {read:>5.0f}  {wc:>6}  {n_issues:>6}  {url}")
        elif mode == "all":
            read = (r.get("content") or {}).get("readability_score", 0)
            cite = (r.get("geo") or {}).get("citability_score", 0)
            print(f"{score_str}  {read:>5.0f}  {cite:>5}  {wc:>6}  {n_issues:>6}  {url}")
        else:
            status = r.get("status_code") or "---"
            print(f"{score_str}  {status:>6}  {wc:>6}  {n_issues:>6}  {url}")

    # Worst pages
    worst = [r for r in sorted_results if (r.get("score") or 0) < 60][:10]
    if worst:
        print(f"\n--- Worst Pages (score < 60) ---")
        for r in worst:
            print(f"\n  {r.get('url', '')}")
            print(f"  Score: {r.get('score', '?')}/100")
            for issue in r.get("issues", []):
                sev = issue["severity"].upper()
                itype = issue.get("type", "page").upper()
                print(f"    [{sev}:{itype}] {issue['issue']}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch SEO analysis (page/content/geo) - analyze 50+ URLs at once"
    )
    parser.add_argument("--urls", "-u", help="Comma-separated list of URLs")
    parser.add_argument("--batch", "-b", help="File with URLs (one per line)")
    parser.add_argument(
        "--mode", "-m",
        choices=VALID_MODES, default="page",
        help="Analysis mode: page (on-page SEO), content (E-E-A-T), geo (AI citation), all (default: page)",
    )
    parser.add_argument("--workers", "-w", type=int, default=3, help="Concurrent workers (default: 3, max: 10)")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between dispatches (default: 0.3s)")
    parser.add_argument("--timeout", type=int, default=30, help="Per-page timeout (default: 30s)")
    parser.add_argument("--save", "-s", help="Save results to JSON file incrementally")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    urls = []
    if args.batch:
        try:
            with open(args.batch, "r") as f:
                urls = [line.strip() for line in f if line.strip() and line.strip().startswith("http")]
        except IOError as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.urls:
        for part in args.urls.replace(",", "\n").split("\n"):
            part = part.strip()
            if part and part.startswith("http"):
                urls.append(part)
    else:
        parser.print_help()
        sys.exit(1)

    if not urls:
        print("Error: No valid URLs found.", file=sys.stderr)
        sys.exit(1)

    if len(urls) > MAX_URLS:
        print(f"Warning: Capping at {MAX_URLS} URLs (got {len(urls)})", file=sys.stderr)
        urls = urls[:MAX_URLS]

    # Auto-generate save path if not specified
    save_path = args.save
    if not save_path:
        # Derive from first URL's domain
        first_url = urls[0]
        domain = urlparse(first_url).netloc.replace("www.", "").replace(":", "_").replace("/", "_")
        timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        save_path = f"seo-batch-{domain}-{args.mode}-{timestamp}.json"

    output = batch_analyze(
        urls, mode=args.mode, workers=args.workers,
        delay=args.delay, timeout=args.timeout, save_path=save_path,
    )

    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print_summary(output)

    # Always print the saved file and report command
    print(f"\n  Results saved to: {save_path}", file=sys.stderr)
    print(f"  Generate DOCX report: /seo report --input {save_path} --format docx", file=sys.stderr)
    print(f"  Generate PDF report:  /seo report --input {save_path} --format pdf", file=sys.stderr)


if __name__ == "__main__":
    main()
