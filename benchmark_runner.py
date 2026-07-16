"""
CaseGraph full-pipeline benchmark runner.

Steps this performs:
  1. Converts all 50 docs in generated_corpus.json into real PDF files
     (since /extract only accepts file uploads, not raw text/JSON).
  2. POSTs each PDF to /extract, collects entities + relationships.
  3. Calls /contradict for the three accused names with planted conflicts
     and checks the response against ground truth.
  4. Runs a handful of /query calls and prints Cypher + answer for manual review.
  5. Flags relationship extractions that reference entities never seen in
     the source text - a cheap, non-exhaustive hallucination check.
"""

import json
import os
import time
import requests
from fpdf import FPDF

BASE_URL = os.getenv("CASEGRAPH_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY")
HEADERS = {"X-API-Key": API_KEY}

CORPUS_PATH = "generated_corpus.json"
PDF_DIR = "corpus_pdfs"


def build_pdfs():
    os.makedirs(PDF_DIR, exist_ok=True)
    with open(CORPUS_PATH) as f:
        docs = json.load(f)

    paths = []
    for doc in docs:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)
        for line in doc["text"].split("\n"):
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 6, line if line.strip() else " ")
        fname = f"{doc['id'].replace('/', '_')}.pdf"
        path = os.path.join(PDF_DIR, fname)
        pdf.output(path)
        paths.append((doc["id"], path))
    print(f"Built {len(paths)} PDFs in {PDF_DIR}/")
    return paths


def health_check():
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        r.raise_for_status()
        print("Backend healthy:", r.json())
        return True
    except Exception as e:
        print(f"Backend not reachable at {BASE_URL}: {e}")
        print("Start it with: uvicorn backend.main:app --reload")
        return False


def run_extraction(paths, skip_existing=True):
    os.makedirs("results", exist_ok=True)
    results = []
    for fir_id, path in paths:
        fname = f"results/extract_{fir_id.replace('/', '_')}.json"
        if skip_existing and os.path.exists(fname):
            with open(fname) as f:
                results.append((fir_id, json.load(f)))
            print(f"[{fir_id}] skipped (already have {fname})")
            continue
        with open(path, "rb") as f:
            files = {"file": (os.path.basename(path), f, "application/pdf")}
            for attempt in range(3):
                try:
                    r = requests.post(f"{BASE_URL}/extract", headers=HEADERS, files=files, timeout=60)
                    r.raise_for_status()
                    data = r.json()
                    results.append((fir_id, data))
                    with open(fname, "w") as out:
                        json.dump(data, out, indent=2)
                    print(f"[{fir_id}] OK — {len(data.get('entities', []))} entities, "
                          f"{len(data.get('relationships', []))} relationships -> {fname}")
                    break
                except Exception as e:
                    wait = 10 * (attempt + 1)
                    print(f"[{fir_id}] attempt {attempt+1} FAILED: {e} — retrying in {wait}s")
                    time.sleep(wait)
            else:
                print(f"[{fir_id}] gave up after 3 attempts")
        time.sleep(2)  # more breathing room for Groq's free-tier rate limit
    return results


def check_hallucinations(results):
    print("\n=== Hallucination spot-check (relationship subjects/objects vs source text) ===")
    flagged = 0
    for fir_id, data in results:
        text = data.get("cleaned_text", "")
        for rel in data.get("relationships", []):
            subj = rel.get("subject", "") or rel.get("source", "")
            obj = rel.get("object", "") or rel.get("target", "")
            for entity_name in (subj, obj):
                if entity_name and entity_name.lower() not in text.lower():
                    print(f"  [{fir_id}] relationship references '{entity_name}' — not found verbatim in source text")
                    flagged += 1
    print(f"Flagged {flagged} relationship endpoints not found in source text.")
    print("NOTE: this only catches exact-string misses (paraphrases won't be flagged).")
    print("Still read a sample of relationships manually — this is a floor, not a full check.\n")


def check_contradictions():
    print("=== Contradiction detection (live) ===")
    expected = {
        "Vikram Reddy": "attribute (age) + relation (vehicle) conflicts",
        "Ravi Kumar": "attribute (mobile) conflict",
        "Priya Sharma": "temporal-spatial conflict",
    }
    os.makedirs("results", exist_ok=True)
    for name, desc in expected.items():
        try:
            r = requests.get(f"{BASE_URL}/contradict", headers=HEADERS,
                              params={"entity": name}, timeout=30)
            r.raise_for_status()
            result = r.json()
            print(f"\n[{name}] expected: {desc}")
            has_contradictions = bool(result.get("contradictions"))
            print(f"  contradictions field present and non-empty: {has_contradictions}")
            print(f"  keys in response: {list(result.keys())}")
            fname = f"results/contradict_{name.replace(' ', '_')}.json"
            with open(fname, "w") as f:
                json.dump(result, f, indent=2)
            print(f"  full response written to {fname}")
        except Exception as e:
            print(f"[{name}] FAILED: {e}")


def check_queries():
    print("\n=== Query engine spot-check ===")
    questions = [
        "Who are all accused persons across all FIRs?",
        "What vehicles are linked to Vikram Reddy?",
        "Which phone numbers appear in more than one FIR?",
        "Summarize FIR 145/2026",
    ]
    os.makedirs("results", exist_ok=True)
    for i, q in enumerate(questions):
        for attempt in range(3):
            try:
                r = requests.get(f"{BASE_URL}/query", headers=HEADERS,
                                  params={"question": q}, timeout=30)
                r.raise_for_status()
                result = r.json()
                print(f"\nQ: {q}")
                print(f"  answer: {result.get('answer')}")
                print(f"  result count: {len(result.get('results', []))}")
                fname = f"results/query_{i}.json"
                with open(fname, "w") as f:
                    json.dump(result, f, indent=2)
                print(f"  full response written to {fname}")
                break
            except Exception as e:
                wait = 10 * (attempt + 1)
                print(f"\nQ: {q}\nattempt {attempt+1} FAILED: {e} — retrying in {wait}s")
                time.sleep(wait)
        else:
            print(f"\nQ: {q}\ngave up after 3 attempts")
        time.sleep(2)


if __name__ == "__main__":
    if not health_check():
        exit(1)
    paths = build_pdfs()
    results = run_extraction(paths)
    check_hallucinations(results)
    check_contradictions()
    check_queries()
