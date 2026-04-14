---
name: seo-page
description: >
  Page SEO analysis -- handles single URL or multiple URLs automatically.
  Covers on-page elements, content quality (E-E-A-T), AI citation readiness (GEO),
  technical meta tags, schema, images, and performance.
  Use when user says "analyze this page", "check page SEO", "page analysis",
  or provides one or more URLs. Supports --mode page|content|geo|all.
user-invokable: true
argument-hint: "<url(s)> [--mode page|content|geo|all]"
license: MIT
metadata:
  author: shantanu11
  version: "1.9.0"
  category: seo
---

# Page Analysis

## Auto-Detection

- **1 URL** -> deep inline analysis (comprehensive report below)
- **2+ URLs** (comma-separated, space-separated, or --batch file) -> automatic batch mode via `scripts/page_batch.py` with --mode all

### Multiple URLs
```
/seo page url1, url2, url3
/seo page --batch urls.txt --mode all --workers 5
```
Runs `python scripts/page_batch.py --urls "..." --mode all` automatically.

---

## MANDATORY Report Structure (Single URL)

Every single-page analysis MUST produce ALL sections below. Verify everything from live HTML source -- do NOT guess.

### 1. Page Header

```
PAGE SEO ANALYSIS
{full URL}
Analyzed: {date}
Page Type: {blog post / product / landing page / homepage / about / etc.}
Platform: {detected from HTML -- Shopify, WordPress, custom, etc.}
HTTP Status: {200 / 301 / etc.}
```

### 2. Page Score Card

| Category | Score | Status |
|----------|-------|--------|
| On-Page SEO | XX/100 | Good / Needs Work / FAILING |
| Content Quality | XX/100 | ... |
| Technical Elements | XX/100 | ... |
| Schema & Structured Data | XX/100 | ... |
| Images | XX/100 | ... |
| AI Citation Readiness (GEO) | XX/100 | ... |
| **Overall** | **XX/100** | |

### 3. On-Page SEO Details

Show exact values found in HTML:

| Element | Found | Assessment |
|---------|-------|------------|
| Title | "{exact title}" ({X} chars) | PASS / Too long / Too short / Missing |
| Meta Description | "{first 80 chars}..." ({X} chars) | PASS / Too long / Missing |
| H1 | "{exact H1 text}" | PASS / Missing / Multiple ({count}) |
| H2 Count | {X} headings | List all H2s |
| H3 Count | {X} headings | |
| URL Structure | {URL path} | Clean / Has parameters / Too long |
| Canonical | {canonical URL} | Self-ref / Mismatch / Missing |
| Meta Robots | {value or "Not set"} | PASS / noindex detected |
| Internal Links | {count} | Good / Low / Orphan page |
| External Links | {count} | Good / None |
| Word Count | {count} words | PASS / Thin / Borderline |

### 4. Content Quality & E-E-A-T

| Signal | Found | Assessment |
|--------|-------|------------|
| Readability (Flesch) | {score} ({level}) | Good / Difficult / Very Difficult |
| Avg Sentence Length | {X} words | OK / Too long (>25) |
| Paragraphs | {count} | Sufficient / Too few |
| Author | {name or "Not found"} | Present with bio / Name only / Missing |
| Author Credentials | {LinkedIn/bio link or "None"} | PASS / Missing |
| Publish Date | {date or "Not found"} | Present / Missing |
| Last Updated | {date or "Not found"} | Present / Missing |
| External Citations | {count} links to authoritative sources | Good / None |
| Lists & Tables | {X} lists, {X} tables | Structured / Lacks structure |
| Content-to-HTML Ratio | {X}% | Good (>15%) / Low / Very Low |

### 5. Schema Markup Audit

List every JSON-LD block found with validation:

| Schema Type | Status | Issues |
|-------------|--------|--------|
| {type found} | Valid / Has errors | {specific field issues} |

If schema is missing, recommend which types to add with ready-to-use JSON-LD code.

NEVER recommend HowTo (deprecated) or FAQ for commercial sites.

### 6. Image Audit

| Metric | Value | Assessment |
|--------|-------|------------|
| Total Images | {count} | |
| Missing Alt Text | {count} ({percentage}%) | PASS / FAIL |
| Images Without Dimensions | {count} | CLS risk |
| Lazy Loaded | {count} of {total} | Good / Missing |
| Format | {WebP/JPEG/PNG breakdown} | Modern / Needs conversion |

If images are missing alt text, list the first 5 with their src:
| Image | Current Alt | Suggested Alt |
|-------|------------|---------------|
| {src or filename} | {empty/generic} | {descriptive suggestion} |

### 7. Technical Meta Tags

| Tag | Found | Assessment |
|-----|-------|------------|
| og:title | {value or "Missing"} | PASS / Missing |
| og:description | {value or "Missing"} | PASS / Missing |
| og:image | {URL or "Missing"} | PASS / Missing |
| og:url | {URL or "Missing"} | PASS / Missing |
| twitter:card | {value or "Missing"} | PASS / Missing |
| twitter:title | {value or "Missing"} | PASS / Missing |
| Hreflang | {count} tags or "None" | PASS / Missing (if multi-lang) |

### 8. Performance Signals (from HTML)

| Signal | Found | Impact |
|--------|-------|--------|
| Preload Tags | {count} | LCP impact |
| Render-Blocking Scripts | {list scripts in <head> without async/defer} | LCP / INP risk |
| Third-Party Scripts | {count} ({list domains}) | Performance overhead |
| Font Loading | {strategy: preload/swap/blocking} | CLS / LCP impact |
| Hero Image | {loading strategy: eager/lazy/preloaded} | LCP impact |

### 9. AI Citation Readiness (GEO)

| Signal | Found | Assessment |
|--------|-------|------------|
| Citability Score | {X}/100 | Good / Low / Very Low |
| Answer-First Format | {Yes/No} | Direct answer in first 60 words after H1? |
| Q&A Headings | {count} question-format headings | Good / Missing |
| Definition Patterns | {Yes/No} | "X is..." patterns found? |
| Citable Passages | {count} of {total paragraphs} (30-200 words each) | Good / Few |
| Statistics with Sources | {count} data points | Good / None |
| Entity Clarity | {High/Medium/Low} | Title/H1 alignment |
| Structured Lists | {count} | Good / Missing |
| Comparison Tables | {count} | Good / Missing |

### 10. Issues with Evidence

Group by severity. Every issue MUST include all fields:

**[SEVERITY:CATEGORY] Issue title**
- **Found:** Exact value from live HTML
- **Expected:** Standard or best practice
- **How to fix:** Platform-specific instruction with file/location to edit
- **Time:** Estimated fix time
- **Verify:** Exact URL to check

### 11. Recommendations

Prioritized list of specific, actionable improvements:

| # | Recommendation | Priority | Time | Impact |
|---|---------------|----------|------|--------|
| 1 | {specific fix} | Critical/High/Medium/Low | X min | {expected improvement} |

### 12. Schema Suggestions

If missing schema opportunities detected, provide **ready-to-use JSON-LD code** the team can copy-paste. Include:
- Article/BlogPosting for blog pages
- Product for product pages
- BreadcrumbList if missing
- Person for author (if author detected)
- Organization if not already present

---

## Multi-URL Mode

For 2+ URLs, runs `scripts/page_batch.py` which produces:
- Summary table (score, readability, citability, words per URL)
- Per-URL detailed analysis (SEO, content, GEO data + issues with evidence)
- Auto-saves JSON with domain-based filename
- Prints exact report command for DOCX generation

---

## DataForSEO Integration (Optional)

If DataForSEO MCP tools are available, use `serp_organic_live_advanced` for real SERP positions and `backlinks_summary` for backlink data.

## Error Handling

| Scenario | Action |
|----------|--------|
| URL unreachable | Report the error clearly. Do not guess page content. |
| Page requires auth (401/403) | Analyze visible portion only. Note limitation. |
| JS-rendered content (empty body) | Flag as potentially incomplete. Suggest browser snapshot. |
