"""Submit documents through APIM and poll for results to show what happens without sticky sessions.

Usage:
  pip install requests
  export APIM_URL=https://<your-apim>.azure-api.net
  export APIM_KEY=<apim subscription key>
  python test_sticky.py 20
"""
import os
import sys
import time
from collections import Counter

import requests

APIM_URL = os.environ["APIM_URL"].rstrip("/")
APIM_KEY = os.environ["APIM_KEY"]
KEY_HEADER = os.environ.get("APIM_KEY_HEADER", "apim-key")  # renamed header, see README
API_VERSION = "2024-11-30"
MODEL = "prebuilt-layout"
SAMPLE_DOC = ("https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/"
              "master/curl/form-recognizer/sample-layout.pdf")

HEADERS = {KEY_HEADER: APIM_KEY, "Content-Type": "application/json"}


def submit():
    r = requests.post(
        f"{APIM_URL}/documentintelligence/documentModels/{MODEL}:analyze",
        params={"api-version": API_VERSION},
        headers=HEADERS,
        json={"urlSource": SAMPLE_DOC},
        timeout=30,
    )
    r.raise_for_status()
    return r.headers["Operation-Location"], r.headers.get("x-served-by", "?")


def poll(op_url, max_tries=30):
    """Return (final_status, list of (http_status, served_by) for each poll)."""
    trail = []
    for _ in range(max_tries):
        r = requests.get(op_url, headers=HEADERS, timeout=30)
        trail.append((r.status_code, r.headers.get("x-served-by", "?")))
        if r.status_code == 404:
            return "404 - result not found on this instance", trail
        if r.ok:
            status = r.json().get("status")
            if status in ("succeeded", "failed"):
                return status, trail
        time.sleep(1)
    return "timeout", trail


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    outcomes = Counter()
    for i in range(n):
        op_url, submitted_to = submit()
        result, trail = poll(op_url)
        outcomes[result.split(" ")[0]] += 1
        polled = ", ".join(f"{code}@{host.split('.')[0]}" for code, host in trail)
        print(f"[{i+1:02}] submitted to {submitted_to.split('.')[0]:<28} -> {result}\n      polls: {polled}")
    print("\nSummary:", dict(outcomes))
    if outcomes.get("404"):
        print("The 404s are polls that were routed to an instance that never received the document.")


if __name__ == "__main__":
    main()
