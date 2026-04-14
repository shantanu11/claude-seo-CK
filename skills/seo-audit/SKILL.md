---
name: seo-audit
description: "Full website SEO audit with parallel subagent delegation. Crawls up to 500 pages, detects business type, delegates to 10 specialists (7 core + 3 conditional), generates health score. Use when user says audit, full SEO check, analyze my site, or website health check."
user-invokable: true
argument-hint: "[url]"
license: MIT
metadata:
  author: shantanu11
  version: "1.9.0"
  category: seo
---

# Full Website SEO Audit

## Process

1. **Fetch homepage**: use `scripts/fetch_page.py` to retrieve HTML
2. **Detect business type**: analyze homepage signals per seo orchestrator
3. **Crawl site**: follow internal links up to 500 pages, respect robots.txt
4. **Inspect deeply**: read actual HTML source, JSON-LD blocks, robots.txt, sitemap.xml, HTTP headers, third-party scripts. Do NOT guess -- verify from live data.
5. **Delegate to subagents** (if available, otherwise run inline sequentially):
   - `seo-technical` -- robots.txt, sitemaps, canonicals, Core Web Vitals, security headers
   - `seo-content` -- E-E-A-T, readability, thin content, AI citation readiness
   - `seo-schema` -- detection, validation, generation recommendations
   - `seo-sitemap` -- structure analysis, quality gates, missing pages
   - `seo-performance` -- LCP, INP, CLS measurements
   - `seo-visual` -- screenshots, mobile testing, above-fold analysis
   - `seo-geo` -- AI crawler access, llms.txt, citability, brand mention signals
   - `seo-local` -- GBP signals, NAP consistency, reviews, local schema (spawn when local business detected)
   - `seo-maps` -- Geo-grid rank tracking, GBP audit, reviews, competitors (spawn when local + DataForSEO available)
   - `seo-google` -- CWV field data (CrUX), URL indexation (GSC), organic traffic (GA4) (spawn when Google API credentials detected)
   - `seo-backlinks` -- Backlink profile data (spawn when Moz/Bing API keys detected)
6. **Score** -- aggregate into SEO Health Score (0-100)
7. **Report** -- generate comprehensive report in the MANDATORY format below

## Crawl Configuration

```
Max pages: 500
Respect robots.txt: Yes
Follow redirects: Yes (max 3 hops)
Timeout per page: 30 seconds
Concurrent requests: 5
Delay between requests: 1 second
```

## Scoring Weights

| Category | Weight |
|----------|--------|
| Technical SEO | 22% |
| Content Quality | 23% |
| On-Page SEO | 20% |
| Schema / Structured Data | 10% |
| Performance (CWV) | 10% |
| AI Search Readiness | 10% |
| Images | 5% |

---

## MANDATORY Report Structure

Every audit MUST produce a report with ALL sections below. No section may be skipped.

### 1. Header Block

```
SEO AUDIT REPORT
{domain}
Audit Date: {date}
Platform: {detected platform + theme if applicable}
Business Type: {detected type}
Target Market: {inferred from content}
Location: {from Organization schema or contact page, if found}
Verification: All findings verified against live site data (HTML source, JSON-LD, robots.txt, sitemap.xml)
```

### 2. SEO Health Score Table

Show ALL 7 categories with individual scores, weights, weighted contribution, status, and priority:

| Category | Weight | Score | Weighted | Status | Priority |
|----------|--------|-------|----------|--------|----------|
| Technical SEO | 22% | XX | XX.X | Good/Needs Work/FAILING | ... |
| Content Quality | 23% | XX | XX.X | ... | ... |
| On-Page SEO | 20% | XX | XX.X | ... | ... |
| Schema / Structured Data | 10% | XX | XX.X | ... | ... |
| Performance (CWV) | 10% | XX | XX.X | ... | ... |
| AI Search Readiness | 10% | XX | XX.X | ... | ... |
| Images | 5% | XX | XX.X | ... | ... |
| **TOTAL** | **100%** | | **XX.X** | | |

### 3. Executive Summary

2-3 paragraphs covering:
- What's already strong (be specific -- name the schemas found, the content patterns working)
- What the critical gaps are (be specific -- name the exact schema fields wrong, the exact scripts blocking)
- Target score achievable in 30 days with fixes

### 4. What's Working Well (Preserve These)

Table format showing every positive finding that should NOT be changed during fixes:

| Element | Status | Details |
|---------|--------|---------|
| ... | PASS | Specific evidence of what's correct |

### 5. Issues -- Grouped by Priority

Each issue MUST include ALL fields below. Number issues sequentially (1, 2, 3...) across the entire report.

#### Critical Issues (Fix Immediately)

```
{number}. {Descriptive Title}
Category: {category} | Impact: {specific measurable impact}

{2-3 sentence explanation of what's wrong and why it matters. Include exact values found in live HTML/JSON-LD.}

{If applicable: table of specific data (e.g., script sizes, wrong field values, affected URLs)}

Recommended Fixes:
- {Specific fix instruction with exact file/location to edit}
- {Another fix step}

Expected impact: {Quantified improvement estimate}
Sample URL: {exact URL where this issue can be verified}
```

#### High Priority Issues (Fix Within 1 Week)

Same format as Critical.

#### Medium Priority Issues (Fix Within 2 Weeks)

Same format as Critical.

#### Low Priority Issues (Backlog)

Can use compact table format:
| # | Issue | Category | Action | Sample URL |
|---|-------|----------|--------|------------|

### 6. Performance Estimates Table

| Metric | Current Est. | Google Threshold | Status |
|--------|-------------|-----------------|--------|
| LCP (75th pctl) | X.Xs | <=2.5s Good / >4.0s Poor | ... |
| INP | Xms | <=200ms Good / >500ms Poor | ... |
| CLS | X.XX | <=0.1 Good / >0.25 Poor | ... |
| Third-party JS | ~XXXKB | -- | ... |
| Preload tags | X | At least 1 (hero image) | ... |

### 7. Content Quality Summary

| Page | Words | Min. | Schema Present | E-E-A-T | Verdict |
|------|-------|------|---------------|---------|---------|
| Homepage | ~X | 500 | {list schemas} | ... | PASS/FAIL |
| {key pages} | ... | ... | ... | ... | ... |

### 8. Sitemap & Crawlability Summary

| Aspect | Status | Details |
|--------|--------|---------|
| robots.txt | PASS/FAIL | ... |
| Sitemap index | PASS/FAIL | {count} child sitemaps |
| AI crawler directives | PASS/MISSING | List which crawlers allowed/blocked |
| lastmod in sitemap | PASS/MISSING | ... |

### 9. 30-Day Implementation Roadmap

Break into 4 phases with numbered tasks, fix references, time estimates, and impact:

**Days 1-3 -- Critical + Quick Wins (Est. X-X hours)**
| # | Task | Fix Ref | Time | Impact |
|---|------|---------|------|--------|

**Days 4-10 -- High Priority (Est. X-X hours)**
| # | Task | Fix Ref | Time | Impact |
|---|------|---------|------|--------|

**Days 11-20 -- Medium Priority (Est. X-X hours)**
| # | Task | Fix Ref | Time | Impact |
|---|------|---------|------|--------|

**Days 21-30 -- Growth & Polish (Est. X-X hours)**
| # | Task | Fix Ref | Time | Impact |
|---|------|---------|------|--------|

**Score Projection:** Current: XX/100 -> Day 10: XX/100 -> Day 30: XX/100

### 10. Footer

```
This report was generated using Claude SEO audit methodology. All findings were
verified against live site HTML source, JSON-LD markup, robots.txt, and sitemap.xml
as of {date}.
```

---

## Issue Evidence Rules

1. **Always verify from live HTML** -- do NOT assume. Read the actual `<script type="application/ld+json">` blocks, actual `<meta>` tags, actual HTTP headers.
2. **Quote exact values** -- if Organization schema has addressLocality wrong, show what it says vs what it should say.
3. **Include sample URLs** -- every issue must have at least one URL where the team can see and verify the problem.
4. **Platform-specific fixes** -- if it's Shopify, say which Liquid file to edit. If WordPress, say which hook/plugin. Don't give generic advice.
5. **Time estimates** -- every fix should have an estimated time (5 min, 30 min, 2 hrs, etc.)
6. **Impact estimates** -- quantify where possible (e.g., "LCP -1.5s", "CLS -0.08", "enables star ratings in SERPs").

---

## Output Files

- `FULL-AUDIT-REPORT.md`: Comprehensive findings in the format above
- `ACTION-PLAN.md`: The 30-day roadmap section extracted as standalone
- Always offer DOCX: "Download as DOCX: `/seo report --input FULL-AUDIT-REPORT.md --format docx`"

## DataForSEO Integration (Optional)

If DataForSEO MCP tools are available, spawn the `seo-dataforseo` agent alongside existing subagents to enrich the audit with live data: real SERP positions, backlink profiles with spam scores, on-page analysis (Lighthouse), business listings, and AI visibility checks (ChatGPT scraper, LLM mentions).

## Google API Integration (Optional)

If Google API credentials are configured (`python scripts/google_auth.py --check`), spawn the `seo-google` agent to enrich the audit with real Google field data: CrUX Core Web Vitals (replaces lab-only estimates), GSC URL indexation status, search performance (clicks, impressions, CTR), and GA4 organic traffic trends.

## Error Handling

| Scenario | Action |
|----------|--------|
| URL unreachable | Report the error clearly. Do not guess site content. |
| robots.txt blocks crawling | Report which paths are blocked. Analyze only accessible pages. |
| Rate limiting (429) | Back off and reduce concurrent requests. Report partial results. |
| Timeout on large sites (500+ pages) | Cap crawl. Report findings for pages crawled. |
