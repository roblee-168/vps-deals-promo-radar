# VPS deals shortlist article — 2026-10-02

## Topic and source use

- Main theme: `vps deals`; US monthly search volume 90 was supplied by the user in the current cycle. No new search-volume estimate was made.
- Page: `https://perkmingle.com/vps-deals-shortlist/` — “VPS Deals: Turn a Plan List into a Workload Shortlist.”
- The user-provided competitor-intelligence result was archived verbatim in `C:\Users\Administrator\Desktop\roster.md`. The article's framing uses the submitted observation that one candidate directory presented a table-first experience: this page adds a workload-fit decision record after discovery. The directory's supplied DR, visit estimates, ranking claims, and causal explanation are not repeated or treated as verified facts.
- The results for “谷歌搜索查词 vps deals” and “老外怎么说 vps deals” were not included in the user's pasted material. The roster records this gap rather than inventing output.

## Official evidence

Each provider statement is scoped to its own product documentation. Pages were opened and checked on 2026-10-02.

| Claim used | Official source |
|---|---|
| DigitalOcean describes shared-CPU and dedicated-CPU Droplet allocation differently; its shared vCPU may be shared, while dedicated CPU gets guaranteed access to a full hyperthread. | https://docs.digitalocean.com/products/droplets/concepts/choosing-a-plan/ |
| Vultr's documentation says inbound transfer is not metered toward bandwidth limits and bandwidth usage is based on outbound transfer. | https://docs.vultr.com/support/platform/billing/how-is-bandwidth-usage-calculated |
| Vultr says server resources continue accruing hourly charges while stopped and billing ends when the server is destroyed. | https://docs.vultr.com/support/platform/billing/how-am-i-billed-for-my-servers |

No price, coupon, expiry, stock, performance measurement, or universal host behavior was added.

## Original-analysis accounting

- Rendered article body: 1,136 words.
- `#shortlist-method` section: 494 words.
- Calculation: 494 ÷ 1,136 × 100 = 43.49%.
- Counting method: visible article text tokenized with `[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?`; markup, navigation, footer, and JSON-LD are excluded.
- This is an editorial accounting ratio for the article's own method section. It is not proof that no other search result contains similar advice, and no whole-SERP exclusivity claim is made.

## Build and generated metadata

- Source template: `templates/vps-deals-shortlist.html`.
- Generator: `build.py`; generates one canonical at `/vps-deals-shortlist/`, an FAQPage and BreadcrumbList graph, homepage-library link, and sitemap entry with `lastmod` 2026-10-02.
- Mobile preview: no horizontal overflow at 390 px or 320 px; the evidence and worksheet tables collapse into the existing mobile table treatment.
- Verification: `python -m unittest discover -s tests` passed (13 tests); `python build.py` completed and generated 57 indexable pages; `git diff --check` passed.
- Published commit `35fd891` to `main`; Cloudflare page returned HTTP 200. Live browser readback confirmed the title, article, official links, and exactly one canonical pointing at the new URL.
- Live 390 px viewport: document client width and scroll width both 375 CSS px. Live 320 px viewport: both 305 CSS px. No horizontal overflow at either tested viewport.
- The locally generated sitemap contains one matching URL with `lastmod` 2026-10-02 and was pushed in the same commit. Live sitemap readback is unconfirmed: browser navigation returned `ERR_BLOCKED_BY_CLIENT` and direct HTTP fetch returned 403.

## Prepared for the next shift

- Question: Does an HTTP 200 response from a VPS listing prove that a named plan is in stock or can be ordered?
- Source prompt: the user-provided CheapVPSList observation says its homepage returned HTTP 200. Treat that only as the seed for the question; do not infer plan inventory or availability from the response status.
- Sources to verify before publishing: IETF HTTP semantics for the meaning of 200, then the exact vendor listing or order state for any named offer.
- This is a distinct availability-evidence question, not a second workload-fit worksheet.
