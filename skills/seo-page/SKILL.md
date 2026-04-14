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

This skill handles both single and multiple URLs:

- **1 URL** → deep inline analysis (original seo-page behavior)
- **2+ URLs** (comma-separated, space-separated, or file) → automatic batch mode via `scripts/page_batch.py`

**How to detect:** Count URLs in the arguments. If there are commas, spaces between `http` strings, or a `--batch` flag, route to batch mode.

### Single URL
```
/seo page https://example.com/blog/post
```
Runs the full inline analysis below (detailed scorecard, recommendations, schema suggestions).

### Multiple URLs
```
/seo page https://example.com/blog/post1, https://example.com/blog/post2, https://example.com/blog/post3
/seo page --batch urls.txt
/seo page --batch urls.txt --mode all --workers 5
```
Runs `python scripts/page_batch.py --urls "url1,url2,..." --mode all` automatically.
Default mode for multi-URL is `all` (page + content + geo).

### Mode Options (multi-URL only)
- `--mode page` -- on-page SEO only (title, meta, headings, links, schema)
- `--mode content` -- + E-E-A-T (readability, author, dates, citations)
- `--mode geo` -- + AI citation readiness (citability, Q&A, answer-first)
- `--mode all` -- everything combined (default for multi-URL)

## What to Analyze

### On-Page SEO
- Title tag: 50-60 characters, includes primary keyword, unique
- Meta description: 150-160 characters, compelling, includes keyword
- H1: exactly one, matches page intent, includes keyword
- H2-H6: logical hierarchy (no skipped levels), descriptive
- URL: short, descriptive, hyphenated, no parameters
- Internal links: sufficient, relevant anchor text, no orphan pages
- External links: to authoritative sources, reasonable count

### Content Quality
- Word count vs page type minimums (see quality-gates.md)
- Readability: Flesch Reading Ease score, grade level
- Keyword density: natural (1-3%), semantic variations present
- E-E-A-T signals: author bio, credentials, first-hand experience markers
- Content freshness: publication date, last updated date

### Technical Elements
- Canonical tag: present, self-referencing or correct
- Meta robots: index/follow unless intentionally blocked
- Open Graph: og:title, og:description, og:image, og:url
- Twitter Card: twitter:card, twitter:title, twitter:description
- Hreflang: if multi-language, correct implementation

### Schema Markup
- Detect all types (JSON-LD preferred)
- Validate required properties
- Identify missing opportunities
- NEVER recommend HowTo (deprecated) or FAQ (restricted to gov/health)

### Images
- Alt text: present, descriptive, includes keywords where natural
- File size: flag >200KB (warning), >500KB (critical)
- Format: recommend WebP/AVIF over JPEG/PNG
- Dimensions: width/height set for CLS prevention
- Lazy loading: loading="lazy" on below-fold images

### Core Web Vitals (reference only, not measurable from HTML alone)
- Flag potential LCP issues (huge hero images, render-blocking resources)
- Flag potential INP issues (heavy JS, no async/defer)
- Flag potential CLS issues (missing image dimensions, injected content)

## Output

### Page Score Card
```
Overall Score: XX/100

On-Page SEO:     XX/100  ████████░░
Content Quality: XX/100  ██████████
Technical:       XX/100  ███████░░░
Schema:          XX/100  █████░░░░░
Images:          XX/100  ████████░░
```

### Issues Found
Organized by priority: Critical -> High -> Medium -> Low

### Recommendations
Specific, actionable improvements with expected impact

### Schema Suggestions
Ready-to-use JSON-LD code for detected opportunities

## DataForSEO Integration (Optional)

If DataForSEO MCP tools are available, use `serp_organic_live_advanced` for real SERP positions and `backlinks_summary` for backlink data and spam scores.

## Error Handling

| Scenario | Action |
|----------|--------|
| URL unreachable (DNS failure, connection refused) | Report the error clearly. Do not guess page content. Suggest the user verify the URL and try again. |
| Page requires authentication (401/403) | Report that the page is behind authentication. Suggest the user provide the rendered HTML directly or a publicly accessible URL. |
| JavaScript-rendered content (empty body in HTML) | Note that key content may be rendered client-side. Analyze the available HTML and flag that results may be incomplete. Suggest using a browser-rendered snapshot if available. |
