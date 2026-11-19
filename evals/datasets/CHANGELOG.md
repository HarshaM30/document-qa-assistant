# Eval dataset changelog

Every report records the dataset as `<file>@<first 8 hex of its SHA-256>`, so a report can
always be matched to the exact dataset it was produced from. Any edit to a dataset file
changes that hash; substantive changes get a new file (`qa_v2.jsonl`) and an entry here.

## dev_v1 (2026-11-19)

25 tuning questions for Milestone 5b, in the same categories and proportions as qa_v1
(6 factual, 6 table, 4 yoy, 4 cross-company, 5 unanswerable). Retrieval changes are chosen on
this set only; qa_v1 stays the held-out test set. No dev question or source quote repeats a
qa_v1 one (checked in the unit tests), though some dev quotes come from the same filings and
tables. All 25 quotes pass `eval verify`; `eval xbrl` reports 10 matches, 17 explained, 0
unexplained. Under the naive index one source (DY01) has no gold chunk, so naive scores on
the dev set are slightly understated.

## qa_v1 (2026-11-17)

50 questions over the 15 locked 10-K filings (`data/filings.lock.json`):

| Category | Count | What it tests |
|---|---|---|
| `factual` | 12 | Facts stated in prose (headcount, segments, fiscal year, capital return) |
| `table` | 12 | One number from a financial table |
| `yoy` | 8 | Two fiscal years of the same metric, from one or two filings |
| `cross_company` | 8 | The same metric for two companies, only for fiscal years both have filed |
| `unanswerable` | 10 | Companies, years, forecasts, or details that no filing contains |

- Every answerable question has one or more sources (`doc`, `section`, `quote`). Each
  quote appears verbatim, after whitespace and quote-style normalization, in the stated Item
  of the parsed filing, with tables rendered as `Row | Column: value` lines
  (`make eval-verify`).
- Numeric answers list each required value with its unit. Values with a non-dimensional
  XBRL fact carry its concept and match SEC `companyfacts` (`make eval-xbrl`). The rest
  (segment and product-line figures, ratios, headcounts, rounded MD&A figures) carry an
  `xbrl_note` explaining why they can't be checked that way.
- Fixed while authoring: J&J tags revenue as
  `RevenueFromContractWithCustomerExcludingAssessedTax` (not `Revenues`) and R&D as
  `ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost`.
