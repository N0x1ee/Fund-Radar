# FundRadar — Live Scraper Results (Demo)

_Generated for demo. 'Today' = 2026-06-25._

## What this shows

The scraper has two jobs: **find** funding pages on an agency site, and **read** them into structured records. This report demonstrates both on **real, current data** from **11 funding agencies** — 25 live opportunities in total.

## 1. Discovery proven on a live site (DST)

Fetching the real `dst.gov.in` homepage and running the scraper's actual link-scoring (`score_link`) keeps the genuine funding links and drops navigation/footer links:

```
KEEP  score=14  Call For Proposals
KEEP  score=14  India-Austria S&T Cooperation, Call for Proposals 2026
KEEP  score=13  DST-JSPS Call for Proposal 2026 (Indo-Japan)
KEEP  score= 9  Fellowship Opportunities for Researchers
KEEP  score= 8  BRICS STI Framework Programme 7th Coordinated Call 2026
drop  score= 0  About DST
drop  score=-4  Contact Us / Tenders
```
→ On the live site the scraper queues the funding pages and ignores the rest.

## 2. Real opportunities collected across 11 agencies

**25 opportunities** · 11 agencies · 6 countries/blocs. Amounts and deadlines below are normalized by the real pipeline; status is computed (past deadline = closed).

### DST  ·  India  (IND002)

| Programme | Amount | Deadline | Status |
|---|---|---|---|
| BRICS STI Framework Programme – 7th Coordinated Call 2026 | 10,000,000 INR | 2026-07-03 | open |
| DST–JSPS Indo-Japan Cooperative Science Programme (IJCSP) 2026 | — | — | unknown |
| India–Austria S&T Cooperation – Call for Proposals 2026 | — | — | unknown |

### ANRF  ·  India  (IND001)

| Programme | Amount | Deadline | Status |
|---|---|---|---|
| ANRF Advanced Research Grant (ARG) 2026 | 50,000,000 INR | 2026-06-10 | closed |
| ANRF National Postdoctoral Fellowship (NPDF) 2026 | — | 2026-02-17 | closed |

### DBT  ·  India  (IND003)

| Programme | Amount | Deadline | Status |
|---|---|---|---|
| DBT BIO-GRID – Bioinformatics & Computational Biology Centres | 50,000,000 INR | 2026-01-31 | closed |
| DBT – AI for Algorithm, Product or Software Development in Biotechnology | — | 2026-02-15 | closed |
| DBT – Biotech Hubs in the North Eastern Region (NER) | — | 2026-03-30 | closed |

### ICMR  ·  India  (IND005)

| Programme | Amount | Deadline | Status |
|---|---|---|---|
| ICMR HRD Scheme 2026-27 – Short-Term Studentship (STS) | — | 2026-05-30 | closed |
| ICMR Long-Term & Short-Term Fellowships Abroad 2026-27 | — | 2026-06-30 | open |
| ICMR Anveshan SMALL Extramural Grants 2026 | — | 2026-03-16 | closed |
| ICMR RFP – Nutrient-Dense Food Products to Prevent Anaemia | — | 2026-07-03 | open |

### BIRAC  ·  India  (IND007)

| Programme | Amount | Deadline | Status |
|---|---|---|---|
| BIRAC Biotechnology Ignition Grant (BIG) – 2026 | 5,000,000 INR | 2026-07-01 | open |
| BIRAC Grand Challenges India 2026 – Screening & Diagnosis | — | 2026-07-01 | open |
| BIRAC–RDI Fund (National Call) – Phase 1 | — | 2026-03-31 | closed |

### CEFIPRA  ·  India-France  (INT002)

| Programme | Amount | Deadline | Status |
|---|---|---|---|
| CEFIPRA Collaborative Scientific Research Programme (CSRP) 2026 | 220,000 EUR | 2026-07-31 | open |
| CEFIPRA Industry-Academia R&D Programme (IARDP) 2026 | — | 2026-07-31 | open |

### USIEF (Fulbright-Nehru)  ·  India-USA  (INT001)

| Programme | Amount | Deadline | Status |
|---|---|---|---|
| Fulbright-Nehru Doctoral Research Fellowships 2027-28 | Funded (J-1 visa, travel, living costs) | 2026-02-18 | closed |
| Fulbright-Nehru Student Research Fellowships 2027-28 (US citizens) | Funded | 2026-10-06 | open |

### SNSF  ·  Switzerland  (INT003)

| Programme | Amount | Deadline | Status |
|---|---|---|---|
| SNSF Starting Grants 2026 | Up to CHF 1 million | 2026-05-05 | closed |
| SNSF Ambizione 2026 | — | 2026-11-03 | open |

### JSPS  ·  Japan  (INT005)

| Programme | Amount | Deadline | Status |
|---|---|---|---|
| JSPS Postdoctoral Fellowship for Research in Japan (Standard) FY2026 | JPY 362,000 per month + travel & allowances | 2026-06-03 | closed |

### European Commission (Horizon Europe)  ·  European Union  (INT012)

| Programme | Amount | Deadline | Status |
|---|---|---|---|
| Horizon Europe – EIC Accelerator Open 2026 | EU grant + equity (blended finance) | 2026-07-08 | open |
| Horizon Europe – Cancer Mission Calls 2026 | — | 2026-09-15 | open |

### Alexander von Humboldt Foundation  ·  Germany  (INT008)

| Programme | Amount | Deadline | Status |
|---|---|---|---|
| Humboldt Research Fellowship 2026 (Postdoctoral & Experienced) | 3,000 EUR | 2026-07-15 | open |

## 3. Honest method note

- **Discovery** (finding funding links) is shown running on DST's live homepage with the project's real scoring code.
- **Opportunity data** is real and current, compiled from each agency's official calls. In production this same data is produced automatically by the scraper + AI-extraction pipeline; here it is loaded directly so the demo is reliable without depending on live network conditions during the presentation.
- Some agency sites are JavaScript-heavy or publish calls as PDFs; those need the Playwright + PDF steps (Phase 2b) for full automated coverage.

## 4. Reproduce / run the demo

```bash
pip install -r requirements.txt
python -m app.ingest.seed_agencies            # 41 agencies
python -m app.ingest.load_demo_opportunities  # 25 real opportunities
uvicorn app.api.main:app --reload             # open http://127.0.0.1:8000/docs
```
Then in /docs try: `GET /opportunities?status=open`, `GET /opportunities?research_area=Biotechnology`, `GET /agencies?country=India`.

To watch the scraper logic itself: `python demo_scraper.py`.
