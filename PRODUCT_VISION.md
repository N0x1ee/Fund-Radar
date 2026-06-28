# FundRadar — Product Vision & Specification

_The foundational definition of what FundRadar is, who it serves, and where it's going._

## 1. Vision

To become **India's most complete, always-current, and personalized home for
funding opportunities** — the first place any researcher, student, startup, or
institution checks. Instead of hunting across hundreds of scattered, ever-changing
websites, a user asks in plain language and instantly sees the opportunities they
are eligible for, with reminders before the deadlines close.

## 2. Mission / Task

Build an automated platform that **collects** funding opportunities from every
relevant source, **monitors** them for changes, uses **AI to standardise** messy
web content into clean records, and **serves** them through personalized search, a
dashboard, and a chatbot — kept fresh automatically with minimal human effort.

## 3. Target users (serving all four)

- **Researchers & faculty** — grants, fellowships; need research-area and
  eligibility matching and deadline alerts.
- **Students** — scholarships, studentships, PhD fellowships; need eligibility by
  level and simple reminders.
- **Startups & innovators** — innovation grants, incubation, seed funding; need
  sector, stage, and amount filters.
- **Institutions / universities** — research offices tracking opportunities for
  their people; need dashboards, exports, and (later) multi-user access.

Because we serve all four, **knowing who the user is** (their profile and
eligibility) is central to the product, not optional.

## 4. Scope

**India-first, across all domains** — science, health, biotech, social sciences,
arts & humanities, agriculture, startups, and more — plus the key **international
funders that Indians can access** (e.g. Fulbright, DFG, Horizon Europe, JSPS,
Humboldt). Strategy: own the Indian funding landscape completely before expanding
globally.

## 5. The core value (our edge)

Not "another search box." FundRadar wins on the **combination** of four things:

1. **Everything in one place** — every funder, comprehensive and continuously fresh.
2. **Eligibility checks** — see only what you actually qualify for.
3. **Personalized matching** — enter your profile (role, field, level, stage) and
   get a tailored list.
4. **Deadline alerts & tracking** — never miss a closing date.

> Tagline idea: *"Not just funding search — it tells you what you qualify for, and
> reminds you before it closes."*

## 6. Functionalities

### Built so far
- Source database of funding organisations (41 today, 18 countries).
- Polite generic web scraper with headless-browser rendering for JavaScript sites.
- AI extraction (amount, eligibility, deadline, research area, summary, tags) with
  currency/date normalisation.
- Automated monitoring pipeline with change detection and scheduling.
- Read API + professional white/blue/green dashboard (search, filter, sort).
- Plain-language chatbot over the verified data.
- Security & reliability layer (headers, rate limiting, safe errors, input limits).

### Planned toward launch
- **User accounts & profiles** (role, field, eligibility) — foundation for everything personal.
- **Personalized matching** — profile → eligible opportunities.
- **Eligibility checks** on each opportunity.
- **Deadline alerts & a personal tracker** (email/notification reminders).
- **Semantic (meaning-based) search** for the chatbot.
- **Full coverage** — process all sources, add PDF reading, expand to every Indian domain.
- **Data-trust features** (see §7).
- **Production hosting & database** (always-on server, PostgreSQL).

## 7. Data trust & accuracy (the approach)

Funding decisions depend on this data, so accuracy is a first-class concern. The
chosen approach is a **hybrid**:
- Every opportunity **links to its official source page** so users can verify.
- Each record shows a **confidence indicator** and a **"last verified" date**.
- **High-confidence** AI extractions publish automatically; **low-confidence** ones
  are flagged for a quick **human review** before being shown prominently.

This scales (mostly hands-off) while protecting credibility — the AI never has to
be perfect, and users always have a verification path.

## 8. Sustainability / monetization

- **Now:** completely free, to test and build a user base.
- **Later:** a **freemium** model — free browsing and search for everyone; a paid
  tier for personalized matching, deadline alerts, and exports; and **institutional
  subscriptions** for universities/organisations (multi-user dashboards, analytics).
- **Design implication:** build user accounts early so a paid tier can be added
  later without rework.

## 9. Roadmap to launch

1. **Deploy live** for review (immediate).
2. **Expand coverage** — all Indian domains, JS + PDF handling, process all sources.
3. **Accounts & profiles** → **personalized matching** + **eligibility checks**.
4. **Deadline alerts & tracker.**
5. **Smarter chatbot** (semantic search, natural-language answers).
6. **Data-trust features** (source links, confidence, verification).
7. **Scale** — PostgreSQL + always-on hosting; then introduce the paid tier.

## 10. What success looks like

A growing number of Indian researchers, students, startups, and institutions
using FundRadar regularly as their default way to find funding — measured by
return visits, opportunities tracked, and deadlines met that would otherwise have
been missed.
