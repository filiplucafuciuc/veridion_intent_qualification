# Intent Qualification System

## Status

This document is being written alongside the implementation. It records
observations and decisions as they are made, rather than describing an
idealized system after the fact.

## 1. Problem framing

The task is not ordinary text similarity. A relevant company must satisfy the
constraints implied by a user request, which may include:

- structured attributes such as country, public status, founding year,
  employee count, and revenue;
- industry and offering requirements;
- the role a company plays, such as manufacturer, supplier, operator, or
  software provider;
- relationships in a broader business context, such as supplying packaging to
  cosmetics brands.

The system therefore needs to distinguish between:

1. **satisfied constraints**;
2. **explicitly violated constraints**; and
3. **unknown constraints caused by missing data**.

Missing data should not automatically be interpreted as a negative answer.
However, an unknown constraint should reduce confidence and should not outrank
strongly evidenced matches without other supporting evidence.

## 2. Dataset investigation

### 2.1 Initial observations

The supplied dataset contains 477 JSONL records. Every record has the same
top-level field names, but some values are missing and some nested values have
inconsistent representations.

The main fields are:

`website`, `operational_name`, `year_founded`, `address`, `employee_count`,
`revenue`, `primary_naics`, `secondary_naics`, `description`,
`business_model`, `target_markets`, `core_offerings`, and `is_public`.

The initial profiling command is:

```bash
python3 scripts/profile_data.py companies.jsonl
```

Its machine-readable output is stored in
[`reports/data_profile.json`](reports/data_profile.json).

The normalization tests can be run with:

```bash
python3 -m pytest -q tests/test_data.py
```

The current result is `3 passed`. This refers to three automated test
functions, not to three companies or three successful queries:

1. loading all 477 records and preserving source identity;
2. normalizing both nested-value representations;
3. preserving missing numeric values as unknown.

The syntax-only check used during development was:

```bash
python3 -m py_compile src/data.py tests/test_data.py scripts/profile_data.py
```

These commands are kept here so the analysis and validation steps are
reproducible.

The structured baseline can be run as a module from the project root:

```bash
python3 -m scripts.run_structured \
  'Public software companies with more than 1,000 employees.' \
  --limit 10
```

Single quotes are intentional in shell examples when a query contains a
currency symbol such as `$50`; otherwise a shell may interpret `$50` as
variable expansion before Python receives the query.

### 2.2 Data quality findings

The first profile found:

- 477 parseable records and no malformed JSON lines;
- `employee_count` missing for 188 records;
- `year_founded` missing for 131 records;
- `revenue` missing for 93 records;
- `secondary_naics` missing for 466 records;
- `is_public` is present for every record;
- `description`, `business_model`, `target_markets`, and `core_offerings`
  are present for every record;
- 413 records store `address` and `primary_naics` as dictionaries, while 64
  store them as strings containing serialized Python dictionary syntax;
- the dataset covers many countries, with the largest groups in the United
  States, Switzerland, France, China, Sweden, the United Kingdom, Norway,
  Denmark, Spain, Finland, and Romania;
- there are repeated websites and operational names. These are not removed
  automatically because they may represent different geographic records or
  duplicate observations that need entity-resolution analysis.

The inconsistent nested representations are a correctness issue, not merely a
formatting issue. Location and NAICS filtering would otherwise behave
differently for different rows. The implementation will normalize both actual
dictionaries and serialized mappings while retaining the original values.

There are not two different business schemas for these fields. There are two
raw encodings of the same intended concepts:

```python
# native dictionary
{"country_code": "de", "town": "Berlin"}

# string containing a Python dictionary literal
"{'country_code': 'de', 'town': 'Berlin'}"
```

The normalizer accepts both and exposes one internal `Location` or `Naics`
type to the rest of the system.

### 2.3 Initial design implications

The dataset supports a hybrid approach:

- deterministic evaluation is appropriate for numeric and boolean constraints;
- NAICS labels, offerings, target markets, and descriptions provide useful
  industry and semantic evidence;
- missing numeric data requires tri-state constraint handling;
- the small dataset size allows a transparent in-memory implementation first;
- duplicate-looking records require stable record identifiers and should not
  be silently deduplicated before their differences are understood.

## 3. Normalization layer

The raw dataset is loaded through
[`src/data.py`](src/data.py). The normalizer makes nested values consistent
without changing the source data:

- native dictionaries and serialized Python mappings are both accepted;
- country codes are normalized to lower case and mapped to country names;
- NAICS values become typed `Naics` records;
- locations become typed `Location` records;
- list-valued fields become immutable tuples;
- numeric missing values remain `None`, representing unknown rather than zero;
- every row receives a stable line-based `record_id`, so duplicate-looking
  companies are not silently merged;
- a lower-case `search_text` is built from the company name, NAICS labels,
  description, business models, target markets, and offerings.

The source line is retained because it makes debugging and result auditing
possible. The normalization tests cover both representations of nested values,
record identity, and missing numeric data.

### 3.1 Geographic scope and regions

The dataset stores a country code for each address, not a canonical
continent/region field. Therefore a query such as "in Scandinavia" cannot be
handled by comparing the query string with one `country_code`.

The query interpreter will need an explicit region vocabulary, for example:

```text
Scandinavia -> Denmark, Norway, Sweden
Nordics -> Denmark, Finland, Iceland, Norway, Sweden
Europe -> an explicit country set
```

This is query-side expansion, not a change to the company data. It must be
documented and tested because "Scandinavia" and "Nordics" are not universally
identical terms. The current location normalizer deliberately handles only
country-level normalization; region expansion belongs in query parsing, where
it can be inspected and audited.

## 4. Design evolution

This section will be updated after each experiment. The current starting
hypothesis is:

1. profile and normalize the data;
2. implement transparent structured and lexical baselines;
3. add semantic retrieval only if the baseline analysis shows a recall gap;
4. combine retrieval with constraint-aware ranking;
5. reserve expensive reasoning for genuinely ambiguous candidates.

The reason for delaying expensive components is that the problem explicitly
requires balancing accuracy, speed, cost, and scalability. A component should
be added only when an observed error demonstrates why it is needed.

## 5. First structured baseline

The first baseline is implemented in
[`src/query.py`](src/query.py) and [`src/structured.py`](src/structured.py).
It intentionally avoids embeddings and external APIs.

The parser extracts:

- country names and explicit region expansions;
- numeric comparisons for employees, revenue, and founding year;
- public, B2B, SaaS, and startup attributes;
- a small canonical industry vocabulary;
- the manufacturer role.

The scorer evaluates each applicable constraint as `satisfied`, `violated`, or
`unknown`. A company with an explicit contradiction is rejected, a company
with missing evidence is marked possible, and a company satisfying all
applicable constraints is a match. The score is an explainable aggregate:
positive evidence adds one unit, contradiction subtracts two, and unknown
evidence subtracts half a unit.

This is a baseline, not the final ranking model. For example, it does not yet
understand that "providing HR solutions" is a target-market relationship, and
it cannot reliably infer "competing with traditional banks" or "using Shopify".
Those limitations are useful evidence for the next retrieval layer.

The all-query report is generated with:

```bash
python3 -m scripts.evaluate_structured --limit 10
```

and stored in
[`reports/structured_baseline.json`](reports/structured_baseline.json).

The first run also exposed implementation issues that were fixed before
continuing:

- "Logistic" and "logistics" needed an explicit alias;
- "Europe" and "Scandinavia" needed visible country-set expansion;
- the manufacturer role had to affect the score rather than only being
  extracted;
- shell examples containing `$50` must use single quotes so the shell does
  not expand the currency expression.

### 4.1 Baseline limitations

The structured baseline is intentionally limited:

- the region vocabulary is manually defined (`Scandinavia`, `Nordics`, and
  `Europe`), so it must be maintained as geographic policy changes or as the
  product supports more regions;
- the current country expansion is not a full geopolitical authority and may
  omit edge cases or disputed interpretations;
- only a small set of industry aliases is available;
- the manufacturer check relies primarily on the `business_model` field;
- business relationships such as "competes with banks" are not inferred;
- platform usage such as "uses Shopify" is not present as a structured
  constraint;
- startup is currently a transparent year-based heuristic, not a verified
  legal or funding classification;
- duplicate-looking source records are retained, so the ranking can show the
  same operational name more than once.

These are known limitations, not hidden assumptions. The structured report is
preserved as an independent artifact so later methods can be compared against
this exact starting point.

## 6. Lexical retrieval baseline

The next experiment is a dependency-free TF-IDF retrieval baseline in
[`src/lexical.py`](src/lexical.py). It indexes the normalized `search_text`
for every company and compares it with the query using cosine similarity.
This method is useful for recall: it can find companies whose descriptions
share relevant terms even when a structured parser has not recognized every
constraint.

It is not the final qualification decision. A lexical match can still confuse
a company with its customer, or a company that mentions an industry with a
company that actually operates in that industry. Therefore each lexical result
also carries the structured result for later comparison.

The baseline can be run with:

```bash
python3 -m scripts.run_lexical \
  'Companies that could supply packaging materials for a direct-to-consumer cosmetics brand' \
  --limit 10
```

The expected next experiment is to compare lexical and structured top results
for the relationship-heavy queries and record concrete false positives.

The lexical report is generated with:

```bash
python3 -m scripts.evaluate_lexical --limit 10
```

and stored separately in
[`reports/lexical_baseline.json`](reports/lexical_baseline.json).

The first lexical inspection produced a useful concrete observation for
packaging retrieval: the top results were mostly packaging-related companies,
which is better recall than a strict industry-only filter. However, the method
does not prove that the company is a suitable supplier for cosmetics brands.
It can also rank incomplete records, such as a company with no operational
name, because the text score is independent of data completeness. This is
evidence for a later role-aware and data-quality-aware ranking stage, not a
reason to discard lexical retrieval altogether.

The all-query report exposed additional concrete failures:

- for the construction query restricted to the United States, a Swiss
  pharmaceutical company appeared near the top because it shared generic
  vocabulary; lexical retrieval does not enforce hard geography;
- for the fintech query, a French food company appeared near the top because
  general business words overlap; lexical similarity is not evidence of a
  fintech role;
- for the e-commerce query, the lexical result did not establish Shopify
  usage, because platform usage is not encoded in the current company fields;
- for the Scandinavia query, a company in Finland was highly lexical despite
  Finland not belonging to the narrow three-country definition used here.

These examples show why the lexical baseline should be used for candidate
recall, not as the final qualifier. The hybrid stage must apply structured
constraints after retrieval and must score company role and evidence fields
separately from generic text overlap.

## 7. Hybrid ranking

The hybrid implementation is in
[`src/hybrid.py`](src/hybrid.py). It uses the lexical index to retrieve a
bounded candidate pool, then reranks those candidates using:

```text
final_score =
    0.35 * lexical_score
  + 0.65 * structured_evidence_score
  - contradiction penalties
```

The weights are an initial, explicit hypothesis rather than learned
parameters. They give structured evidence more influence because a lexical
match should not override an explicit user constraint.

The hybrid stage distinguishes:

- **hard contradictions**: wrong country, wrong numeric threshold, or wrong
  public status; these are rejected;
- **soft/semantic contradictions**: weak industry or role evidence; these are
  retained as `possible` so recall is not destroyed by an imperfect vocabulary;
- **unknown evidence**: missing fields reduce the score and confidence but do
  not become false automatically.

Each result retains lexical score, evidence score, confidence, matched
constraints, unknown constraints, and violated constraints. This makes the
ranking auditable rather than presenting one unexplained number.

The report is generated with:

```bash
python3 -m scripts.evaluate_hybrid --limit 10 --candidate-limit 100
```

and stored in
[`reports/hybrid_baseline.json`](reports/hybrid_baseline.json).

The candidate limit is a scalability control. With 477 records, 100
candidates is inexpensive; at larger scale the lexical index would be
persisted and the same reranking stage could operate on a much smaller
candidate set.

### 7.1 Hybrid observations and current limitations

The hybrid report has no top-10 result marked `match` while also carrying a
hard contradiction. This is the intended safety property: lexical relevance
cannot override an explicit country, numeric, or public-status constraint.

The report also exposed limitations that remain:

- duplicate-looking source records still appear more than once;
- the current industry vocabulary can make a company a `match` when it only
  has weak textual evidence for a broad category;
- `Shopify or similar platforms` is not confirmed by the available fields;
- `fast-growing` and `competing with traditional banks` are not yet modeled
  as separate evidence requirements;
- supplier relationships and target-market relationships need field-aware
  evidence instead of one combined text score;
- confidence is currently a calibrated heuristic, not a probability learned
  from labeled outcomes.

The evaluation also led to a targeted refinement: merely mentioning banking
is not evidence that a company competes with traditional banks. The
relationship check therefore requires competition language (or an explicit
traditional-bank relationship) rather than accepting the generic word
`banking`.

This is an important distinction in the evolution of the system: the hybrid
stage prevents objective contradictions, but it does not yet solve every
semantic qualification problem. The next stage is evaluation and error
analysis, followed by targeted improvements rather than adding complexity
without evidence.

## 8. Evaluation methodology

The challenge supplies 12 queries but no relevance labels. We therefore use a
two-part evaluation:

1. **objective checks**, such as parsing correctness and hard-constraint
   violations;
2. **human review**, with a small graded reference set and written evidence.

The comparison artifact is generated with:

```bash
python3 -m scripts.build_comparison --limit 5
```

and stored in
[`reports/method_comparison.json`](reports/method_comparison.json).

The review schema is in
[`reports/manual_review.json`](reports/manual_review.json). We use:

```text
2 = strong match
1 = plausible/partial match
0 = irrelevant or contradicted
```

Reviewers must cite only evidence present in the company record. This prevents
the evaluation from becoming an untraceable opinion, especially for queries
containing terms such as "could supply", "fast-growing", or "similar
platforms".

The review is intentionally kept separate from generated ranking reports.
This preserves the distinction between:

- what the system produced;
- what a reviewer judged;
- why the reviewer made that judgment.

Objective checks can be run with:

```bash
python3 -m scripts.evaluate_objective --report reports/hybrid_baseline.json
```

These checks report hard-constraint violations and duplicate names in the
review window. They do not claim that every lexical or semantic match is
correct; that requires the written manual labels.

The current review subset contains explicit evidence for representative
results in
[`reports/manual_review.json`](reports/manual_review.json). Its metrics are
generated with:

```bash
python3 -m scripts.evaluate_manual
```

The review currently includes 14 records. It is intentionally a small,
auditable sample, not a complete answer key. In particular, a label of `1`
captures candidates that are useful but lack evidence for a qualitative
condition such as growth, bank competition, or Shopify usage.

The resulting `review_precision=1.000` must not be interpreted as production
precision. The reviewed records were selected to cover representative strong
matches and known ambiguity cases, rather than sampled randomly from every
returned result. The useful conclusions from this audit are:

- all 14 reviewed records were at least plausible;
- 11 had strong evidence and 3 were deliberately marked partial because a
  qualitative requirement was not observable;
- the audit found concrete model issues and drove the field-aware industry,
  supplier-role, platform, growth, and competition changes;
- objective hard-constraint checks cover all 120 top-10 results separately.

This separation prevents a small qualitative audit from being presented as a
statistically reliable benchmark.

## 10. Ambiguity detection

Before introducing an optional LLM, the project now detects ambiguity using
signals available in the current 477-record dataset. The detector is in
[`src/ambiguity.py`](src/ambiguity.py) and reports:

- query complexity from relational language and qualitative requirements;
- unknown constraints;
- disagreement between lexical and structured evidence;
- contextual industry evidence that appears only in target markets;
- small score margins;
- incomplete company records.

The report is generated with:

```bash
python3 -m scripts.evaluate_ambiguity --top-k 10 --candidate-limit 100
```

and stored in
[`reports/ambiguity_report.json`](reports/ambiguity_report.json).

This is intentionally a bounded review queue, not an LLM call. On this
dataset, it lets us inspect how many candidates would be sent to a human or
an optional resolver and why. A future LLM adapter should receive only that
queue, preserve hard constraints, and return structured evidence; the core
pipeline remains runnable without an API key.

The current report shows that structured queries produce small queues, while
queries with unobservable requirements produce much larger ambiguity pools:
Shopify usage is unknown for every candidate because the dataset has no
technology-stack field, and growth/bank competition are unknown for the
fintech query because there is no historical series or explicit relationship
field. The report therefore limits the proposed review queue to five
candidates per query while retaining the full ambiguity count for monitoring.
This is a useful result: the detector identifies when the missing data itself,
rather than the ranking model, is the source of uncertainty.

## 9. Error analysis

The baseline reports and manual audit produced the following concrete error
patterns:

1. **Customer industry versus company industry.** CBRE Romania serves
   logistics customers, but its primary activity is real estate. Treating
   `target_markets` as sufficient industry evidence incorrectly promoted it
   for a logistics-company query. The scorer now treats target-market-only
   evidence as `unknown`.
2. **Lexical geography errors.** The lexical baseline ranked a Swiss
   pharmaceutical company for a US construction query. Hybrid ranking removes
   this class of error by applying location as a hard constraint.
3. **Role ambiguity.** A company can mention cosmetic packaging without being a
   packaging supplier. The hybrid stage now checks manufacturing, wholesale,
   distribution, packaging offerings, and target markets separately, while
   still treating the relationship as an inference.
4. **Unavailable technology evidence.** E-commerce evidence does not establish
   Shopify usage. The result is now `possible` unless the company record
   explicitly mentions Shopify.
5. **Unavailable historical evidence.** "Fast-growing" cannot be confirmed
   from one current employee or revenue value. Without a time series it is
   marked unknown rather than inferred from company size.
6. **Duplicate source observations.** The top results include repeated
   operational names. We retain them for traceability, but a production
   system would need entity resolution or a configurable grouping policy.

These are not all solved by one model. Some are algorithmic and can be
improved with field-aware scoring; others require additional data.

## 10. Trade-offs

The design prioritizes correctness for explicit constraints, explainability,
and a dependable offline core over maximum semantic coverage.

### Accuracy

Hard constraints are evaluated deterministically. This avoids returning a
semantically similar but objectively invalid company. The trade-off is that
the system can be conservative when evidence is missing or when a relationship
is only implied.

### Speed and cost

TF-IDF retrieval and structured scoring are local and inexpensive. Only a
bounded candidate pool is reranked. We deliberately did not make an LLM
request part of the core path because the dataset does not justify the cost,
latency, or operational dependency. A future selective reranker could be
added for high-value ambiguous cases.

### Simplicity and ownership

The parser, scoring rules, and explanations are inspectable and testable.
This is preferable to a larger opaque stack for a 477-record challenge
dataset. The trade-off is less robust synonym and relationship understanding
than a trained or foundation model.

### Confidence

Confidence is an evidence heuristic, not a calibrated probability. It should
be calibrated against production labels before being used for automated
decisions.

## 11. Scaling and production design

For 100,000 companies per query, I would preserve the same logical stages but
change the storage and retrieval implementation:

1. normalize and validate records in an offline ingestion job;
2. store structured fields in indexed columns, including country, NAICS,
   public status, and numeric ranges;
3. persist an inverted lexical index or use BM25 rather than rebuilding the
   TF-IDF index for every request;
4. retrieve candidates through a union of structured filters and lexical or
   vector search;
5. rerank only the top few hundred candidates;
6. cache parsed queries, region expansions, and repeated retrieval results;
7. deduplicate or group entities only with a documented identity policy;
8. version the geography and industry vocabularies.

For millions of records, I would also add approximate-nearest-neighbor
retrieval for semantic recall, sharding, query-result caching, and an
asynchronous ambiguity queue. The hard-constraint evaluator would remain
close to the final ranking stage so approximate retrieval could not silently
reintroduce invalid candidates.

## 12. Failure modes and monitoring

The system can produce confident but incorrect results when:

- a description contains an industry term that describes a customer rather
  than the company;
- a broad alias maps an unrelated NAICS category into an industry;
- a manually defined region has the wrong policy definition;
- a duplicate record has stale or conflicting values;
- the dataset lacks evidence for a qualitative condition but the scoring
  weights are too generous;
- a company description is templated, noisy, or copied from another entity.

Production monitoring should include:

- hard-constraint violation rate;
- percentage of results marked `possible`;
- distribution of confidence by query type;
- duplicate rate in top-k results;
- missing-field rates and schema drift;
- disagreement between lexical and structured signals;
- reviewer acceptance rate and false-positive rate on sampled traffic;
- latency, candidate-pool size, and cache hit rate.

Alerts should be triggered by schema changes, sudden shifts in country or
industry distributions, increases in hard violations, and drops in reviewer
acceptance.

## 13. Evaluation ground truth

The 12 supplied queries will be evaluated using:

- hard-constraint violation checks;
- Precision@K on manually reviewed results;
- ranking quality such as NDCG@K where graded relevance labels are available;
- latency and candidate-count measurements;
- query-by-query error analysis.

The exact metrics and results will be added after the baselines and final
ranking pipeline are implemented.


The brief provides 12 queries but does not provide a labeled file containing
the correct companies for each query. We therefore cannot honestly claim an
objective recall score yet.

After the first baselines exist, we will create a small human-reviewed
reference set:

1. run each query with each baseline;
2. review the top results and a sample of borderline results;
3. assign graded labels such as `2 = strong match`, `1 = plausible/partial`,
   and `0 = irrelevant`;
4. record evidence and disagreements rather than hiding them;
5. compare methods using Precision@K and, where enough graded labels exist,
   NDCG@K.

Manual labels are not perfect ground truth. They are a transparent evaluation
protocol for a challenge that supplies queries but no answer key. Hard
constraint violations can still be measured objectively, such as returning a
company in France for a query explicitly restricted to Switzerland.
