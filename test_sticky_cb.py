"""Test Document Intelligence behind APIM: sticky sessions and circuit breaking.

Two modes:
  direct  - call ONE Document Intelligence instance directly (baseline, should be 100% success)
  apim    - call through APIM round-robin pool (expect ~50%+ of jobs to fail with 404)

Usage:
  pip install requests

  # Baseline
  export DI_ENDPOINT=https://<instance-1>.cognitiveservices.azure.com
  export DI_KEY=<instance-1 key>
  python test_sticky.py direct 10

  # Through APIM
  export APIM_URL=https://<your-apim>.azure-api.net
  export APIM_KEY=<apim subscription key>
  python test_sticky.py apim 20
"""
import os
import sys
import time
from collections import Counter

import requests

API_VERSION = "2024-11-30"
BASE = "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/"

# Free public sample documents from Microsoft's sample repo: (file, model to use)
DOCS = [
    ("sample-layout.pdf",           "prebuilt-layout"),
    ("rest-api/invoice.pdf",        "prebuilt-invoice"),
    ("rest-api/receipt.png",        "prebuilt-receipt"),
    ("sample-invoice.pdf",          "prebuilt-invoice"),
    ("rest-api/layout.png",         "prebuilt-layout"),
    ("contoso-receipt.png",         "prebuilt-receipt"),
    ("rest-api/read.png",           "prebuilt-read"),
    ("rest-api/identity_documents.png", "prebuilt-idDocument"),
    ("rest-api/business_card.jpg",  "prebuilt-layout"),
    ("rest-api/w2.png",             "prebuilt-tax.us.w2"),
    # Multi-page = longer processing = more polls = more chances to hit the wrong instance
    ("covid-informed-consent-for-inactivated-immunization-universal-2020-v.3.-covid-screening-vaccine-questions.pdf",
     "prebuilt-layout"),
]


def config(mode):
    if mode == "direct":
        return os.environ["DI_ENDPOINT"].rstrip("/"), {"Ocp-Apim-Subscription-Key": os.environ["DI_KEY"]}
    header = os.environ.get("APIM_KEY_HEADER", "apim-key")  # renamed in APIM, see README
    return os.environ["APIM_URL"].rstrip("/"), {header: os.environ["APIM_KEY"]}


def submit(base, headers, doc, model):
    """Return (operation_url or None, served_by, attempts, http_status, error_detail)."""
    r = requests.post(
        f"{base}/documentintelligence/documentModels/{model}:analyze",
        params={"api-version": API_VERSION},
        headers={**headers, "Content-Type": "application/json"},
        json={"urlSource": BASE + doc},
        timeout=60,
    )
    served = r.headers.get("x-served-by", "direct" if "x-attempts" not in r.headers else "?")
    attempts = r.headers.get("x-attempts", "-")
    op_url = r.headers.get("Operation-Location") if r.status_code == 202 else None
    detail = ""
    if op_url is None:
        # Debug headers set by the policy's on-error section, plus the start of the body
        parts = [f"{k[8:]}={r.headers[k]}" for k in ("x-error-section", "x-error-source", "x-error-reason", "x-error-message") if r.headers.get(k)]
        body = " ".join(r.text.split())[:300]
        detail = " | ".join(parts + ([f"body={body}"] if body else []))
    return op_url, served, attempts, r.status_code, detail


def poll(op_url, headers, max_tries=60):
    trail = []
    for _ in range(max_tries):
        r = requests.get(op_url, headers=headers, timeout=30)
        trail.append((r.status_code, r.headers.get("x-served-by", "direct")))
        if r.status_code == 404:
            return "404", trail
        if r.status_code == 429:
            time.sleep(2)
            continue
        if r.ok:
            status = r.json().get("status")
            if status in ("succeeded", "failed"):
                return status, trail
        time.sleep(1)
    return "timeout", trail


def short(host):
    return host.split(".")[0]


def main():
    args = sys.argv[1:]
    # Accept "apim 20", "direct 10", or just "20" (defaults to apim mode)
    mode = args.pop(0) if args and not args[0].isdigit() else "apim"
    n = int(args[0]) if args else len(DOCS)
    base, headers = config(mode)
    outcomes = Counter()
    seen_errors = set()

    print(f"Mode: {mode}  ->  {base}\n")
    for i in range(n):
        doc, model = DOCS[i % len(DOCS)]
        op_url, submitted_to, attempts, status, detail = submit(base, headers, doc, model)
        name = doc.split('/')[-1][:30]
        if op_url is None:
            # Submission itself failed (for example the chosen instance is down)
            result = f"submit failed {status}"
            outcomes[result] += 1
            print(f"[{i+1:02}] {name:<30} {model:<20} POST@{short(submitted_to)}  attempts={attempts}  => {result}")
            if detail and detail not in seen_errors:
                seen_errors.add(detail)
                print(f"      error: {detail}")
            continue
        result, trail = poll(op_url, headers)
        outcomes[result] += 1
        polls = " ".join(f"{code}@{short(h)}" for code, h in trail)
        print(f"[{i+1:02}] {name:<30} {model:<20} POST@{short(submitted_to)}  attempts={attempts}  => {result}")
        print(f"      polls: {polls}")

    print("\nSummary:", dict(outcomes))
    if outcomes.get("404"):
        print("404 = the poll was routed to an instance that never received that document.")


if __name__ == "__main__":
    main()