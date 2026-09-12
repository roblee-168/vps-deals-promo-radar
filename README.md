# vps-deals

Official VPS promotions and trials, with the source always one click away.

Deployment status: **not yet deployed**. Planned Pages project: `vps-deals-promo-radar`. Replace this paragraph with the verified live URL only after deployment succeeds.

## What runs

Python 3.12 standard library only. No model calls, paid inference, pip packages or manually supplied API keys. GitHub Actions uses its built-in short-lived `GITHUB_TOKEN` to push generated results; Cloudflare uses its GitHub integration. Thus zero *user-managed* runtime keys, not literally zero authentication.

```sh
python scraper.py
python -m unittest discover -s tests
python sync_workflow.py --check
python build.py
python -m http.server 8000 --directory site
```

Defaults: brand `vps-deals`, niche VPS hosting, locale `en-US`. Seeds: Hostinger, IONOS, Akamai. Only official public sources. Unavailable sources remain visible as coverage gaps; no invented offers, prices or expiry dates. The initial implementation extracts promotional page headings, not a complete per-plan price catalogue. Price extraction requires a matching named structured Offer.

## I-Lang is executable configuration

`.ilang/site.ilang` is the only source for the brand, origin, provider list, URLs, affiliate destinations, field list, request limits, freshness threshold, render modes and update interval. The parser accepts a deliberately small documented subset: `::STATE` comma-separated key/value pairs, `::MODULE` sections, pipe-separated provider rows, and runtime `key: value` entries. It does not execute prose rules; code and tests implement the stated boundaries. This is not a claim of conformance with an external I-Lang specification.

Change a provider in `PROVIDERS` and run scraper/build: its pages change. Removing a provider also removes old generated pages. After changing the six-hour schedule, run `python sync_workflow.py` and commit `.github/workflows/update.yml`; GitHub must receive a literal cron expression before execution. CI rejects schedule drift. `en-US` is the only v1 locale; translations need localized sources and templates, not relabelled English data.

## Deploy to Cloudflare Pages

1. Create the public GitHub repository `vps-deals-promo-radar`; push this directory to `main`.
2. Cloudflare dashboard → Workers & Pages → Create application → Pages → Connect to Git. Grant access only to this repository.
3. Select branch `main`, framework None, build command `python build.py`, output directory `site`, Python version `3.12`.
4. Set the actual assigned Pages origin in `.ilang/site.ilang` before production verification, then build and commit. Never treat the planned slug as a verified URL.
5. Run the Actions workflow manually; verify the resulting commit triggers a successful Pages deployment. Scheduled pushes use GitHub's built-in token; verify this integration end to end in the actual account.
6. Open `/`, `/compare/`, a provider and an offer page. Run a URL test at https://search.google.com/test/rich-results and inspect the JSON-LD. The project has local data-safety tests, not a completed Google test until recorded below.

No analytics account or email subscriptions are created automatically. Actions warnings identify partial failures; all-source failure marks the workflow failed after committing an honest empty site.

## Data and freshness

`data/offers.json` contains source URLs, actual fetch timestamps and source failures. robots.txt denial, TLS errors and HTTP failures stop that source. Robots errors fail closed; a 404/410 robots response permits access. Requests are bounded, redirects are checked again and private IP destinations are refused. Sources changing markup need human maintenance.

Each build drops expired and older-than-24-hour data. If Actions or Pages stops entirely, an already published static page can still age: displayed timestamps are the authority, not a promise of perpetual freshness. Public scheduled workflows can be disabled after 60 days without repository activity and schedules may be delayed. Check periodically.

Credits, trials, refund guarantees and purchase prices are different. Unspecified fields are absent from JSON-LD. An Offer without price is not necessarily eligible for Google product rich results. No fabricated reviews, stock status or Product markup just to pass a test. Services with comparable actual prices can use AggregateOffer; lists use ItemList and interior pages use BreadcrumbList. No FAQ section is rendered, so no FAQPage is emitted. Sitemap modification dates use actual source fetch times where applicable; never invent source dates for static policy pages.

## Monetization and ownership

Affiliate links are initially empty. Apply only after the site is live, using each vendor's current official program and terms. Record approval date, allowed markets, permitted promotion methods and current program URL before adding an approved destination to the provider row. The builder labels affiliate destinations `rel="sponsored noopener"` and discloses compensation on the offer page. No commissions, recurring earnings or approvals are assumed. No cookie injection, brand bidding, self-referrals or manufactured traffic. X/Facebook automation is intentionally deferred in v1.

An owned domain makes the brand portable and easier to transfer with the repository and verifiable revenue history. Domain registration costs money and is optional. Age alone does not guarantee search authority or income; GitHub commits are not a ranking strategy. On migration, update the configured origin, bind the domain in Pages, add redirects and update Search Console. Do not purchase a domain automatically.

Official references: [GitHub Actions billing](https://docs.github.com/en/actions/concepts/billing-and-usage), [scheduled workflow inactivity](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows), [Pages limits](https://developers.cloudflare.com/pages/platform/limits/), [Pages Git integration](https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/), [Google product snippets](https://developers.google.com/search/docs/appearance/structured-data/product-snippet). Free quotas and program terms can change.

## Verification record

Local tests, build results and deployment blockers are recorded in `VERIFICATION.md`. Production URLs must only be recorded after successful HTTP and browser verification.

站点规则用 I-Lang 协议描述，见 .ilang/site.ilang；协议说明 ilang.ai。
