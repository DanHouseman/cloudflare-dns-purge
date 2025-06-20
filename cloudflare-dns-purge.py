#!/usr/bin/env python3
# =============================================================================
# cloudflare-purge-dns.py
# A CLI tool to purge specific DNS record types from Cloudflare’s 1.1.1.1 cache.
# + Purpose:
#     - Clear cached/stale DNS entries across global resolvers.
#     - Automate DNS hygiene for CI/CD, migrations, or failovers.
# + Basic Usage:
#     python cloudflare-purge-dns.py example.com --types A AAAA --verbose --export
# + Install dependencies:
#     pip install -r requirements.txt
# + Install globally for CLI access:
#     pip install .
#     cloudflare-purge-dns example.com --types A AAAA --verbose --export csv
# + API Endpoint Used:
#     https://one.one.one.one/api/v1/purge
# =============================================================================

import argparse
import requests
import sys
import time
import random
import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

ALL_TYPES = [
    "A", "AAAA", "CAA", "CNAME", "DNSKEY", "DS", "HTTPS", "LOC",
    "MX", "NAPTR", "NS", "PTR", "SPF", "SRV", "SVCB", "SSHFP", "TLSA", "TXT"
]

def purge_record(domain, record_type, verbose, pad_width):
    url = "https://one.one.one.one/api/v1/purge"
    body = {"domain": domain, "type": record_type}
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "CloudflarePurgeScript/1.6"
    }

    try:
        response = requests.post(url, json=body, headers=headers)
        try:
            text = response.json().get("msg", "").strip()
        except ValueError:
            text = response.text.strip()

        is_success = response.status_code == 200 and "purge request queued" in text.lower()

        if verbose:
            status_icon = "✅" if is_success else "❌"
            status_text = "SUCCESS" if is_success else "FAILURE"
            padded_type = record_type.ljust(pad_width)
            print(f"[{status_icon} {status_text}] {padded_type} → {text}")

        return is_success, record_type, text

    except Exception as e:
        if verbose:
            padded_type = record_type.ljust(pad_width)
            print(f"[❌ FAILURE] {padded_type} → Exception: {str(e)}")
        return False, record_type, str(e)

def parse_record_types(raw):
    if not raw:
        return ALL_TYPES
    combined = " ".join(raw) if isinstance(raw, list) else raw
    tokens = [t.strip().upper() for t in combined.replace(",", " ").split()]
    return list(filter(None, tokens))

def main():
    parser = argparse.ArgumentParser(description="Purge DNS records from 1.1.1.1")
    parser.add_argument("domain", help="Target domain (e.g. example.com)")
    parser.add_argument(
        "--types", nargs="+",
        help="Comma or space-separated list of DNS record types (e.g. A,AAAA or A AAAA). Defaults to all.",
        default=[]
    )
    parser.add_argument(
        "--delay", type=float, default=0,
        help="Delay (in seconds) between purge requests or submissions."
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable per-request output"
    )
    parser.add_argument(
        "--threads", type=int, default=1,
        help="Number of threads for concurrent purges (default: 1)"
    )
    parser.add_argument(
        "--export", nargs="?", const="json", choices=["json", "csv"],
        help="Export results to file. Defaults to JSON. Use --export csv for CSV format."
    )

    args = parser.parse_args()
    record_types = parse_record_types(args.types)

    # Validate
    invalid_types = [t for t in record_types if t not in ALL_TYPES]
    if invalid_types:
        print(f"[ERROR] Unknown DNS types: {', '.join(invalid_types)}")
        sys.exit(1)

    pad_width = max(len(t) for t in record_types)
    successes, failures = [], []

    if args.threads > 1:
        if args.verbose and args.delay > 0:
            print(f"[INFO] Multithreading with {args.threads} threads and {args.delay:.2f}s delay between submissions.")
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = []
            for i, rtype in enumerate(record_types):
                futures.append(executor.submit(
                    purge_record, args.domain, rtype, args.verbose, pad_width
                ))
                if args.delay > 0 and i < len(record_types) - 1:
                    time.sleep(args.delay)
            for future in as_completed(futures):
                success, rtype, message = future.result()
                if success:
                    successes.append(rtype)
                else:
                    failures.append((rtype, message))
    else:
        for rtype in record_types:
            success, rtype, message = purge_record(args.domain, rtype, args.verbose, pad_width)
            if success:
                successes.append(rtype)
            else:
                failures.append((rtype, message))
            if args.delay > 0:
                time.sleep(args.delay + random.uniform(0.1, 0.3))

    # === SUMMARY ===
    print("\n=== SUMMARY ===")
    print(f"✅ Successes: {len(successes)} → {', '.join(successes) if successes else 'None'}")
    print(f"❌ Failures: {len(failures)}")
    for rtype, msg in failures:
        print(f"  - {rtype.ljust(pad_width)} → {msg}")

    # === EXPORT ===
    if args.export:
        export_file = f"purge_log_{args.domain}.{args.export}"
        if args.export == "csv":
            with open(export_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Type", "Status", "Message"])
                for t in successes:
                    writer.writerow([t, "SUCCESS", "purge request queued"])
                for t, msg in failures:
                    writer.writerow([t, "FAILURE", msg])
        else:
            data = {
                "domain": args.domain,
                "successes": [{"type": t, "status": "SUCCESS", "message": "purge request queued"} for t in successes],
                "failures": [{"type": t, "status": "FAILURE", "message": msg} for t, msg in failures]
            }
            with open(export_file, "w") as f:
                json.dump(data, f, indent=2)
        print(f"[INFO] Results exported to {export_file}")

if __name__ == "__main__":
    main()
