# CaseGraph — Evaluation

This document describes the ground-truth evaluation harness built for CaseGraph,
the bugs it surfaced, the fixes applied, and the final measured accuracy of the
system. All numbers below were produced by running the actual deployed
pipeline (`/extract`, `/contradict`, `/query`) against a synthetic test corpus.

## Methodology

1. **Corpus**: 50 synthetic FIR documents (`generated_corpus.json`), each
   following the exact structural template CaseGraph's ingestion pipeline
   expects (Complainant Details / Accused Details / Incident Details /
   Witnesses / Recovered Evidence sections), generated from a structured
   ground-truth table (`corpus_data.py`).
2. **Planted contradictions**: 4 deliberate conflicts were embedded across the
   corpus to test contradiction detection:
   - **Attribute conflict** — Vikram Reddy's age recorded as 34 in most FIRs,
     32 in FIR104/FIR117.
   - **Attribute conflict** — Ravi Kumar's mobile number recorded as
     9876543210 in most FIRs, 9112233445 in FIR106.
   - **Relation conflict** — Vikram Reddy fled in a Hyundai i20 in several
     FIRs, a Mahindra Thar in others.
   - **Temporal-spatial conflict** — Priya Sharma accused in FIR105 (Phoenix
     Marketcity, 08:15–08:45 PM) and FIR107 (Indiranagar, 08:20–08:40 PM) on
     the same date, with overlapping time windows at two different locations.
3. **Pipeline under test**: each of the 50 FIRs was converted to a real PDF
   (`benchmark_runner.py`) and POSTed to the live `/extract` endpoint -
   exercising OCR/PDF parsing, regex identifier extraction, spaCy NER, and
   LLM-based (Groq Llama-3.3-70B) relationship extraction exactly as a real
   user would.
4. **Scoring**: `compute_metrics.py` compares the live system's output against
   the ground-truth table on a per-document, per-field basis, producing exact
   true positive / false positive / false negative counts - not aggregate
   counts, which can mask compensating errors.

## Results

### Structured identifier extraction (11 types, all 50 documents)

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| phone_numbers | 165 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| vehicle_numbers | 14 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| aadhaar_numbers | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| pan_numbers | 4 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| ifsc_codes | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| passport_numbers | 1 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| upi_ids | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| bank_accounts | 4 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| driving_licences | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| imei_numbers | 2 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| fir_number | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| **Overall** | **256** | **0** | **0** | **1.000** | **1.000** | **1.000** |

### Contradiction detection (3 tracked entities, 4 planted conflicts)

| Entity | Conflict | Result |
|---|---|---|
| Vikram Reddy | Age (34 vs 32) | True positive |
| Vikram Reddy | Vehicle (`FLED_IN` Hyundai i20 vs Mahindra Thar) | True positive |
| Ravi Kumar | Mobile (9876543210 vs 9112233445) | True positive |
| Priya Sharma | Temporal-spatial (FIR105 vs FIR107) | True positive |
| Ravi Kumar | Vehicle (`FLED_IN` KA01MG1234 vs KA06CH6006) | False positive — see [Known Limitations](#known-limitations) |

**TP = 4, FP = 1, FN = 0 → Precision = 0.80, Recall = 1.00, F1 = 0.889**

## Bugs found and fixed

Two bugs and one detection-logic gap were identified through this harness and
patched in the codebase (not just noted):

1. **Phone regex false positives** — `PHONE_PATTERN` had no word-boundary
   anchoring, so it matched 10-digit substrings embedded inside unrelated
   longer numbers (bank accounts, IMEI). Fixed with `(?<!\d)` / `(?!\d)`
   lookaround assertions. This eliminated all 5 false positives that had been
   present in the phone_numbers row above (originally 165 TP / 5 FP / 0 FN,
   1.000 → 0.971 precision before the fix).
2. **UPI handle coverage gap** — `UPI_PATTERN` recognized `okaxis`, `paytm`,
   `ybl`, and several others, but not `phonepe` or `googlepay` - two of the
   most common UPI providers in India. This caused 3 of 5 UPI IDs in the
   corpus to be silently dropped (recall 0.400 before the fix). Fixed by
   extending the pattern's handle-suffix list.
3. **Contradiction false-positive pattern** — the relation-conflict check
   flagged *any* relation type with more than one distinct object across
   cases as a contradiction, with no distinction between identity-defining
   relations (e.g. `FLED_IN`, which should typically be consistent for one
   person) and repeatable-event relations (e.g. `COMMITTED_THEFT_AT`, which
   are *expected* to vary — a repeat offender legitimately commits crimes in
   many locations). This produced one false positive per additional case a
   repeat offender appeared in (3 of the 4 original false positives, before
   the fix, all traced to this single root cause). Fixed by excluding
   `COMMITTED_*`-prefixed relation types from the blanket cross-case conflict
   check in `contradiction_detection.py`. This raised contradiction-detection
   precision from 0.50 to 0.80 while holding recall at 1.00.

## Known limitations

- **Ravi Kumar `FLED_IN` false positive is a test-corpus issue, not a
  system defect.** The synthetic corpus assigned Ravi Kumar two different
  vehicle registrations across FIR102 and FIR130 without an intentional
  planted conflict - the system is behaving consistently with how it
  correctly flags genuine vehicle conflicts; the corpus just
  produced an unplanned fifth case. This is not fixed - it would require either correcting the test corpus or accepting that
  the detector will (correctly) flag any real instance of this pattern.
- **Hallucination checking on LLM-extracted relationships is a floor, not a
  full audit.** The automated check only flags relationship subjects/objects
  whose exact text string doesn't appear anywhere in the source document -
  it will not catch a paraphrased hallucination. No hallucinations were flagged in this run,
  but that result should not be read as "none at all."
- **Evaluation corpus is synthetic**, generated to match CaseGraph's expected
  input template. It is not a substitute for evaluation against real,
  messier FIR documents (inconsistent formatting, OCR noise from actual
  scanned documents, ambiguous phrasing) that the system would encounter in
  practice.

## Reproducing this evaluation

```
python benchmark_runner.py        # extracts all 50 FIRs, checks contradictions, spot-checks queries
python compute_metrics.py         # scores results/ against corpus_data.py ground truth
```

Requires a running Neo4j instance, `GROQ_API_KEY` set in `.env`, and the
backend running locally (`uvicorn backend.main:app --reload`).
