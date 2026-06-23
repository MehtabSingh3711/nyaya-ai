# Technical & Business Problem Compendium — 3rd Year Batch (B.Tech CSE-AIDE)

**Duration:** 22 June 2026 → 26 July 2026 (5 weeks)
**Companion to:** 01_Workflow_Guide.md
**Purpose:** For every problem statement, this document gives you the *business scenario*, the *problem to solve*, the *technical direction* (what to learn and use), and the *deliverable shape* (what to ship).

---

## How to Read This Document

Each problem statement follows the same 6-section structure:

1. **Business Scenario** — the imagined company, its pain, and why this problem matters
2. **Problem Statement** — what you are specifically being asked to deliver
3. **Why This Matters for Placements** — which companies / roles will resonate with this
4. **Technical Direction** — what topics you need to cover, at what depth (no tutorials, just the map)
5. **Scope Boundaries** — what is in scope, what is explicitly out, what is bonus
6. **Final Deliverable Shape** — what the shipped product looks like

Pick ONE problem. Read its 6 sections fully. Then go back to Document 01 and follow the workflow.

---

# SEGMENT 1 — INSIGHTS & DECISION INTELLIGENCE

> Target roles: Data Analyst · Business Analyst · BI Analyst · Analytics Consultant
> Target companies (illustrative): TCS DA · Accenture AA · Cognizant · Mu Sigma · Tiger Analytics · Fractal · Latentview · Mphasis · JioMART BA · early-career BI at product companies

---

## A1. Churn Radar — SaaS Customer Churn Analytics

### 1. Business Scenario
You are the **first analytics hire at "Workhorse," a B2B SaaS company** that sells project-management software to mid-market engineering teams (50-500 employees). They have ~12,000 paying customers across India, SEA, and the US, paying $99-$2,499/month. Last quarter, net revenue retention dropped from 108% to 96%. The CEO wants answers: *Who is leaving, why, and what is the revenue at risk over the next 90 days if we do nothing?* The Head of Customer Success says "everyone gives different reasons in exit interviews" and the existing dashboard is a mess of 14 charts nobody trusts.

### 2. Problem Statement
Build **Churn Radar** — an end-to-end analytics product that:
- Ingests and models customer, subscription, usage, and support-ticket data into a clean warehouse
- Computes churn health: leading indicators (login frequency, support ticket volume, NPS), lagging indicators (downgrades, cancels)
- Segments customers via RFM and identifies "quiet quitter" cohorts (still paying, usage collapsing)
- Forecasts 30/60/90-day churn risk per account with a simple, interpretable model
- Surfaces the output in a 4-tab exec dashboard: **Health · Segments · At-Risk Pipeline · Why They Left**
- Quantifies revenue at risk in ₹/month, with a "save-list" ranked by save-probability × ARR

### 3. Why This Matters for Placements
Churn is the universal business problem. Every product company, every subscription business, every B2B SaaS asks this. A solid churn project demonstrates the full analytics stack: data modelling, statistical reasoning, business framing, stakeholder comms. This is the kind of project that wins interviews at **TCS Digital, Accenture AA, Tiger Analytics, Mphasis, Latentview, JioMART, Razorpay BA, and most consulting analytics interviews.**

### 4. Technical Direction

**Data layer**
- Synthetic dataset generation OR public SaaS dataset (e.g., IBM Telco, Kaggle "SaaS Customer Churn") — but you MUST augment it with realistic support tickets, login events, and a usage-event stream
- Schema design: star schema with `dim_customer`, `dim_date`, `fact_subscription_event`, `fact_usage_event`, `fact_support_ticket`
- dbt for transformations, with at least 8 models (staging → intermediate → marts)
- Data quality tests with `dbt-expectations` or `dbt-utils` (uniqueness, not-null, accepted ranges, referential integrity)

**Warehouse**
- Snowflake free trial, BigQuery free tier, or local Postgres — your choice. Justify it in an ADR.

**Analysis & modelling**
- Cohort retention heatmap
- RFM segmentation (Recency, Frequency, Monetary)
- Survival analysis (Kaplan-Meier) for time-to-churn
- A churn-risk score using logistic regression or gradient boosting (XGBoost) with proper time-based train/val/test split
- SHAP for per-customer explanations
- Revenue-at-risk = Σ (ARR_customer × P(churn in 90d))

**Dashboard**
- Streamlit, Plotly Dash, or Metabase. Must be hosted on a public URL.
- 4 tabs as above
- At least 3 "drill-down" interactions (click cohort → see customers, click customer → see their usage timeline)
- An exec-summary card on tab 1: "₹X.X Cr at risk in next 90d, 142 accounts, top 3 reasons"

**Communication**
- A 12-page "Insights Report" written for the CEO — not the data team
- 10 SQL business questions with optimised queries (window functions, CTEs, anti-joins)

### 5. Scope Boundaries
- **In scope:** synthetic-but-realistic data, full warehouse modelling, 1 risk model, 4-tab dashboard, insights report
- **Out of scope:** real-time scoring, multi-tenant UI, SSO
- **Bonus (if time):** "Save playbook" — for each at-risk account, suggest the next best action (call from CSM, in-app nudge, discount offer) based on the reason segment

### 6. Final Deliverable Shape
- Public GitHub repo with: dbt project, ingest scripts, model training, dashboard app, README
- Hosted dashboard URL
- `insights_report.pdf` (or .md) — exec-ready
- `sql_portfolio.sql` — 10 questions with commentary
- `ADR-001-warehouse-choice.md` and 2 more ADRs
- 5-min Loom walkthrough
- Resume bullets (3-4)

---

## A2. Pricing Forensics — Quick-Commerce Pricing Intelligence

### 1. Business Scenario
You are a **Pricing Analyst at "Zipp", a 10-minute grocery delivery startup** operating in 8 Indian cities. The category team is bleeding margin: competitor price changes are tracked manually by 4 analysts in spreadsheets, markdowns are decided by gut feel, and there was a public backlash last month when Zipp was charging 18% more than Blinkit for a SKU during a cricket final. Leadership wants a system that **watches competitor prices, detects anomalies, models demand elasticity, and recommends a markdown policy that protects margin without losing basket share.**

### 2. Problem Statement
Build **PricePulse** — a pricing-intelligence platform that:
- Ingests daily competitor price scrapes (synthesise 6-9 months of price history for 3-4 competitors across 200 SKUs in a category, e.g., biscuits or personal care)
- Cleans the data: handles missing prices, detects scraper failures, reconciles SKU name variations
- Detects price anomalies: z-score, IQR, and a simple change-point detector on competitor price series
- Models price elasticity of demand per SKU category using historical price-volume pairs (log-log regression or Bayesian hierarchical model — your choice, justify it)
- Recommends a markdown policy: for each SKU in a category, "lower by X% if competitor is Y% lower, raise by Z% if demand-elastic and we're undercutting"
- Exposes all of this in a dashboard with 3 tabs: **Market View · Elasticity Curves · Markdown Planner**

### 3. Why This Matters for Placements
Pricing is the highest-stakes business problem in e-commerce. Anyone interviewing for **Blinkit, Zepto, Swiggy Instamart, Flipkart, Amazon, Myntra, Nykaa, BigBasket, JioMart, or any D2C brand** will recognise this instantly. Demonstrates real-world data engineering (scrape → warehouse) + econometric reasoning + business framing.

### 4. Technical Direction

**Data layer**
- Web-scraping module (Scrapy or Playwright) for a small set of public-facing e-commerce sites, OR generate realistic synthetic data (preferred for legal reasons — and you must document why)
- A price-event fact table with `(date, sku, competitor, price, in_stock_flag)`
- Data quality rules: stuck-at-same-price-for-N-days → scraper-broken alert

**Analysis**
- Time-series outlier detection on competitor prices
- Price elasticity estimation: `log(quantity) ~ log(price) + controls`, segment by category
- Markdown simulator: given the elasticity estimates, what is the optimal markdown % per SKU to maximise revenue, subject to "must not be >X% more expensive than competitor median"?

**Dashboard**
- Plotly Dash or Streamlit
- Market View: heatmap of (competitor × SKU) median prices, with our price overlaid
- Elasticity Curves: per-category regression line with confidence band, R² reported
- Markdown Planner: a table you can sort/filter with recommended actions, expected revenue impact, and confidence

**Communication**
- A 10-page memo to the category head: "What the data says about our current pricing, what to fix Monday morning, and what to keep watching"
- 8 SQL business questions on the data

### 5. Scope Boundaries
- **In scope:** scrape or simulate scrape data, clean it, elasticity model, markdown recommender, dashboard
- **Out of scope:** real-time bidding, multi-region, A/B test execution
- **Bonus:** A "what-if" simulator in the dashboard where the user can change the competitor price and see the recommended response

### 6. Final Deliverable Shape
- GitHub repo with scraper (or simulator), warehouse models, elasticity model, dashboard, ADRs
- Hosted dashboard
- `pricing_memo.pdf`
- `sql_portfolio.sql`
- Loom + resume bullets

---

## A3. Funnel Autopsy — Fintech Marketing Attribution & Funnel Analytics

### 1. Business Scenario
You are the **Growth Analytics lead at "PaisaOne", a digital lending fintech** that offers personal loans up to ₹5 lakh. Their app has 2M downloads but conversion from "app open" to "disbursed loan" is 0.4%. The marketing team spends ₹12 Cr/month across Google, Meta, affiliates, and influencers — but cannot answer "which channel actually drives disbursed loans, not just app installs?" Last-touch attribution gives Meta 70% of the credit, but the data team suspects it's wrong. They need a **multi-touch attribution model, a funnel diagnostic that pinpoints where users drop, and A/B test analytics that the marketing team can actually run themselves.**

### 2. Problem Statement
Build **FunnelScope** — a full-stack growth-analytics product:
- Ingests 3 data sources: marketing touch events (impressions, clicks, installs), in-app events (signup, KYC start, KYC done, loan apply, approved, disbursed), and A/B test assignment + outcomes
- Models the funnel with stage-to-stage conversion rates, with cohort breakdowns by acquisition channel, city tier, and device
- Implements 3 attribution models: last-touch, first-touch, and a data-driven multi-touch (Shapley-value-based, or simple time-decay — your choice, justify it)
- Surfaces an A/B test analyser: input a test's exposure + variant + outcome → outputs lift, p-value, CI, segment-level breakdown, and a "would you ship this?" verdict
- Dashboard with 3 tabs: **Funnel · Attribution · Experiments**

### 3. Why This Matters for Placements
Every consumer-tech, fintech, edtech, and D2C company asks these exact questions. **PhonePe, Paytm, Cred, Razorpay, Groww, Zerodha, Jupiter, Slice, KreditBee, Tata Neu, Flipkart, Myntra, Nykaa, Swiggy** — they all have growth analytics teams hiring. This project demonstrates the full growth-stack: events, attribution, experimentation, which is the holy trinity of modern product analytics.

### 4. Technical Direction

**Data layer**
- Synthesise 90 days of events: ~500K marketing events, ~1M in-app events, ~50K A/B test exposures
- dbt models: `stg_events`, `int_funnel`, `fct_attribution_*`, `fct_experiments`
- Event schema following a simple spec: `user_id, event_name, event_time, properties, session_id`

**Attribution**
- Implement last-touch (easy), first-touch (easy), and one advanced model
- For the advanced model, choose ONE: Shapley-value (compute on a DAG of channels), time-decay with half-life, or Markov-chain (use the `python-markovchain` library or write it)
- Document the choice in an ADR with reasoning

**Funnel**
- Stage conversion rates with confidence intervals (beta distribution)
- Drop-off analysis: of users who drop at KYC, what % had failed face-match, failed PAN, low CIBIL, etc.
- Cohort analysis by acquisition month

**Experimentation**
- Frequentist A/B test analyser: t-test for continuous, z-test for proportions, with multiple-testing correction (Bonferroni or BH)
- Bayesian alternative as a bonus
- Sequential testing support (mSPRT or always-valid CIs) as a stretch bonus

**Dashboard**
- 3 tabs, hosted
- Funnel tab: Sankey diagram, conversion tables, drop-off reasons
- Attribution tab: side-by-side comparison of the 3 models with a "$ equivalent" column (per-channel credit in ₹)
- Experiments tab: A/B test analyser UI

**Communication**
- A memo to the CMO: "We are wasting ₹3.2 Cr/month on Meta. Here's the proof and what to do."
- 8 SQL questions on funnel/attribution

### 5. Scope Boundaries
- **In scope:** synthetic data, 3 attribution models, 1 A/B test analyser, dashboard, memo
- **Out of scope:** causal inference with double-ML, multi-arm bandits, incrementality testing
- **Bonus:** A "next experiment to run" recommender

### 6. Final Deliverable Shape
Same shape as A1, A2: repo, hosted dashboard, memo, SQL portfolio, ADRs, Loom, resume.

---

## A4. People Analytics — IT Services Workforce Analytics

### 1. Business Scenario
You are the **People Analytics Partner at "NimbusTech", a 35,000-employee IT services company**. Voluntary attrition is at 18% — high for the industry. HR business partners spend 60% of their time in spreadsheets trying to answer questions from the CHRO: "Which managers have the highest attrition in their teams? Are we losing more people from specific projects? Are our pay bands fair across genders? What's the retention curve for new joiners by college tier?" The CHRO wants a single product that answers all of these.

### 2. Problem Statement
Build **PeopleLens** — a workforce analytics platform:
- Ingests and models HR data: employee master, comp history, project assignments, manager hierarchy, performance ratings, exit interviews, learning records
- Computes attrition risk per employee (simple logistic or gradient boosting) using 1-yr-ago features (no leakage)
- Manager-effect analysis: attrition rate of each manager's team, benchmarked against teams at the same level
- Pay-fairness audit: comp-ratio distribution by gender / role / location, with statistical test for disparity
- New-joiner retention curves by college tier, joining quarter, role
- Dashboard with 4 tabs: **Attrition · Manager Effect · Pay Fairness · Retention Curves**

### 3. Why This Matters for Placements
People analytics is a fast-growing function at **TCS, Infosys, Wipro, LTIMindtree, Mphasis, Cognizant, Accenture, HCL, Tech Mahindra, Capgemini, and the GCCs (Goldman Sachs Bengaluru, JP Morgan Bengaluru, Wells Fargo, Microsoft IDC).** A People Analytics project reads as "I understand both HR and data" — rare and valuable.

### 4. Technical Direction

**Data layer**
- Synthetic HR data: 10,000+ employees across 5 years, with realistic tenure, comp, project, rating distributions
- dbt models with proper SCD-2 for employee history
- Sensitive handling: NO PII (names, emails) in the public dataset — use employee_id only

**Analysis**
- Attrition risk model: time-based split, only features known at prediction time, SHAP explanations
- Manager-effect: for each manager, compute "rolling 12-month attrition rate of direct reports" with confidence interval, benchmarked against peers
- Pay-fairness: within each (role, level, location) bucket, compute gender pay ratio + bootstrap CI; flag if outside ±5%
- Retention curves: Kaplan-Meier survival by college tier

**Dashboard**
- 4 tabs as above
- Privacy-preserving: no row-level data, only aggregated slices with k-anonymity (k≥10)
- An "executive briefing" tab: 3 charts and 3 sentences

**Communication**
- A memo to the CHRO: "We are losing 22% of new joiners in year 1 from Tier-2 colleges, costing ₹X Cr. Here's the fix."
- 6 SQL questions on workforce data

### 5. Scope Boundaries
- **In scope:** synthetic data, attrition model, manager-effect, pay-fairness, retention curves, dashboard, memo
- **Out of scope:** NLP on exit interviews (treat as a stretch), recommendation engine for retention actions

### 6. Final Deliverable Shape
Standard shape: repo, hosted dashboard, memo, SQL portfolio, ADRs, Loom, resume.

---

# SEGMENT 2 — DATA PLATFORM & PIPELINE ENGINEERING

> Target roles: Data Engineer · Analytics Engineer · Big Data Engineer · Streaming Engineer
> Target companies: Amazon DE · Flipkart · Walmart Global Tech · Razorpay · PhonePe · NPCI · Paytm · Groww · JP Morgan DE · Wells Fargo · all service-company DE tracks

---

## B1. Unified Commerce Lakehouse — Medallion Architecture for a Multi-Channel Retailer

### 1. Business Scenario
You are the **first Data Platform Engineer at "CartCo", a ₹4,000 Cr GMV multi-channel retailer** selling on its own website, Amazon, Flipkart, Myntra, and 80 physical stores. Data lives in 5 places: Shopify (own site), Seller Central APIs (Amazon, Flipkart), MySQL (in-store POS), Kafka (warehouse events), and 12 daily CSV drops from distributors. The Head of Analytics says "I can't get a single number for total revenue — every team reports a different figure." You will build the **foundation of the company's data platform**: a medallion lakehouse.

### 2. Problem Statement
Build a **medallion lakehouse** (bronze → silver → gold) for CartCo:
- **Ingestion:** 4 source connectors — Shopify GraphQL API, Amazon Selling Partner API, Kafka topic for in-store events, SFTP CSV drop loader. Use Airbyte, custom Python, or Kafka Connect — justify in ADR.
- **Storage:** S3/MinIO with **open table format** (Apache Iceberg or Delta Lake) — pick one and defend the choice.
- **Compute:** Spark (PySpark) for batch, optionally Flink/KSQL for the Kafka source
- **Layers:**
  - Bronze: raw, schema-on-read, partitioned by ingestion date
  - Silver: cleaned, deduplicated, schema-enforced, conformed to a canonical entity model
  - Gold: business-facing marts (daily revenue, channel performance, inventory turnover, customer 360)
- **Orchestration:** Airflow, Dagster, or Prefect — 3-5 DAGs minimum
- **Observability:** OpenLineage + Marquez (or DataHub) for lineage, Great Expectations for data quality, basic Grafana dashboard for pipeline health
- **Catalog:** Hive Metastore, AWS Glue Catalog, or Nessie — at least one table-level description, column-level types, ownership

### 3. Why This Matters for Placements
Lakehouse is THE data architecture of 2026. **Every** serious data company — Snowflake, Databricks, AWS, Google — hires on this. Recruiters at **Amazon DE, Flipkart, Walmart, Razorpay, PhonePe, Paytm, NPCI, Mphasis, Cognizant DataPractice, Tiger Analytics, and any company with "data platform" in the JD** will see this and immediately know you understand modern data engineering, not just SQL.

### 4. Technical Direction

**Topics you must cover (at working depth):**
- **Open table formats:** Iceberg or Delta — ACID guarantees, time-travel, schema evolution, hidden partitioning
- **Medallion architecture:** why bronze/silver/gold, how to enforce layer boundaries
- **Distributed compute:** Spark (the 800-lb gorilla), partitioning, bucketing, shuffle, broadcast joins
- **Orchestration:** DAG design, idempotency, retries, SLAs, sensors
- **Ingestion patterns:** batch (full vs incremental vs CDC), streaming (Kafka), file-based (SFTP, S3 events)
- **Data quality:** GE/Soda — types of expectations, when to fail vs warn
- **Lineage:** column-level lineage, why it matters for debugging and trust
- **Cost & performance:** partitioning strategy, file sizing, compaction, Z-ordering / hidden partitioning
- **IaC:** Terraform or Pulumi to provision the whole stack (MinIO + Airflow + Spark + Marquez)

**Stretch (pick at least one):**
- Add a streaming source end-to-end (Kafka → Flink → Iceberg)
- Implement a data contract for one source (schema-as-code, owner-signed)
- Add a small feature store (Feast) populated from the gold layer

### 5. Scope Boundaries
- **In scope:** 2-3 source connectors (synthetic data is fine), full bronze→silver→gold, 3-5 DAGs, lineage + DQ + observability
- **Out of scope:** real-time sub-second SLAs, multi-region replication, 100+ sources
- **Bonus:** Streaming source, data contracts, feature store

### 6. Final Deliverable Shape
- GitHub repo with: IaC (Terraform), ingestion code, dbt/Spark models, Airflow/Dagster DAGs, GE suites, lineage config
- Live deployment OR a fully-reproducible `docker-compose up` that boots the whole stack locally
- 5 ADRs (table format choice, orchestrator choice, partition strategy, ingestion tool, schema evolution policy)
- Architecture diagram (C4 model, both Container and Component views)
- Loom walkthrough + resume bullets

---

## B2. Clickstream Telemetry Pipeline — Real-Time Event Processing

### 1. Business Scenario
You are the **Streaming Data Engineer at "EduPlus", an edtech platform** with 8M MAU. The product team wants to know: *within 60 seconds of a student dropping out of a live class, who can we re-engage?* The current pipeline is a 6-hour batch job. You will build a real-time clickstream pipeline that handles web/mobile events at peak ~5,000 events/sec, enriches them, detects sessionisation and drop-off, and serves features to a downstream re-engagement system.

### 2. Problem Statement
Build **PulseStream** — a real-time event pipeline:
- **Producers:** synthesise events from 2-3 sources (web clicks, mobile app events, video playbacks)
- **Ingest:** Kafka with proper topic design (per-source, partitioned by user_id), Avro/Protobuf schema, Schema Registry
- **Stream processing:** Kafka Streams OR Apache Flink — pick one, justify. Compute:
  - Session windows (30-min inactivity gap)
  - Drop-off detector (user entered a live class event, no "still watching" event in last 60s)
  - Late-arrival handling (watermarks, allowed lateness, side outputs)
  - Deduplication (event_id-based, with state store)
- **Sink:** ClickHouse, Druid, Pinot, or just Iceberg/Parquet on S3
- **Downstream serving:** a simple FastAPI service that exposes "currently-at-risk users" as a feature endpoint
- **Observability:** Kafka lag dashboards, Flink/KStreams metrics, dead-letter handling
- **Replay:** ability to re-process the last 7 days from a compacted topic

### 3. Why This Matters for Placements
Streaming is the most under-taught and most-hired skill in 2026. **Razorpay, PhonePe, CRED, Swiggy, Zomato, Flipkart, Myntra, Dream11, MPL, Games24x7, ShareChat, InMobi, Glance, and all ad-tech / real-time-bidding shops** have streaming roles. A working streaming pipeline on your resume is a strong differentiator.

### 4. Technical Direction

**Topics you must cover:**
- **Kafka fundamentals:** partitions, consumer groups, exactly-once semantics, log compaction, retention, replicas, ISR
- **Schema management:** Avro/Protobuf with Confluent/Apicurio Schema Registry, backward/forward compatibility
- **Stream processing patterns:** stateless transforms, stateful aggregations, windowing (tumbling, sliding, session), joins (stream-stream, stream-table), late events
- **Watermarks & out-of-order handling:** event time vs processing time
- **State backends:** RocksDB for Flink, in-memory or RocksDB for Kafka Streams
- **Backpressure & scaling:** parallelism, rebalancing, checkpoints
- **Observability:** Burrow for lag, JMX metrics, Flink Web UI, Kafka lag exporter
- **Replay & reprocessing:** compacted topics, offsets, snapshots

**Stretch:**
- Exactly-once end-to-end with Kafka Transactions
- A simple anomaly detector (sudden drop in user activity)

### 5. Scope Boundaries
- **In scope:** synth events at modest scale, full ingest-process-serve chain, observability basics
- **Out of scope:** multi-DC replication, Schema Registry HA, real production load (100K+ eps)

### 6. Final Deliverable Shape
- GitHub repo: producers, Kafka config, stream processor, sink, serving API, Docker Compose to run it all
- Live demo of live drop-off detection
- ADRs (stream processor choice, window choice, sink choice, schema strategy)
- Loom + resume

---

## B3. Regulatory Data Mesh — Multi-Domain BFSI

### 1. Business Scenario
You are the **Lead Data Engineer at "TrustBank", a universal bank with 14M customers**, modernising its data platform to comply with RBI's Account Aggregator framework and the upcoming DPDP Act. The bank has 6 business domains (Retail Banking, Cards, Wealth, Treasury, Corporate, Risk & Compliance), each with its own data product owner. Centralised data teams have failed. The bank is going data-mesh. You will design and build the **platform and 2-3 reference data products** to prove the model works.

### 2. Problem Statement
Build a **reference data-mesh implementation** for a BFSI:
- **Domain 1 — Customer 360:** data product owned by Retail Banking, serves to all other domains
- **Domain 2 — Card Transactions:** data product owned by Cards
- **Domain 3 — Regulatory Reporting:** data product owned by Risk & Compliance
- **Platform capabilities:** data contracts (schema-as-code, SLA in YAML), self-serve ingestion templates, federated governance (data catalog with ownership), data product scorecards (SLOs on freshness, quality, usage)
- **Tech stack:** any combination, but justify; expected to include at least one lakehouse, one orchestrator, one catalog
- **Compliance angle:** data minimisation, purpose limitation, consent capture, audit trail

### 3. Why This Matters for Placements
**HSBC, Citibank, JP Morgan, Wells Fargo, Goldman Sachs, HDFC, ICICI, Axis, Kotak, SBI Cards, Paytm Payments Bank, Jupiter, Niyo, and every BFSI in India** is hiring for data platform + data mesh. This is a top-3 hot area. Compliance + engineering is rare.

### 4. Technical Direction

**Topics you must cover:**
- **Data mesh principles:** domain ownership, data as a product, self-serve platform, federated governance
- **Data contracts:** schema-as-code (e.g., Protobuf + custom YAML), contract testing, breaking-change policy
- **Data product scorecards:** SLOs on freshness, completeness, validity, usage
- **Federated catalog:** DataHub or OpenMetadata, with ownership, glossary, lineage
- **Policy-as-code:** OPA for "this dataset cannot be joined with that one without consent"
- **PII handling:** tokenisation, masking, k-anonymity
- **BFSI specifics:** consent management, purpose binding, audit log immutability

### 5. Scope Boundaries
- **In scope:** 2-3 reference data products, data contract templates, catalog, scorecards, compliance demo
- **Out of scope:** real RBI integration, production-grade security

### 6. Final Deliverable Shape
- Repo: platform code, 3 data products, data contracts, catalog config, sample compliance report
- Live demo
- ADRs on the 4 mesh principles
- Loom + resume

---

## B4. CDC Replicator — Change-Data-Capture from OLTP to Warehouse

### 1. Business Scenario
You are the **Data Engineer at "RideGo", a ride-hailing platform** whose operational database (Postgres + MongoDB) is the source of truth for drivers, rides, and payments. The analytics team needs near-real-time updates to the warehouse, but the current solution is a 4-hour batch poll. You will build a CDC pipeline that streams row-level changes from the OLTP to the warehouse in under 30 seconds, while handling schema evolution, ordering, and exactly-once semantics.

### 2. Problem Statement
Build **CDCFlight** — a CDC pipeline:
- **Source:** Postgres (logical replication / Debezium) and MongoDB (change streams)
- **Transport:** Kafka
- **Processing:** Kafka Streams or Flink — apply transformations, handle out-of-order events, deduplicate, enrich
- **Sink:** Snowflake/BigQuery/Postgres (warehouse) AND a feature store (Feast) for low-latency serving
- **Schema evolution:** add a column in source → pipeline must adapt without downtime
- **Exactly-once end-to-end** for at least the Postgres → warehouse path
- **SCD-2 modeling** in the warehouse layer (dbt snapshots or hand-rolled)

### 3. Why This Matters for Placements
CDC is the data engineer's bread-and-butter in 2026. Mentioning Debezium/Flink/Snowflake/Feast on a resume at any product company = interview. **Amazon, Flipkart, Walmart, Uber, Ola, Rapido, Swiggy, Zomato, Cred, Razorpay, PhonePe** all run CDC at scale.

### 4. Technical Direction

**Topics:**
- Logical replication (WAL, LSN, publication/subscription)
- Debezium internals (snapshot vs streaming modes, offsets)
- Kafka exactly-once: idempotent producers, transactional APIs, read_committed consumers
- Stream-table joins, lookups, enrichment
- SCD-2 with dbt snapshots
- Schema evolution: backward/forward compatibility, schema registry
- Backfill strategies

### 5. Scope Boundaries
- **In scope:** 1 OLTP source (Postgres), full pipeline, SCD-2, schema evolution demo
- **Out of scope:** multi-master replication, conflict resolution

### 6. Final Deliverable Shape
Standard. Repo, demo, ADRs, Loom, resume.

---

# SEGMENT 3 — APPLIED AI & INTELLIGENT SYSTEMS

> Target roles: AI Engineer · ML Engineer · Computer Vision Engineer · Applied Scientist (new grad)
> Target companies: NVIDIA · Samsung R&D · Qualcomm · Microsoft · Google · AWS ML · Adobe · Oracle · ServiceNow · GenAI service companies (Accenture AI, Cognizant Neuro, EY.ai, KPMG Lighthouse) · AI startups

---

## C1. Contract Intelligence — RAG + Structured Extraction over Legal/HR Contracts

### 1. Business Scenario
You are the **AI Engineer at "LawDesk", a legal-tech startup** that sells a contract-review product to in-house legal teams. Lawyers spend 60% of their time on first-pass review: "What's the termination clause? What's the liability cap? Are there non-competes?" You will build the **AI engine** that reads a contract, extracts structured fields, answers questions with citations, and flags risky clauses.

### 2. Problem Statement
Build **ClauseCraft** — a contract-intelligence system:
- **Ingestion:** PDF, DOCX, and scanned-image contracts (200+ contracts across 4 types: NDA, MSA, employment, lease)
- **Extraction:** structured fields (parties, dates, amounts, governing law, term, termination clause, liability cap, indemnification) — schema-validated JSON output
- **RAG:** ask natural-language questions, get answers with **inline citations to the exact clause** (page + paragraph + quote)
- **Risk flags:** classify clauses into risk levels (low/medium/high) for 8 standard risk types (auto-renewal, unlimited liability, broad indemnity, IP assignment, non-compete, etc.)
- **Comparison view:** upload 2 contracts, get a diff of clauses side by side
- **Hallucination guard:** answer "I don't know" when evidence is weak, with confidence score
- **Eval harness:** 100 Q&A pairs with ground truth, measure exact-match, citation-precision, and hallucination rate

### 3. Why This Matters for Placements
Legal AI is the #1 vertical where GenAI has clear ROI. **Harvey AI, Ironclad, Luminance, Evisort, Thomson Reuters, Wolters Kluwer, LexisNexis, and every Indian legal-tech (SpotDraft, Leegality, IndusLaw, Cyril Amarchand's tech team)** are hiring. Demonstrates RAG done right, structured extraction, eval, and product thinking.

### 4. Technical Direction

**Topics:**
- **Document parsing:** PyMuPDF, Unstructured.io, Tesseract OCR for scans
- **Chunking strategies:** semantic, structural (by clause heading), table-aware
- **Embeddings & vector DB:** OpenAI / Voyage / Cohere / BGE; Qdrant / Weaviate / pgvector
- **Retrieval:** hybrid (BM25 + dense), re-ranking (Cohere Rerank / bge-reranker)
- **Extraction:** structured output (Pydantic + JSON mode), function-calling
- **Eval:** Ragas, DeepEval, custom metric for citation precision
- **Guardrails:** input sanitisation, output schema validation, refusal logic
- **Caching:** semantic cache, exact-match cache
- **Cost engineering:** batching, model cascading (small model first, escalate to large on low confidence)

**Stretch:**
- Fine-tune a small model (Qwen2.5 / Phi-3 / Llama-3.2) for the extraction schema
- Multi-lingual support (Indian contracts have Hindi/regional language clauses)
- Agentic clause review: "find all contracts that auto-renew in the next 90 days"

### 5. Scope Boundaries
- **In scope:** PDF/DOCX contracts, extraction, RAG, eval, simple web UI
- **Out of scope:** e-signature integration, contract authoring, multi-tenant
- **Bonus:** fine-tuned extractor, multi-lingual

### 6. Final Deliverable Shape
- Repo: ingest, parse, chunk, embed, retrieve, extract, eval, app
- Hosted web app (Streamlit / Next.js / Gradio)
- Eval report (100 test cases, scores)
- 5 ADRs
- Loom + resume

---

## C2. Visual Quality Inspection — Manufacturing Defect Detection

### 1. Business Scenario
You are the **Computer Vision Engineer at "MetalWorks", an auto-ancillary manufacturer** producing 50,000 sheet-metal brackets per day. Quality control is done by 12 human inspectors with 92% accuracy — meaning 4,000 defective parts ship per day, causing ₹8L/month in warranty returns. You will build a vision system that inspects every part, classifies defects, and routes flagged parts to a rework station.

### 2. Problem Statement
Build **SteelSight** — a CV-based quality inspection system:
- **Dataset:** a public industrial defect dataset (MVTec AD, NEU-DET, or Severstal Steel Defect Detection on Kaggle) — 5000+ images, 5-6 defect classes + OK class
- **Detection:** object detection (YOLOv8 / YOLOv11 / RT-DETR) to localise defects; classification (EfficientNet / ConvNeXt) as a comparison
- **Active learning loop:** a UI to upload a batch of "uncertain" predictions for human review, retrain, redeploy
- **Edge deployment:** export to ONNX → TensorRT → run inference on a simulated edge device (Jetson Nano emulator or a laptop with latency budget)
- **Edge-case collector:** low-confidence predictions get logged, queued for labeling
- **Drift monitor:** PSI/KS-test on input image features (brightness, contrast) and on prediction distribution
- **Dashboard:** defect rate per hour, per line, per class, top defect types, model performance over time

### 3. Why This Matters for Placements
Manufacturing AI is booming in India. **Tata Steel, Tata Motors, Mahindra, Maruti, Hyundai, Samsung Chennai, Apple (Foxconn), Flex, Wistron, Bharat Forge, Bharat Electronics, HAL** are all hiring CV engineers. A solid CV project with edge deployment is interview gold.

### 4. Technical Direction

**Topics:**
- **Object detection:** YOLO family, anchor-free vs anchor-based, mAP, IoU, NMS
- **Data augmentation:** mosaic, mixup, copy-paste, domain-specific (lighting, blur)
- **Class imbalance:** focal loss, oversampling, hard-negative mining
- **Model export:** ONNX, TensorRT, OpenVINO
- **Active learning:** uncertainty sampling, diversity sampling, human-in-the-loop
- **Drift detection:** image-level (CNN embeddings), pixel-level (intensity histograms), prediction-level (confidence distribution)
- **MLOps basics:** experiment tracking (MLflow / W&B), model registry, CI for model retraining
- **Production concerns:** latency budget, batching, async inference, queueing

### 5. Scope Boundaries
- **In scope:** public dataset, detection + classification, active learning UI, edge export, drift monitor, dashboard
- **Out of scope:** real PLC integration, multi-camera sync
- **Bonus:** synthetic defect generation (using diffusion) to augment rare classes

### 6. Final Deliverable Shape
- Repo: data, training, eval, export, inference server, active learning UI, drift monitor, dashboard
- Live demo
- Loom + resume

---

## C3. Voice-First Customer Support — Multilingual Speech AI

### 1. Business Scenario
You are the **AI Engineer at "HelpLine Co.", a BPO serving Indian D2C and fintech clients**. 70% of support calls are routine: "What's my order status?", "Reset my password", "Update my address". Agents handle 50 calls/day, costing ₹40/call. You will build a **voice AI agent** that handles tier-1 calls end-to-end in Hindi, English, and Hinglish.

### 2. Problem Statement
Build **Vani** — a multilingual voice agent:
- **ASR:** Whisper / wav2vec-BERT / IndicConformer for Hindi, English, and code-mixed
- **Intent + entity:** classify the caller's intent (50+ intents), extract entities (order ID, phone number, date)
- **Dialog manager:** state machine + LLM-driven fallback
- **TTS:** natural-sounding response (Bark / XTTS / ElevenLabs clone / Azure)
- **Telephony:** Twilio / Exotel integration OR a web-based mic demo if telephony is hard
- **Tool use:** agent calls real APIs (order status, password reset, address update) — synthetic or stubbed
- **Observability:** Arize Phoenix / Langfuse traces, with the full call transcript + audio + tool calls
- **Eval:** 100 test calls, measure intent accuracy, task success, average handle time
- **Safety:** PII redaction in logs, no hallucinated order data

### 3. Why This Matters for Placements
Voice AI is the next wave. **Sarvam AI, Krutrim, Yellow.ai, Verloop, Haptik, Ozonetel, Yellow.ai, Exotel, Cisco (Webex), Microsoft Teams, and every BPO / contact-center-as-a-service** is hiring speech-AI engineers. A working voice agent is a top-1% project.

### 4. Technical Direction

**Topics:**
- ASR: Whisper variants, IndicConformer, language ID, code-switching
- NLU: intent classification, NER, slot filling
- Dialog systems: state machines, LLM-as-orchestrator, tool calling
- TTS: zero-shot cloning, prosody, latency
- Telephony: SIP, WebRTC, Twilio Media Streams
- Streaming: partial transcripts, endpointing, barge-in
- Eval: turn-level success, task completion, MOS, latency
- Observability: trace-based debugging for multi-turn dialogs

### 5. Scope Boundaries
- **In scope:** ASR → intent → dialog → TTS → tool use → trace, 1 language pair (Hindi ↔ English), web demo
- **Out of scope:** emotion detection, real telephony carrier, multi-tenant
- **Bonus:** streaming ASR with <500ms latency

### 6. Final Deliverable Shape
Standard. Repo, live demo (call the agent, talk to it), eval report, Loom, resume.

---

## C4. Predictive Supply Chain — FMCG Demand Forecasting + Replenishment

### 1. Business Scenario
You are the **ML Engineer at "FreshKart", a 500-store FMCG retailer**. Stockouts cause lost sales of ₹4 Cr/month; overstock causes 8% wastage of perishables. The replenishment team uses a 90-day moving average. You will build a **forecasting + replenishment system** that predicts daily demand per SKU per store, then recommends an order quantity that balances stockout cost vs holding cost.

### 2. Problem Statement
Build **FreshMind** — a demand forecasting + replenishment system:
- **Dataset:** M5 Forecasting (Walmart) OR generate synthetic (Kaggle "Favorita", "Store Item Demand") — daily sales for 1000+ SKUs across 10 stores, 4 years
- **Features:** price, promotions, holidays, weather, day-of-week, month, lag features, rolling stats, Fourier features for yearly seasonality
- **Models:** baseline (naive, seasonal naive), classical (Prophet, ETS), ML (LightGBM with lag features), deep (TFT / N-BEATS / PatchTST) — compare all
- **Hierarchical reconciliation:** forecast at SKU-store, then reconcile up to store → region → total using MinT or bottom-up
- **Replenishment:** for each SKU-store-day, compute order-up-to level given forecast, lead time, holding cost, stockout cost, service level target
- **Backtest:** walk-forward validation, measure WAPE, bias, stockout-days, wastage
- **Dashboard:** forecast vs actual, stockout heatmap, replenishment recommendations

### 3. Why This Matters for Placements
Supply chain AI is universal. **Amazon, Flipkart, Walmart, BigBasket, Blinkit, Zepto, JioMart, Swiggy Instamart, Domino's, McDonald's, all CPG companies, all D2C** hire for this. Plus, it's one of the cleanest ML problems to defend in an interview.

### 4. Technical Direction

**Topics:**
- Time series fundamentals: stationarity, ACF/PACF, seasonality, stationarity tests
- Feature engineering for time series: lags, rolling windows, date features, external regressors
- Models: Prophet, ETS, ARIMA, LightGBM with proper lag handling (recursive vs direct), deep models (TFT, N-BEATS, PatchTST)
- Hierarchical forecasting: MinT reconciliation, bottom-up, top-down
- Probabilistic forecasting: quantiles, prediction intervals, CRPS
- Inventory theory: newsvendor, (s, S) policy, (R, Q) policy, safety stock
- Backtesting: walk-forward vs k-fold, leakage prevention
- MLOps: scheduled retraining, model registry, drift monitoring

### 5. Scope Boundaries
- **In scope:** dataset, 4+ models compared, hierarchical reconciliation, replenishment policy, dashboard
- **Out of scope:** real supplier integration, multi-echelon
- **Bonus:** probabilistic forecasting + newsvendor-based replenishment

### 6. Final Deliverable Shape
Standard. Repo, dashboard, eval report, Loom, resume.

---

# SEGMENT 4 — MLOPS & PRODUCTION ML

> Target roles: MLOps Engineer · ML Platform Engineer · ML Reliability · ML Infrastructure
> Target companies: MLOps-specific teams at fintech, healthtech, retail-tech · Service-company MLOps practices · MLOps startups (Weights & Biases, Tecton, Arize, Fiddler, WhyLabs equivalents in India) · Platform engineering teams at product companies

---

## D1. Feature Store in a Box

### 1. Business Scenario
You are the **ML Platform Engineer at "LoanAI", a fintech serving 5M users**. Two ML teams (credit scoring, fraud detection) are independently reinventing feature pipelines. Features are computed differently in batch and online, leading to training-serving skew. You will build a **central feature store** that 2 model teams will consume, with online + offline consistency, point-in-time correctness, and a self-serve UI for feature registration.

### 2. Problem Statement
Build **FeatureHub** — a self-serve feature store:
- **Feature store:** Feast (open source) on Kubernetes OR Hopsworks — pick one, justify
- **Batch pipeline:** 3-5 feature pipelines using Spark / dbt / SQL, registered in the store
- **Online store:** Redis or DynamoDB-backed
- **Offline store:** S3 / Parquet / Iceberg
- **Point-in-time correctness:** historical feature retrieval for training
- **Online-offline consistency:** same feature definition produces same value in both stores
- **Feature registry / catalog:** web UI to browse, search, request access, see lineage
- **2 consumers:** a credit-scoring model and a fraud-detection model both consume features
- **Monitoring:** feature freshness, value distribution drift, online serving latency

### 3. Why This Matters for Placements
Feature stores are a defining MLOps skill. **Every serious ML team in 2026 has one.** Recruiters at fintech, retail-tech, healthtech, and ad-tech see "Feast/Hopsworks" and shortlist.

### 4. Technical Direction

**Topics:**
- Feature store architectures: online vs offline, materialisation, freshness SLAs
- Point-in-time joins: how to avoid leakage
- Feature engineering frameworks: dbt + Feast, Spark + Feast
- Storage backends: Parquet/Iceberg, Redis, DynamoDB
- Feature versioning: schema evolution, backfills
- Access control: project-level isolation
- Monitoring: drift, freshness, missingness, online latency

### 5. Scope Boundaries
- **In scope:** 3-5 features, 2 model consumers, point-in-time demo, monitoring
- **Out of scope:** real-time sub-second features, multi-region

### 6. Final Deliverable Shape
Standard. Repo, live deployment, ADRs, Loom, resume.

---

## D2. Continuous Training Platform — Drift-Triggered Retraining

### 1. Business Scenario
You are the **MLOps Engineer at "InsureAI", an insurance claims prediction team**. Their claim-fraud model is 18 months old and accuracy has degraded 7 points. The data team retrains manually every quarter. You will build a **continuous-training platform** that detects drift, automatically retrains when drift crosses a threshold, and does a canary deploy with champion-challenger comparison.

### 2. Problem Statement
Build **AutoPilot ML** — a CT platform:
- **Drift detection:** Evidently AI or Alibi Detect — data drift, target drift, concept drift, prediction drift
- **Trigger logic:** configurable thresholds, suppression windows (don't retrain twice in 24h)
- **Retraining pipeline:** modular, parameterised, runs on Kubernetes (Argo Workflows or Kubeflow Pipelines)
- **Validation:** held-out + shadow comparison; gate promotion on metric thresholds
- **Model registry:** MLflow — staging → canary → production
- **Serving:** canary deploy with traffic split (e.g., 95/5), auto-rollback on degradation
- **Notifications:** Slack/email on retraining events, with a one-line reason
- **Audit log:** immutable record of every training, every promotion, every rollback

### 3. Why This Matters for Placements
Continuous training is the **end-state of MLOps**. Recruiters at any AI/ML-heavy team see this and know you can build production ML, not just notebooks.

### 4. Technical Direction

**Topics:**
- Drift detection: statistical tests (KS, PSI, Chi²), embedding-based drift, learned drift detectors
- Workflow orchestration: Argo, Kubeflow, Airflow
- Model registry: MLflow, Weights & Biases
- Deployment: canary, blue/green, shadow, A/B
- Auto-rollback: SLI/SLO-based, Prometheus-driven
- Feature store integration (reuse D1 components if doing both)
- Cost & schedule: don't retrain on noise; use suppression windows and statistical significance tests

### 5. Scope Boundaries
- **In scope:** full CT loop on a public dataset, drift detection, canary deploy, rollback
- **Out of scope:** multi-model orchestration, real-time features

### 6. Final Deliverable Shape
Standard. Repo, live CT loop demo (with simulated drift), ADRs, Loom, resume.

---

## D3. LLMOps Control Plane — Prompt, Provider, Cost, Safety

### 1. Business Scenario
You are the **LLMOps Engineer at "CoPilot Inc."**, where 12 product teams use LLMs in production. There is no central visibility: which prompts are running, which providers, what they cost, what's the latency, what % of outputs were PII-leaking? You will build a **control plane** that all teams pipe their LLM calls through, with unified observability, eval, cost, and safety.

### 2. Problem Statement
Build **LLMGov** — a central control plane:
- **Proxy/gateway:** every LLM call goes through it; supports OpenAI, Anthropic, Google, Azure, self-hosted
- **Prompt management:** versioning, A/B routing, prompt registry
- **Eval harness:** every call gets scored on 5 axes (correctness, toxicity, PII, format, latency)
- **Cost dashboard:** $ per team, per model, per prompt version
- **Latency dashboard:** p50/p95/p99 per provider
- **Safety:** PII redaction in inputs, output toxicity check (Perspective API or local model), jailbreak detection
- **Caching:** semantic cache (Redis with embeddings)
- **Failover:** if provider X is slow, auto-route to Y
- **Audit log:** full request/response (with PII redacted), immutable

### 3. Why This Matters for Placements
LLMOps is the **fastest-growing specialty in 2026**. Every AI-first company needs this. **Microsoft, Google, AWS, NVIDIA, Datadog, New Relic, Arize, LangChain, LlamaIndex** all have related products. Demonstrates systems thinking + LLM fluency.

### 4. Technical Direction

**Topics:**
- API gateway patterns: rate limiting, auth, routing
- LLM provider abstraction: litellm, portkey, OpenRouter patterns
- Observability: OpenTelemetry, Langfuse, Arize Phoenix, Helicone
- Eval: DeepEval, Ragas, Promptfoo, custom metrics
- Caching: exact + semantic
- Safety: regex, ML-based (Perspective, Detoxify, Llama Guard)
- Cost engineering: token counting, model cascading
- Reliability: circuit breakers, retries with backoff, fallback models

### 5. Scope Boundaries
- **In scope:** 2-3 LLM providers, full proxy, eval, cost/latency dashboards, basic safety
- **Out of scope:** model fine-tuning, training infrastructure

### 6. Final Deliverable Shape
Standard. Repo, live proxy demo, dashboards, ADRs, Loom, resume.

---

## D4. Model Risk & Governance — Regulated-Industry ML Audit

### 1. Business Scenario
You are the **Model Risk Manager at "CreditFirst", a NBFC** subject to RBI's Model Risk Management guidelines. Every model in production must have: a model card, bias/fairness audit, ongoing monitoring, explainability, and an annual review. You will build a **governance platform** that automates as much of this as possible, and that produces a regulator-ready report per model.

### 2. Problem Statement
Build **ModelGuard** — a governance platform:
- **Model registry:** every model (2-3 sample models) registered with metadata: owner, use case, training data, intended population
- **Auto model card generation:** from training pipeline + eval + monitoring
- **Bias & fairness:** 8 protected attributes (gender, age, location, income bracket, etc.), disparate impact ratio, equal opportunity difference, with bootstrap CIs
- **Explainability:** SHAP global + local, with a UI to inspect any decision
- **Monitoring:** drift, performance decay, calibration
- **Periodic review:** auto-generated quarterly report
- **Audit trail:** who trained, who approved, who deployed, who changed what, when
- **Document store:** versioned PDFs of model docs, approvals, sign-offs

### 3. Why This Matters for Placements
Governance is **the moat** for AI in regulated industries. NBFCs, banks, insurers, healthcare, pharma, edtech (with government contracts) all need this. Recruiters at **RBI, SEBI-regulated entities, banks, NBFCs, insurance, hospital systems** will see this and move you to the top of the pile.

### 4. Technical Direction

**Topics:**
- Model risk management frameworks: SR 11-7, RBI MRM, EU AI Act
- Fairness metrics: demographic parity, equalised odds, calibration across groups
- Explainability: SHAP, LIME, partial dependence, individual conditional expectation
- Model cards (Mitchell et al. format)
- Drift & performance monitoring
- Audit logging: append-only, signed
- Report generation: LaTeX, Quarto, or HTML

### 5. Scope Boundaries
- **In scope:** 2-3 sample models, full governance workflow, sample regulator report
- **Out of scope:** real RBI submission, e-signature integration

### 6. Final Deliverable Shape
Standard. Repo, governance UI, sample regulator report, ADRs, Loom, resume.

---

# SEGMENT 5 — LLM SYSTEMS & APPLIED GENAI

> Target roles: LLM Engineer · GenAI Engineer · AI Product Engineer · Prompt Engineer · Applied Research Engineer (GenAI)
> Target companies: GenAI-native startups (Sarvam, Krutrim, Yellow.ai, Haptik, Verloop, Fluid AI, KrishiHub, Observe.AI) · Microsoft Copilot ecosystem · Google Gemini for Workspace · Amazon Q · Adobe Firefly · Service-company GenAI studios (Accenture GenAI, Cognizant Neuro, EY.ai, KPMG Lighthouse, Deloitte AI) · OpenAI/Anthropic-adjacent

---

## E1. Agentic Research Analyst — Multi-Agent Equity Research

### 1. Business Scenario
You are the **Applied GenAI Engineer at "AlphaDesk", a wealth-tech startup** that provides retail investors with equity-research-style notes. Senior analysts take 4-8 hours per note. You will build a **multi-agent system** that takes a sector/company query and produces a cited research note in 5 minutes, with a human-in-the-loop review step.

### 2. Problem Statement
Build **AlphaAgents** — a multi-agent research system:
- **Orchestrator:** plans the research (which sub-questions, which sources, in what order)
- **Web researcher agent:** browses (Tavily / SerpAPI / Bing), fetches, summarises with citations
- **Financial data agent:** pulls from a financial API (yfinance, Alpha Vantage, or a stub) — fundamentals, ratios, recent filings
- **News agent:** sentiment + key events from the last 7 days
- **Writer agent:** synthesises a 4-6 page equity-research-style note: investment thesis, key risks, valuation summary, comparable companies, recommendation
- **Critic agent:** reviews the draft for unsupported claims, missing risks, factual errors
- **HITL checkpoint:** human analyst approves/edits before publication
- **Eval:** 20 sample queries with human-rated notes; measure factuality, completeness, actionability

### 3. Why This Matters for Placements
Multi-agent systems are the **flagship GenAI project of 2026**. Anyone interviewing at AI-first companies will ask about it. **OpenAI, Anthropic, Google DeepMind, Microsoft Research, every GenAI startup, every consulting firm's GenAI practice** is building these.

### 4. Technical Direction

**Topics:**
- Agent frameworks: LangGraph, AutoGen, CrewAI — pick one and justify
- Tool use: function calling, structured outputs, browser tools
- Planning: ReAct, Plan-and-Execute, Reflexion
- Memory: short-term (conversation), long-term (vector store of past research)
- Multi-agent patterns: orchestrator-worker, debate, supervisor
- Tracing: Langfuse, Arize Phoenix, OpenLLMetry
- Eval: factuality (RAGAS), completeness (LLM-as-judge), actionability (human)
- Safety: citation enforcement, hallucination guard, source diversity

### 5. Scope Boundaries
- **In scope:** 4-5 agents, full pipeline, eval, web UI
- **Out of scope:** real-time market data, paid APIs (use free tiers or stubs)
- **Bonus:** debate agent (bull vs bear), streaming UI

### 6. Final Deliverable Shape
Standard. Repo, live demo, eval report, ADRs, Loom, resume.

---

## E2. Domain Copilot — Vertical Assistant with Tool-Use

### 1. Business Scenario
You are the **AI Product Engineer at "MediNote", a health-tech startup** with a 3,000-doctor B2B platform. Doctors spend 2 hours/day on documentation. You will build a **medical-copilot** that listens to a doctor-patient conversation (or accepts a typed summary) and produces a structured SOAP note, suggests a differential diagnosis, and flags drug interactions. Must be safe, must be auditable, must be **physician-acceptable**.

### 2. Problem Statement
Build **MediMate** — a medical copilot (or pick another vertical: legal, KYC, code review — your choice, justify):
- **Inputs:** audio (Whisper) OR text
- **Structured output:** SOAP note, ICD-10 codes, suggested tests, drug interaction check (use a public API or stub)
- **Retrieval:** RAG over clinical guidelines (e.g., NICE, ICD-10, drug databases)
- **Tool use:** drug interaction lookup, ICD-10 suggestion, test recommendation
- **HITL:** doctor approves/edits before note is saved
- **Safety:** explicit refusal on diagnosis statements; flag when the case is outside scope
- **Eval:** 50 sample doctor-patient summaries, measure SOAP completeness, ICD-10 accuracy, hallucination rate

### 3. Why This Matters for Placements
Vertical copilots are where the money is. **Suki, Abridge, Nabla, DeepScribe, Augmedix (medical); Harvey, Spellbook (legal); Cognition (Devin), Cursor (code); Glean (enterprise search)** — all are high-growth GenAI companies. This pattern is universally applicable.

### 4. Technical Direction

Same as E1, with a focus on:
- Domain-specific RAG (clinical guidelines, drug databases)
- High-stakes safety: refusals, uncertainty, escalation
- Structured outputs (SOAP, ICD-10, JSON schemas)
- Eval with domain experts (or curated datasets)
- Observability + audit

### 5. Scope Boundaries
- **In scope:** one vertical (medical is recommended, but you can pick), full pipeline, eval, web UI
- **Out of scope:** real EHR integration, voice telephony

### 6. Final Deliverable Shape
Standard. Repo, live demo, eval report, ADRs, Loom, resume.

---

## E3. RAG over Enterprise Mess — Multi-Modal Dirty Data

### 1. Business Scenario
You are the **LLM Engineer at "BigCorp", an enterprise with 15 years of internal knowledge** scattered across Confluence, Slack, PDFs (some scanned), Word docs, Excel, emails, and a few wiki pages. The CEO wants a **"ask the company anything"** internal tool. Off-the-shelf RAG fails because: documents have tables, scans need OCR, Slack is threaded, some pages are duplicates with slight diffs, and knowledge is permissioned.

### 2. Problem Statement
Build **AskTheCompany** — enterprise RAG done right:
- **Sources:** at least 4 — Confluence-like pages (markdown), PDFs (text + scanned), Slack-like threads (JSON), Excel/CSV tables
- **Ingestion:** per-source parser, OCR where needed, table extraction
- **Chunking:** semantic + structural (heading-aware, table-aware)
- **Retrieval:** hybrid (BM25 + dense), re-ranking, query rewriting
- **Permissions:** documents have ACLs; user can only retrieve what they're allowed to see
- **Dedup:** near-duplicate detection across sources
- **Citations:** inline, with source type icon, page/section/row
- **Eval:** 100 Q&A pairs across difficulty (factual, multi-hop, table-lookup, opinion), measure accuracy + citation precision

### 3. Why This Matters for Placements
Enterprise RAG is the **most-hired GenAI skill** in 2026. **Glean, Notion AI, Slack AI, Microsoft Copilot, Google Gemini for Workspace, Box AI, Coda AI, plus every Indian GCC** is building or buying this.

### 4. Technical Direction

**Topics:**
- Document parsing: Unstructured.io, LlamaParse, Azure Document Intelligence
- Table extraction: TableTransformer, TAPAS, Markdownify
- OCR: Tesseract, PaddleOCR, EasyOCR, Azure Vision
- Hybrid retrieval: BM25 (Elasticsearch / OpenSearch) + dense (Qdrant / Weaviate / pgvector)
- Re-ranking: Cohere, bge-reranker, cross-encoder
- Query understanding: HyDE, query expansion, multi-query
- Permissions: ACL filtering at retrieval time
- Eval: RAGAS, TruLens, custom citation-precision metric

### 5. Scope Boundaries
- **In scope:** 4 source types, full pipeline, permissions, eval
- **Out of scope:** live connectors (use dumps)

### 6. Final Deliverable Shape
Standard. Repo, live demo, eval report, ADRs, Loom, resume.

---

## E4. Fine-Tuned Specialist Model — QLoRA on a Niche Domain

### 1. Business Scenario
You are the **Applied Research Engineer at "CodeCraft", a code-review startup**. The base Llama-3-3-70B is great at general code review but misses framework-specific patterns (e.g., Spring Boot anti-patterns, React Server Components pitfalls). You will **fine-tune a small open model** (3B-8B) to beat GPT-4o on this niche eval, while being 10x cheaper and 5x faster to run.

### 2. Problem Statement
Build **SpecialistLM** — a fine-tuned small LLM:
- **Domain:** pick ONE — code review in a specific framework, legal judgment summarisation, customer-support response drafting, Indian regulatory Q&A, medical history taking
- **Base model:** Llama-3.2-3B / Phi-3.5-mini / Qwen2.5-7B / Gemma-2-9B
- **Method:** QLoRA (4-bit base + LoRA adapters), with full hyperparameter sweep
- **Data:** curate or generate 5,000-10,000 high-quality (input, ideal-output) pairs — use GPT-4o to bootstrap, then human-filter a subset
- **Eval:** 200 held-out test cases, with both automated metrics (LLM-as-judge) and a small human-rated set
- **Comparison:** base model vs your model vs GPT-4o on the same eval — show your model wins on your niche
- **Serving:** vLLM or TGI, with cost/latency comparison vs GPT-4o
- **Reproducibility:** a single command to retrain from scratch

### 3. Why This Matters for Placements
Fine-tuning is a **core applied-research skill**. Recruiters at AI labs, AI startups, and AI-forward teams see "I fine-tuned a model that beats GPT-4o on X" and call you.

### 4. Technical Direction

**Topics:**
- Fine-tuning fundamentals: SFT, LoRA, QLoRA, full FT
- Data curation: filtering, deduplication, quality scoring
- Training: HuggingFace TRL, Axolotl, LLaMA-Factory
- Eval: LLM-as-judge, human eval, benchmark design
- Serving: vLLM, TGI, SGLang, latency/cost tradeoffs
- Quantisation: GGUF, AWQ, GPTQ
- Safety: don't degrade alignment, evaluate for regressions

### 5. Scope Boundaries
- **In scope:** 5-10k examples, QLoRA, full eval, serving comparison
- **Out of scope:** pre-training from scratch, RLHF, multi-modal

### 6. Final Deliverable Shape
Standard. Repo, eval report, serving comparison, ADRs, Loom, resume.

---

# SEGMENT 6 — CLOUD-NATIVE & PLATFORM ENGINEERING

> Target roles: Cloud Engineer · DevOps Engineer · SRE · Platform Engineer · Cloud Architect (entry)
> Target companies: AWS / Azure / GCP partner companies · All service-company DevOps tracks · Fintech platform teams · GCCs · DevOps startups (Hasura, Porter, InfraCloud equivalents)

---

## F1. Multi-Tenant SaaS Backbone

### 1. Business Scenario
You are the **Platform Engineer at "B2B SaaS Co."** building the next Notion-for-X. Multi-tenancy is non-negotiable: each customer's data must be isolated, each customer's admins manage their own users, and usage is metered for billing. You will build the **reference multi-tenant backbone** that any B2B SaaS product can fork.

### 2. Problem Statement
Build **TenantCore** — a multi-tenant SaaS backbone:
- **Tenant isolation:** 2 strategies implemented — schema-per-tenant (Postgres) AND row-level security; a config flag to switch
- **Auth:** Keycloak (self-hosted) OR Auth0 OR Clerk — tenant-aware (each tenant has its own realm/org)
- **Authorisation:** RBAC + ABAC, tenant-scoped
- **Per-tenant database routing:** middleware that picks the right DB connection based on tenant
- **Usage metering:** every billable event counted, persisted, aggregated
- **Billing webhook:** emits `invoice.created` events to a Stripe stub (or Razorpay stub)
- **Observability:** per-tenant logs, metrics, traces
- **Self-serve onboarding:** a new tenant can sign up, get isolated, and start using the API in 5 minutes
- **IaC:** Terraform/Pulumi that provisions the whole thing

### 3. Why This Matters for Placements
Multi-tenancy is the **#1 architecture question** for B2B SaaS engineers. **Freshworks, Zoho, Chargebee, Razorpay, Chargebee, CleverTap, MoEngage, and every B2B SaaS** interviews on this.

### 4. Technical Direction

**Topics:**
- Multi-tenant patterns: shared DB shared schema, shared DB separate schema, separate DB
- Row-level security (Postgres RLS)
- AuthN/AuthZ: OIDC, SAML, OAuth, RBAC, ABAC
- API gateway: Kong, Apigee, AWS API Gateway
- Metering & billing: event design, idempotency, aggregation
- Observability per tenant: log tagging, metric labels, trace propagation
- IaC: Terraform, Pulumi
- Cost: per-tenant resource budgeting

### 5. Scope Boundaries
- **In scope:** 2 isolation strategies, full auth, metering, IaC, demo with 2-3 tenants
- **Out of scope:** real Stripe integration, full self-serve UI

### 6. Final Deliverable Shape
Standard. Repo, live deployment, ADRs, Loom, resume.

---

## F2. Event-Driven Order System — Saga on Kubernetes

### 1. Business Scenario
You are the **Platform Engineer at "CartCo" (from B1)** but on the transactional side: order placement, payment, inventory, shipping, notification — all distributed, all needing exactly-once semantics. You will build an **event-driven order system** using the saga pattern, with outbox, idempotency, and chaos testing.

### 2. Problem Statement
Build **OrderSaga**:
- **Order service:** accepts order, writes to outbox, emits `OrderCreated`
- **Payment service:** consumes, processes payment, emits `PaymentSucceeded` or `PaymentFailed`
- **Inventory service:** reserves stock, emits `InventoryReserved` or compensating `ReleaseStock`
- **Shipping service:** schedules, emits `ShipmentScheduled`
- **Notification service:** sends email/SMS (stubbed)
- **Saga orchestrator:** tracks state machine, fires compensations on failure
- **Outbox pattern:** for at-least-once + exactly-once via dedup keys
- **Idempotency:** every consumer checks `event_id` in a dedup store
- **Chaos testing:** kill 1 service mid-saga; verify compensation + eventual consistency
- **Observability:** full distributed trace per order, with saga state visible

### 3. Why This Matters for Placements
Saga + outbox + idempotency is the **bread-and-butter of distributed systems interviews**. **Every product company with microservices asks this.**

### 4. Technical Direction

**Topics:**
- Saga pattern: orchestration vs choreography
- Outbox pattern: transactional outbox, CDC-based relay
- Idempotency: dedup keys, idempotency keys in APIs
- Kafka: topics, partitioning, exactly-once
- Distributed tracing: OpenTelemetry, Jaeger/Tempo
- Chaos engineering: Litmus, Chaos Mesh
- Kubernetes: deployments, services, ingress, configmaps, secrets
- Resilience: retries with backoff, circuit breakers, bulkheads, dead-letter

### 5. Scope Boundaries
- **In scope:** 4-5 services, full saga, chaos demo, tracing
- **Out of scope:** real payment gateway, multi-region

### 6. Final Deliverable Shape
Standard. Repo, live k8s deployment, chaos demo video, ADRs, Loom, resume.

---

## F3. Cost-Optimised Data Lake on a Shoestring (<₹500/month)

### 1. Business Scenario
You are the **Cloud Engineer at "BootStrap Co.", a 3-person startup** that needs to ingest, store, and query 100GB of data monthly but has a near-zero cloud budget. You will build a **data lake on AWS free tier** (or equivalent) that handles 100GB+ ingest, supports SQL queries, with a monthly bill < ₹500.

### 2. Problem Statement
Build **PennyLake**:
- **Storage:** S3 with lifecycle policies (Glacier after 30d)
- **Ingest:** Lambda + EventBridge for scheduled CSV/JSON drops
- **Catalog:** Glue Crawler + Glue Catalog (or Lake Formation)
- **Query:** Athena (serverless)
- **Transform:** Glue jobs OR dbt + Athena
- **Orchestration:** Step Functions OR EventBridge scheduler
- **Cost engineering:** partition pruning, columnar formats (Parquet), compression, lifecycle policies, query result caching
- **Dashboard:** QuickSight (free tier) OR Streamlit
- **Cost dashboard:** real-time $ burn, with projections

### 3. Why This Matters for Placements
"Cost-optimised cloud architecture" is the **#1 cloud interview question in 2026**, especially at early-stage startups. Demonstrates you understand cloud economics, not just cloud services.

### 4. Technical Direction

**Topics:**
- AWS S3 storage classes, lifecycle policies
- Lambda cost model, concurrency limits
- Athena pricing: per-TB scanned, partition pruning
- Glue: jobs, crawlers, Data Catalog
- Parquet + Snappy: columnar compression
- Cost monitoring: Cost Explorer, billing alarms
- IaC: Terraform, AWS CDK
- Security: IAM least-privilege, KMS, S3 encryption

### 5. Scope Boundaries
- **In scope:** 100GB synthetic data, full pipeline, cost dashboard, bill < ₹500/month
- **Out of scope:** real-time, multi-account

### 6. Final Deliverable Shape
Standard. Repo, live AWS deployment, cost dashboard, ADRs, Loom, resume.

---

## F4. GitOps Reference Platform

### 1. Business Scenario
You are the **DevOps Engineer at "Platform Co."** building the internal developer platform. Every team needs: a Kubernetes cluster, secrets, observability, CI/CD, and ingress. You will build a **GitOps-managed reference platform** that any new team can adopt in 1 day.

### 2. Problem Statement
Build **GitOps Platform**:
- **Cluster:** kind/k3d for local OR EKS/GKE free tier
- **GitOps:** ArgoCD OR Flux — pick one, justify
- **Secrets:** Sealed Secrets OR External Secrets Operator
- **Ingress:** ingress-nginx + cert-manager + Let's Encrypt
- **Observability:** Prometheus + Grafana + Loki + Tempo (or a managed alternative)
- **CI/CD:** GitHub Actions or Tekton — building images, signing, deploying
- **App of apps:** a single repo that deploys the whole platform
- **Disaster recovery:** destroy cluster → re-apply → 100% recovered

### 3. Why This Matters for Placements
GitOps is **standard** in 2026. Any platform/devops/SRE interview will probe it. **All major product companies, all banks' platform teams, every DevOps-first startup.**

### 4. Technical Direction

**Topics:**
- GitOps principles: declarative, versioned, automated, continuously reconciled
- ArgoCD: app of apps, sync windows, health checks, rollbacks
- Secrets management: Sealed Secrets, External Secrets, HashiCorp Vault
- Ingress + TLS: cert-manager, Let's Encrypt, ingress-nginx
- Observability stack: Prometheus, Grafana, Loki, Tempo, OpenTelemetry
- CI/CD: image build, sign (cosign), push, deploy
- Disaster recovery: Velero for k8s backups

### 5. Scope Boundaries
- **In scope:** local kind/k3d cluster with full stack, GitOps repo, DR demo
- **Out of scope:** multi-cluster, production HA

### 6. Final Deliverable Shape
Standard. Repo, live cluster demo, DR demo video, ADRs, Loom, resume.

---

# Final Note

This compendium is the **map**. The intern is the **journey**. The destination is the same for everyone: a portfolio piece that, when a recruiter opens it, makes them put your resume on the shortlist pile.

Pick. Read. Build. Ship.

See you on 22 June.
