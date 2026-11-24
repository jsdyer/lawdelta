# Law Delta

A static reading room for dated captures of four British Columbia privacy laws. It compares section and schedule text across captures from the official BC Laws CiviX XML API. Runs at `https://coolcode.ca/lawdelta/`; all browser filtering and comparison stays local.

<!-- coolcode:guide -->
Search the wider BC legislation title catalogue and full text across the four privacy laws in the selected capture. Historical versions and legislative change tables are labelled separately. Open a section to inspect its recorded text and compare captures. Observation dates are distinct from effective dates; catalogue title matches do not add change history for other laws.
<!-- /coolcode:guide -->

## Exact watchlist

| Document | CiviX document ID | Source XML |
| --- | --- | --- |
| Freedom of Information and Protection of Privacy Act | `96165_00_multi` | [Complete XML](https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/96165_00_multi/xml) |
| Personal Information Protection Act | `03063_01` | [Complete XML](https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/03063_01/xml) |
| Freedom of Information and Protection of Privacy Regulation | `155_2012` | [Complete XML](https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/155_2012/xml) |
| Personal Information Protection Act Regulations | `473_2003` | [Complete XML](https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/473_2003/xml) |

The initial real capture has **207 sections and schedules**. This is a complete-text watchlist of these four documents, not coverage of all BC law. The full FOIPPA document uses the API's documented `_multi` identifier; its unsuffixed `96165_00/xml` resource is an HTML table of contents and is rejected by the parser.

## Collection permission and source policy

[Official API overview](https://www.bclaws.gov.bc.ca/civix/template/complete/api/index.html) explicitly offers REST/XML retrieval for third-party applications under the [King's Printer Licence](https://www.bclaws.gov.bc.ca/standards/Licence.html). [Document API documentation](https://www.bclaws.gov.bc.ca/civix/template/complete/api/API_document.html) specifies `/xml` and full multi-document access.

The site's `robots.txt` observed on 2026-11-22 disallows generic crawlers (`User-agent: *; Disallow: /`) while allowing named search engines. This application uses the expressly offered, documented REST API for four fixed full-text resources and a paginated document-title catalogue; it never crawls HTML, follows discovered links, impersonates search engines, rotates IPs or bypasses blocks. The full-text collector spaces requests by two seconds. The title collector starts at most one request per second with at most four in flight, and caches completed pages for the day to resume transient failures. Both stop on denied responses. No API key is needed.

## Dates and comparison model

`captured_at` is our observation time. Per-source `retrieved_at`, HTTP Last-Modified/ETag when supplied, exact XML hash and original source URL are preserved. A missing source date is shown as missing.

Printed section numbers identify sections; schedule titles identify whole schedules. Generated XML IDs are evidence only and do not determine matching. Inline text is retained, whitespace normalized and block boundaries preserved. Section heading or text changes are visible; formatting-only whitespace is ignored. Schedules, including tables, are compared as entire units. The raw XML retains source comments and notices. Textual normalization is a reading aid and can omit visual layout, so consult the source for forms or complex tables.

Initial captures produce `baseline`, never additions. Later captures distinguish additions, removals, text changes and unchanged units. The browser lets readers choose any two retained captures in chronological order, search both versions, view changed lines and export section CSV. Observation intervals are not legal commencement dates.

Regulation `amend/@effective`, `regnum`, `added` and `bullId` fields are copied verbatim into a separate document-level annotation list. They are not assigned to section changes. The current Personal Information Protection Act Regulations XML includes a future `2027-08-01` annotation; it is explicitly labelled as future relative to the capture. Royal assent, deposition and original effective-date fields are kept separately. No commencement date is inferred where XML does not supply one. This is not a historical point-in-time reconstruction or legal advice.

## Reproducible data and deployment

- Schedule: **08:27 UTC Mondays**, `27 8 * * 1`, in `.github/workflows/pages.yml`.
- `python3 scripts/collect.py` fetches four XML resources, rejects HTML/DTD/entity documents, validates expected titles and nonempty unique numbered units, and saves only after all four parse successfully.
- Exact sources live under `data/raw/<sha256>.xml`; dated, immutable normalized captures are in `data/history/`. `data/manifest.json` verifies all raw and normalized hashes on every build. New captures never overwrite old captures.
- `data/index.json` is a small hub summary of coverage, unit count, capture timestamp, baseline/change status and latest path.
- Normal builds are offline. A scheduled/manual refresh must pass Node/Python/browser checks before its data is committed and the same build is deployed. If a source or validation fails, the prior deployment remains available.

```sh
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
```

CI performs Playwright checks at a Pages project subpath, including real baseline text, four-document navigation, search, change filters, annotations, CSV, safe literal input, desktop/mobile layout and screenshots. App/runtime dependencies: Python standard library and browser JavaScript only. Playwright is test-only. Do not commit `dist/` or add a `CNAME`.

## Privacy and related tools

Filters and CSV export run in tab memory. No pasted legal text is uploaded; the browser reads only static data files. A shared CoolCode counter records aggregate opens without search strings. [ATIP Records Explorer](https://coolcode.ca/atip/) provides a related path into access-to-information records.

## Required attribution

These materials contain information that has been derived from information originally made available by the Province of British Columbia at: http://www.bclaws.gov.bc.ca and this information is being used in accordance with the King's Printer Licence – British Columbia available at: https://www.bclaws.gov.bc.ca/standards/Licence.html. They have not, however, been produced in affiliation with, or with the endorsement of, the Province of British Columbia and THESE MATERIALS ARE NOT AN OFFICIAL VERSION.

Software: MIT. Legislative data: King's Printer Licence – British Columbia (v1.1), not the Open Government Licence. The mandatory attribution also appears prominently in the app. No provincial logo or endorsement is claimed.


## Added browser workflow

Search the wider BC legislation title catalogue and full text across the four privacy laws in the selected capture. Historical versions and legislative change tables are labelled separately. Open a section to inspect its recorded text and compare captures. Observation dates are distinct from effective dates; catalogue title matches do not add change history for other laws.

The weekly workflow refreshes the four immutable full-text captures and a separate static title catalogue through the documented CiviX search API. Catalogue metadata is replaced atomically only after complete pagination and validation. Identical documents indexed under different source parents are merged with all parent IDs retained; repeated or conflicting records fail validation. Source hit counts and merged alias counts are preserved. Browser searches never call BC Laws. The catalogue is not a full historical text archive.

<!-- schedule-reliability -->
## Schedule reliability

Public GitHub repositories can have scheduled workflows disabled after 60 days of inactivity. A separate weekly [schedule guard](.github/workflows/schedule-guard.yml) calls GitHub's enable-workflow API for an explicit list of refresh workflows and itself. It can restore workflows disabled for inactivity, preserves manually disabled workflows, and runs independently of collection failures.

This is an interim mitigation, not a scheduling guarantee: GitHub does not document active-workflow renewal as a permanent exemption, and scheduled runs can be delayed or dropped. A scheduler on our own Linux server is the planned independent trigger. The guard does not collect data, create dummy commits, or change source/check timestamps; successful collection and published data freshness still need monitoring.
<!-- /schedule-reliability -->
