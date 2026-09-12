# Performance & Speed Improvements

The scraper currently runs **one Chrome browser**, page by page, then detail by detail. That is reliable, but slow for large jobs (hundreds or thousands of listings).

This document lists **practical options** to speed things up. Pick one (or combine a few) for the next implementation phase.

---

## Why it feels slow today

| Bottleneck | What happens now |
|------------|------------------|
| Single browser | Only one page loads at a time |
| Sequential details | Each business page waits for the previous one |
| Heavy page work | Scroll gallery, reviews, full HTML parse per detail |
| Image downloads | Optional local gallery saves add network time |
| Polite delays | `request_delay` between requests reduces blocks but costs time |
| Undetected Chrome | Safer against bots, but heavier than plain HTTP |

---

## Suggested approaches (decide next)

### 1. Multi-Chrome workers (your idea) — **recommended first**

Open **N Chrome instances** (e.g. 3–5) and scrape in parallel.

**How it could work**

1. One “manager” discovers listing URLs (or assigns listing **pages**).
2. A shared queue holds pending detail URLs (`progress.json` already tracks these).
3. Each Chrome worker pulls the next URL, scrapes the detail, writes results, marks progress.
4. Optional: also split **listing pages** — worker 1 does pages 1–20, worker 2 does 21–40, etc.

**Pros**

- Large real-world speedup (often ~3–5× with 3–5 browsers)
- Still uses undetected Chrome (same anti-bot path)
- Fits the existing resume model (URL queue)

**Cons**

- More RAM/CPU (each Chrome is heavy)
- Higher chance of rate-limits / CAPTCHAs if N is too high
- Need thread-safe or process-safe writes to CSV/JSON/progress

**Suggested defaults:** start with **3 workers**, headless on, delay 1–2s per worker. Tune from there.

---

### 2. Page-wise parallel listing discovery

Instead of walking page 1 → 2 → 3:

- Launch workers that each fetch a different `?page=` URL at the same time
- Merge all detail URLs into the shared pending queue
- Then run detail workers (same as option 1)

**Best when:** total list pages is large (hundreds+).

---

### 3. Multiprocessing vs multithreading

| Model | Good for | Notes |
|-------|----------|--------|
| **Threading** | I/O wait (page loads) | Simpler GUI integration; Chrome drivers often work better as separate processes |
| **Multiprocessing** | Isolating Chrome crashes | Safer: one dead browser does not kill all workers |
| **Hybrid** | Production | Process pool of Chrome workers + thread for GUI/status updates |

**Recommendation:** prefer **multiprocessing (or separate processes)** for Chrome workers; use threads only for GUI callbacks and light I/O (image downloads).

---

### 4. Async / concurrent image downloads

Keep detail scraping as-is (or parallel as above), but download gallery images **concurrently**:

- After each detail (or in a background pool), fetch many images at once with `asyncio` / thread pool
- Or: scrape first (URLs only), download images in a second pass

**Pros:** big win when “Store gallery images locally” is enabled  
**Cons:** does not speed up HTML scraping itself

---

### 5. Two-phase scrape (fast list → deep detail)

**Phase A (fast):** listing pages only → name, phone, URL, address  
**Phase B (optional/deep):** detail pages for reviews, gallery, hours

**Pros:** usable CSV much sooner; deep scrape only for selected rows  
**Cons:** two pipelines to maintain

---

### 6. Lighter page mode (speed profile)

Add a GUI/CLI “**Fast mode**” that skips expensive steps:

- Skip gallery carousel scrolling
- Skip review scrolling
- Disable image downloads
- Shorter waits / fewer retries

**Pros:** easy, low risk, immediate speedup  
**Cons:** less complete records

---

### 7. HTTP / API path for some data (advanced)

If listing cards already contain enough fields, parse listing HTML without opening every detail.

Or explore whether Yellow Pages exposes JSON XHR endpoints the browser already calls — reuse those carefully.

**Pros:** can be much faster than full page loads  
**Cons:** more brittle; higher detection risk; may break site TOS — evaluate carefully

---

### 8. Smarter queue & batching

- Batch CSV/JSON flushes (write every N records, not every 1)
- Skip re-parsing already-scraped URLs (already partly done via `progress.json`)
- Prioritize failed retries in a separate low-concurrency queue
- Shard output by worker (`businesses_worker1.csv`) then merge

**Pros:** less disk lock contention under parallelism  
**Cons:** small gain alone; best combined with multi-Chrome

---

### 9. Proxy / identity rotation (scale, not raw CPU)

When increasing workers, Yellow Pages may throttle one IP.

- Rotating residential proxies
- Separate browser profiles per worker
- Adaptive delay: slow down when errors/CAPTCHAs rise

**Pros:** needed for large parallel runs  
**Cons:** cost/complexity; not a substitute for good architecture

---

### 10. Async orchestration layer

Use `asyncio` + process pool:

- Async manager schedules pages/details
- Blocking Selenium work runs in `ProcessPoolExecutor`
- GUI receives progress via a queue

**Pros:** clean architecture for high throughput  
**Cons:** more engineering effort than a simple worker pool

---

## Rough speed expectations

Assuming ~20 listings per page and detail pages as the main cost:

| Setup | Relative speed | Notes |
|-------|----------------|-------|
| Current (1 Chrome) | 1× | Baseline |
| Fast mode (skip gallery/reviews/images) | ~1.5–3× | Easiest win |
| 3 Chrome detail workers | ~2.5–4× | Best balance for most PCs |
| 5 Chrome detail workers | ~3–5× | Needs strong CPU/RAM; watch bans |
| List parallel + 5 detail workers + fast mode | highest | Highest complexity |

Actual numbers depend on network, site throttling, and PC specs.

---

## Recommended roadmap

1. **Now / easy:** add **Fast mode** + make image download async/pooled.  
2. **Next (your idea):** **multi-Chrome worker pool** (3 workers) on the pending URL queue.  
3. **Then:** page-wise parallel listing discovery.  
4. **Later:** proxies + adaptive rate limiting for large runs.  
5. **Optional:** two-phase scrape for “quick CSV first.”

---

## Implementation notes (when we build it)

- Keep **one shared `progress.json`** (file lock or SQLite) so resume still works.
- Each worker should have its **own Chrome profile/user-data-dir**.
- Prefer **append-only per-worker files**, then merge — avoids corrupt CSV/JSON.
- Expose in GUI: `Worker count (1–5)`, `Fast mode`, `Parallel listing pages`.
- Cap workers by default: `min(5, cpu_count - 1)`.

---

## Decision checklist

Choose what you want next:

- [ ] Multi-Chrome detail workers (3–5 instances)
- [ ] Page-wise multi-process listing crawl
- [ ] Fast mode (skip heavy sections)
- [ ] Async / pooled gallery image downloads
- [ ] Two-phase scrape (list first, details later)
- [ ] Batch writes + worker-local output files
- [ ] Proxies / adaptive delays for scale

Once you pick an option (or a short list), we can implement it in the scraper and GUI.
