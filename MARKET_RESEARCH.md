# MARKET_RESEARCH.md — CPA Budget Platform

> **Purpose** — Output of "Step 1: Market & Web Analysis" in the four-step
> planning workflow. Feeds into `PRD.md` (Step 2) + `ARCHITECTURE.md` (Step 3).
> Mix of earlier Perplexity-style research (sections 1–5) and a fresh verified
> research pass (sections 6–10) run April 2026 using live web searches.
> Everything in sections 6–10 was source-verified in this pass; sections 1–5
> are kept from the earlier pass for color and unverified-but-plausible detail.

---

### 1. Competitor Teardown: Israeli Municipal Education Budgeting

The landscape for municipal finance in Israel is heavily dominated by legacy ERP systems and broad IT integrators, leaving a significant gap for modern, niche SaaS tailored to the Ministry of Education's "הוראה תקציבית חודשית" (Monthly Budget Instruction).

1. **ONE City (formerly אוטומציה החדשה - The New Automation)**
   * **Core Features:** The absolute dominant incumbent in Israeli municipal IT. They offer a dedicated Education module ("מערכות ניהול תקציבי לבתי הספר והגנים" - Budget management systems for schools and kindergartens) intertwined with their general billing and ERP software. 
   * **Variance/Files:** While they ingest general budget data, CPAs frequently complain that the system operates strictly as a general ledger. It lacks the nuanced, automated month-over-month driver decomposition (Enrollment vs. FTE vs. Rate) required for the CHESHBONIT (invoice) and SACAL (payroll) files. 
   * **Pricing:** Enterprise tender-based.
   * **URL:** [ONE City Education Portal](https://www.rashuiot.co.il/html5/portalLookup.taf?_id=45524&did=1118&G=8776&SM=8867)
2. **Malam-Team (מלם-תים) & Matrix (מטריקס)**
   * **Core Features:** These are massive systems integrators (often implementing SAP, Oracle, or bespoke BI). Large municipalities (e.g., Tel Aviv, Jerusalem) use them to build custom data warehouses. 
   * **HASMASLULIM handling:** They do not offer out-of-the-box route-level (HASMASLULIM) audits. CPAs auditing transportation codes 52/140 are forced to export tabular data to Excel and run manual VLOOKUPs against municipal GPS/routing data.
3. **Chilan (חילן)**
   * **Core Features:** The undisputed leader in Israeli payroll processing. They handle the SACAL (teaching staff payroll) data perfectly, but they are an HR/Payroll platform, not an education-budget variance tool. They do not ingest ICHLUSKITOT (classroom population/enrollment) to analyze why the budget changed.
4. **Taldor / Ness**
   * **Core Features:** Similar to Matrix, providing BI overlays. They do not specialize in the "חוברת סגולה" (Purple Booklet) topic code logic.
5. **In-House CPA Excel Macros ("אקסל")**
   * **The Real Competitor:** Because legacy vendors fail to provide driver decomposition, the actual tool used by 90% of municipal accountants is heavily layered Excel workbooks. The ecosystem relies fundamentally on exporting flat files and running complex macros. 

### 2. User Complaints & Unmet Needs
Your suspicions regarding the pain points of CPAs and "גזברים" (Treasurers) are entirely validated by discussions in Israeli municipal forums.

* **The Excel Chokehold:** Treasurers and municipal watchdogs frequently battle over data trapping. Systems often fail to export clean data, leading to severe frustration. Discussions in municipal data forums emphasize the absolute necessity of raw Excel manipulation because legacy dashboards are too rigid ("סרבניות שלא משחררות את קובץ האקסל" - Refusers that do not release the Excel file).
* **Opaque Roll-ups & Unused Budgets:** Think tanks and budget reviewers cite massive issues with "חוסר שקיפות והיעדר בקרה" (Lack of transparency and lack of control/oversight) regarding Ministry of Education allocations. Total sums arrive in the CHESHBONIT, but drilling down into the exact driver (did a special education student leave, or did the route rate drop?) is practically impossible without manual reconciliation. 
* *Sources:* [Hasadna Municipal Forum](https://forum.hasadna.org.il/t/topic/1598), [Taub Center on Education Budgeting](https://www.taubcenter.org.il/pr/snr-2025-education/)

### 3. Standard UI/UX Conventions & Accessibility (Israeli GovTech)
Selling SaaS to an Israeli municipality requires strict compliance with specific visual and legal frameworks.

* **Accessibility (תקן ישראלי 5568 / IS 5568):** Israeli law strictly mandates WCAG 2.0 AA compliance for all systems serving the public sector. 
* **PDF Export Rules:** Crucially, Part 2 of the standard ("ת"י 5568 חלק 2") explicitly dictates that *digital documents (PDFs)* must be accessible. Your CPA reports must have proper semantic tagging for tables, alternative text for variance graphs, and proper reading order for screen readers. Failure to do this will disqualify you from public tenders.
* **Workflow States:** Standard Hebrew SaaS conventions for approvals are: "ממתין לאישור" (Pending Approval), "אושר" (Approved), "נדחה" (Rejected), and "בטיפול" (In Progress). 
* **Data Formatting:** Dates must strictly be `DD/MM/YYYY`. Currency (`₪`) is universally placed to the left of the number in RTL interfaces (e.g., `₪ 1,500.00`), and numeric columns in tables should be left-aligned to allow decimal points to line up visually, even though the text flow is Right-to-Left. 
* *Sources:* [Israeli Standard 5568 Official Site](https://www.gov.il/he/pages/israeli_standard_5598), [Digital Document Accessibility](https://aisrael.org/%D7%9E%D7%99%D7%93%D7%A2-%D7%9C%D7%9E%D7%A0%D7%92%D7%99%D7%A9/%D7%A0%D7%92%D7%99%D7%A9%D7%95%D7%AA-%D7%90%D7%AA%D7%A8%D7%99-%D7%90%D7%99%D7%A0%D7%98%D7%A8%D7%A0%D7%98/%D7%AA%D7%A7%D7%9F-%D7%99%D7%A9%D7%A8%D7%90%D7%9C%D7%99-%D7%97%D7%93%D7%A9-%D7%A0%D7%92%D7%99%D7%A9%D7%95%D7%AA-%D7%9E%D7%A1%D7%9E%D7%9B%D7%99%D7%9D-%D7%93%D7%99%D7%92%D7%99%D7%98%D7%9C%D7%99%D7%99/)

### 4. Ministry Data Format Gotchas (HORADA ZIP)
The ZIP payload provided by the Ministry of Education is highly archaic.
* **Lack of Keys:** A major issue developers face is the lack of persistent primary keys across the different text/CSV files. Linking `HASMASLULIM` (routes) directly to the aggregated `CHESHBONIT` (invoice) requires bridging logic based on the "חוברת סגולה" topic codes, which occasionally change mid-year without clean schema versioning.
* **Encoding:** Government text files in Israel are frequently exported in `Windows-1255` (Hebrew ANSI) rather than `UTF-8`. If your ingestion engine assumes UTF-8, the Hebrew characters in the `YADANIIM` (manual adjustments) files will render as gibberish.

### 5. Pricing Benchmarks
Because you are selling to municipalities ("רשויות מקומיות"), direct SaaS credit-card swiping does not exist. Purchases must go through a formal tender process ("מכרז פומבי") or fall under a "פטור ממכרז" (tender exemption) if the cost is low enough.
* **Tender Participation:** Municipalities charge simply to view the RFP (e.g., [Eshkol HaSharon charges 1,000 ₪ non-refundable](https://esharon.co.il/mihrazim-cpt/%D7%9E%D7%9B%D7%A8%D7%96-%D7%A4%D7%95%D7%9E%D7%91%D7%99-%D7%9E%D7%A1-012026-%D7%9C%D7%94%D7%A4%D7%A2%D7%9C%D7%AA-%D7%9E%D7%A8%D7%9B%D7%96%D7%99-%D7%97%D7%9B%D7%9E-%D7%97%D7%99%D7%96%D7%95/)).
* **Annual Licensing:** Comparable modular financial SaaS products for Israeli municipalities run between **40,000 ₪ to 150,000 ₪ annually**, depending entirely on the municipality's socioeconomic scale ("אשכול סוציואקונומי") and population size. Implementation and initial data migration (integrating with ONE City or Matrix) is heavily front-loaded in the contract pricing.

---

## 6. Verified competitors — April 2026 fresh pass

The single most important finding in this fresh pass: no branded product
surfaced in any search that does what this platform does (ingest HORADA ZIPs,
reconcile CHESHBONIT against detail files, decompose variance by topic code,
surface per-route HASMASLULIM audit, produce Ministry-audit-ready reports).
That's our wedge.

### 6.1 EPR Systems / MASTER Mathix ⭐ primary incumbent

Founded 2000. Joined **TSG Group in 2022**. Their own site describes MASTER
Mathix as *"the only system specially developed for local authorities"* for
financial + logistical management — i.e. they self-position as the muni ERP
incumbent. Windows desktop, not SaaS. Education-budget is a module inside the
larger product, not the focus. No evidence of per-route / per-formula variance
decomposition.

- [EPR Systems — financial module](https://www.eprsystems.co.il/financial)
- [EPR Systems — main](https://www.eprsystems.co.il)
- [EPR Systems — old product page](https://www.eprsys.co.il/page.asp?pageID=8&lang=he)
- [TSG IT Systems — municipal 360](https://www.tsgitsystems.com/en/municipal/)

### 6.2 Malam-Team, Matrix, Taldor, Ness (large integrators)

IT services houses. They deliver SAP / custom systems into big municipalities
but don't ship a shrink-wrapped Ministry-of-Education reconciliation product.
They're the hosts of "in-house" systems — we compete on *focus + Ministry
domain depth*, not scale.

- [Malam-Team — Dun's 100](https://www.duns100.co.il/en/MalamTeam_Group)
- [Malam-Team — Bloomberg](https://www.bloomberg.com/profile/company/MLTM:IT)
- [Taldor — profile](https://www.taldor.co.il/company-profile/)

### 6.3 CPA advisory firms — customers, not competitors

**Mishor CPA (מישור חשבות וייעוץ עסקי)** explicitly markets accounting +
consulting for local authorities including MEITAR-participation work. Today
they do reconciliation in Excel. Selling them a tool that 10× their
throughput is the single cleanest pitch in the deck.

- [Mishor CPA — muni services](https://mishorcpa.co.il/%D7%9E%D7%99%D7%A9%D7%95%D7%A8%D7%99%D7%9D-%D7%9C%D7%A8%D7%A9%D7%95%D7%99%D7%95%D7%AA-%D7%9E%D7%A7%D7%95%D7%9E%D7%99%D7%95%D7%AA/)

### 6.4 The Ministry's own tools (set the parity bar)

Anything we ship must at minimum match the Ministry's own transparency. Our
numbers must reconcile to MEITAR to the shekel, or the CPA won't trust us.

- **MEITAR (מית"ר)** — unified payments portal, publicly transparent:
  [pob.education.gov.il/budget/meitar-system](https://pob.education.gov.il/budget/meitar-system/)
- **GEFEN (גפן)** — school-level pedagogical budget portal:
  [pob.education.gov.il/budget/main-gefen/digital-content](https://pob.education.gov.il/budget/main-gefen/digital-content/)
- **POB** — master portal for local authorities + education owners:
  [pob.education.gov.il](https://pob.education.gov.il/)
- **MTRNET** — user-flagged "goated" reference for topic codes + HORADA:
  `apps.education.gov.il/mtrnet/`
- **Annual participation criteria PDFs** (yearly "purple booklet"
  predecessors/updates):
  [2020/21 (tashpa)](https://meyda.education.gov.il/files/MinhalCalcala/hishtatfutmisrad_tashpa.pdf),
  [2017/18 (tashah)](https://meyda.education.gov.il/files/MinhalCalcala/hishtatfutmisrad_tashah.pdf),
  [2025 proposal](https://meyda.education.gov.il/files/MinhalCalcala/hazaat_takziv2025.pdf).

---

## 7. Verified pain points (State Comptroller + press)

These are not speculation — they're published.

### 7.1 State Comptroller explicitly cited the computerized-oversight gap

The 2022 report on local-authority audit flagged that the Interior Ministry
has **no computerized tools** for managing unusual development budgets and
*"management is manual; the office cannot produce periodic reports to support
control and supervision."* The 2023 report on differential budgeting followed
up with evidence that differential Ministry funding is eroded by
own-source muni spending, making variance attribution practically impossible
without a tool like this one.

- [State Comptroller 2022 — Taktzivim](https://library.mevaker.gov.il/sites/DigitalLibrary/Documents/2022/Shilton/2022-Shilton-202-Taktzivim.pdf)
- [State Comptroller 2023 — Differential Budgeting](https://library.mevaker.gov.il/sites/DigitalLibrary/Documents/2023/2023.5/2023.5-210-Differential-Budget-Edu.pdf)
- [State Comptroller 2023 — Social audit / local authorities](https://library.mevaker.gov.il/sites/DigitalLibrary/Documents/2023/2023-Shilton/2023-Shilton-203-Limudim.pdf)

**Sales takeaway**: citing the State Comptroller by name is the strongest
third-party validation we can reach for in any GovTech pitch.

### 7.2 Strong-vs-weak municipality gap (4.6×)

Taub Center data: per-student spending from local-authority own sources in
cluster 7–8 munis is **4.6×** cluster 1–2. Weak munis *can't afford* to lose
reconcilable amounts to Excel errors — which means our product delivers the
biggest value to the smallest budget muni.

- [Taub Center — local authorities](https://www.taubcenter.org.il/en/pr/local-authorities/)

### 7.3 Press coverage of Ministry differential-funding failure

Published reporting that *the Ministry's differential funding fails to close
gaps because municipalities' own spending dwarfs Ministry Δ*. CPAs need a tool
that can cleanly split Ministry-contributed Δ from own-source Δ per topic.

- [Calcalist — tech budget fail](https://www.calcalist.co.il/local_news/article/hk1sjnox3)
- [Calcalist — inequality in education](https://www.calcalist.co.il/local/articles/0,7340,L-3847242,00.html)
- [Israel Hayom — system failure](https://www.israelhayom.co.il/news/education/article/14517629)

### 7.4 Manual reconciliation universal pain (not Israel-specific)

Generic but real. Fohlio + Euna both describe the time/error tax.

- [Fohlio — pain of manual budget reconciliation](https://www.fohlio.com/blog/the-pain-of-manual-budget-reconcillation-and-7-ways-to-fix-it)
- [Euna — K-12 budget software](https://eunasolutions.com/resources/how-questica-budget-removes-the-pain-of-manual-budgeting-for-k-12-schools/)

---

## 8. IS 5568 accessibility — launch-blocker, not polish

- In force since Oct 2017, **mandatory** for public-facing Israeli sites
  including government + every muni.
- Requires **WCAG 2.0 Level AA** conformance.
- Fines up to **NIS 50,000**, private individuals can sue.
- **Part 2 extends this to PDF exports** — the CPA's monthly report PDF must
  have proper semantic table tagging, alt text on variance charts, and
  correct reading order for screen readers. This directly disqualifies any
  vendor whose reports are image-only or untagged PDFs.

- [Gov.il — IS 5568 official PDF](https://www.gov.il/BlobFolder/legalinfo/israeli_accessibility_standards_pdf/he/sitedocs_si-5568-1-september-2023.pdf)
- [TabNav guide (Hebrew)](https://tabnav.com/he/info-center/accessibility-standard-5568-israel-law)
- [AccessiBe — IS 5568](https://accessibe.com/compliance/is-5568)
- [EqualWeb — IS 5568](https://www.equalweb.com/p/43310/8656/israel_standard_5568_compliance)

**Action**: axe-core (or equivalent) must run in CI before first muni
onboarding. The PDF pipeline (`backend/services/pdf_generator.py`) needs a
tagged-PDF pass — plain ReportLab output is not compliant by default.

---

## 9. Ministry data format — verified externals

Clean externally-verifiable facts to cross-check the parser:

- **Transportation (codes 52 / 140)** is funded via **two methods** — per-student
  and per-route. Our `transport_routes` model covers the per-route method via
  HASMASLULIM.
  [POB transportation](https://pob.education.gov.il/municipal-services/transportation/)
- **Purple booklet structure**: organized by age group, with appendices
  containing per-position example costs, cluster lists, and a
  topic-code → calculation-model map. Special-ed topics live with their age
  group (except kindergarten special-ed → kindergarten chapter).
  [Participation 2020/21 PDF](https://meyda.education.gov.il/files/MinhalCalcala/hishtatfutmisrad_tashpa.pdf)
- **Knesset glossary** for budget terminology:
  [Knesset MMM glossary](https://fs.knesset.gov.il/globaldocs/MMM/fc793c1b-6855-eb11-811a-00155d0af32a/2_fc793c1b-6855-eb11-811a-00155d0af32a_11_18149.pdf)

**Encoding** (from earlier pass, unverified in this pass but matches field
reality — keep in mind): CSVs frequently arrive as Windows-1255, not UTF-8.
Our parser must detect or force the right encoding on ingest.

---

## 10. What this research *changes* about product direction

Feeds directly into `PRD.md` (Step 2):

1. **Position against EPR / MASTER Mathix, don't replace it.** Sell as *"the
   variance-explanation and Ministry-audit layer on top of your existing muni
   ERP."* Integrate via CSV/Excel export on request.
2. **Sales deck slide 1 = State Comptroller quote on the computerized-oversight
   gap.** Free credibility.
3. **Prioritize weak-cluster (1–4) munis for early adopters.** Biggest value per
   shekel; more likely to outsource to the CPA firms that buy our tool.
4. **IS 5568 + Part 2 (PDF) is a launch blocker.** Reports have to ship as
   tagged, accessible PDFs or we fail public-tender evaluations.
5. **MEITAR parity is a trust signal.** Build a "MEITAR sanity check"
   endpoint that reconciles our computed CHESHBONIT totals to MEITAR public
   payments.
6. **Moat = structured per-topic variance decomposition** (enrollment Δ × rate
   Δ × residual) with route- and class-level drill-down. Nothing else surfaced
   does this.
7. **Hebrew-first + RTL-first is a feature, not a checkbox.** Every generic
   ERP that "also supports Hebrew" will lose to a Hebrew-native product.
8. **Primary buyer hypothesis** (still to validate with interviews): the
   **CPA audit firm** (Mishor-style), not the muni itself — white-label them
   tooling, they expand the service into more munis, muni never has to sign a
   tender. Avoids the 40–150K NIS tender cycle entirely.

---

## 11. Open questions to resolve before Step 2 (PRD)

- Primary buyer — muni treasurer (גזבר), CPA audit firm, or Ministry itself?
- Pricing — per-muni license vs. per-CPA-firm license vs. per-audit?
- Channel partner opportunity with Mishor-style firms (white-label)?
- Does MEITAR expose a machine-readable API, or only HTML?
  (Check `apps.education.gov.il/mtrnet/` directly — egress-blocked from here.)
- Cluster-based pricing politically viable?

---

## 12. Consolidated source list (April 2026 fresh pass)

Competitors + muni ERP:
[EPR Systems financial](https://www.eprsystems.co.il/financial) ·
[EPR main](https://www.eprsystems.co.il) ·
[TSG municipal 360](https://www.tsgitsystems.com/en/municipal/) ·
[Malam-Team Dun's 100](https://www.duns100.co.il/en/MalamTeam_Group) ·
[Taldor profile](https://www.taldor.co.il/company-profile/) ·
[Mishor CPA muni services](https://mishorcpa.co.il/%D7%9E%D7%99%D7%A9%D7%95%D7%A8%D7%99%D7%9D-%D7%9C%D7%A8%D7%A9%D7%95%D7%99%D7%95%D7%AA-%D7%9E%D7%A7%D7%95%D7%9E%D7%99%D7%95%D7%AA/)

Ministry portals + primary data:
[POB](https://pob.education.gov.il/) ·
[MEITAR](https://pob.education.gov.il/budget/meitar-system/) ·
[POB transportation](https://pob.education.gov.il/municipal-services/transportation/) ·
[GEFEN digital content](https://pob.education.gov.il/budget/main-gefen/digital-content/) ·
[Participation 2020/21](https://meyda.education.gov.il/files/MinhalCalcala/hishtatfutmisrad_tashpa.pdf) ·
[Participation 2017/18](https://meyda.education.gov.il/files/MinhalCalcala/hishtatfutmisrad_tashah.pdf) ·
[2025 budget proposal](https://meyda.education.gov.il/files/MinhalCalcala/hazaat_takziv2025.pdf) ·
[Ministry budget admin](https://minhal-calcala.education.gov.il/budget/) ·
[Knesset glossary](https://fs.knesset.gov.il/globaldocs/MMM/fc793c1b-6855-eb11-811a-00155d0af32a/2_fc793c1b-6855-eb11-811a-00155d0af32a_11_18149.pdf)

Pain points + policy:
[State Comptroller 2022 Taktzivim](https://library.mevaker.gov.il/sites/DigitalLibrary/Documents/2022/Shilton/2022-Shilton-202-Taktzivim.pdf) ·
[State Comptroller 2023 Differential Budgeting](https://library.mevaker.gov.il/sites/DigitalLibrary/Documents/2023/2023.5/2023.5-210-Differential-Budget-Edu.pdf) ·
[State Comptroller 2023 Social audit](https://library.mevaker.gov.il/sites/DigitalLibrary/Documents/2023/2023-Shilton/2023-Shilton-203-Limudim.pdf) ·
[Taub Center](https://www.taubcenter.org.il/en/pr/local-authorities/) ·
[Calcalist tech fail](https://www.calcalist.co.il/local_news/article/hk1sjnox3) ·
[Calcalist inequality](https://www.calcalist.co.il/local/articles/0,7340,L-3847242,00.html) ·
[Israel Hayom](https://www.israelhayom.co.il/news/education/article/14517629) ·
[Fohlio](https://www.fohlio.com/blog/the-pain-of-manual-budget-reconcillation-and-7-ways-to-fix-it) ·
[Euna](https://eunasolutions.com/resources/how-questica-budget-removes-the-pain-of-manual-budgeting-for-k-12-schools/)

Accessibility + RTL UX:
[Gov.il IS 5568 PDF](https://www.gov.il/BlobFolder/legalinfo/israeli_accessibility_standards_pdf/he/sitedocs_si-5568-1-september-2023.pdf) ·
[TabNav](https://tabnav.com/he/info-center/accessibility-standard-5568-israel-law) ·
[AccessiBe](https://accessibe.com/compliance/is-5568) ·
[EqualWeb](https://www.equalweb.com/p/43310/8656/israel_standard_5568_compliance) ·
[Techradiant RTL](https://medium.com/techradiant/quick-guideline-for-rtl-ui-2da60615b655) ·
[Argos RTL QA](https://www.argosmultilingual.com/blog/planning-for-rtl-languages-how-layout-content-and-qa-fit-together) ·
[SimpleLocalize UI i18n](https://simplelocalize.io/blog/posts/ui-localization-best-practices/) ·
[Tomedes Hebrew UI](https://www.tomedes.com/translator-hub/optimize-ui-ux-hebrew-software)