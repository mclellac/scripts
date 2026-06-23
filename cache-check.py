#!/usr/bin/env python
import requests
import time
import argparse
import sys
from collections import Counter


class AkamaiValidator:
    def __init__(self, url):
        self.url = url
        self.session = requests.Session()
        # Pragma headers to expose Akamai internal cache logic
        self.session.headers.update(
            {
                "Pragma": (
                    "akamai-x-get-request-id, "
                    "akamai-x-get-cache-key, "
                    "akamai-x-get-true-cache-key, "
                    "akamai-x-cache-on, "
                    "akamai-x-cache-remote-on, "
                    "akamai-x-check-cacheable, "
                    "x-akamai-logging-mode: verbose"
                ),
                "User-Agent": "CBC/Akamai Cache Integrity Tester/1.0",
            }
        )
        self.history = []

    def validate(self, count, interval):
        print(f"\nTarget: {self.url}")
        print(f"Executing {count} GET requests with {interval}s interval...")
        print("-" * 80)

        for i in range(1, count + 1):
            try:
                # stream=True fetches headers but doesn't download the body content
                with self.session.get(self.url, stream=True, timeout=10) as r:
                    raw_age = r.headers.get("Age")
                    data = {
                        "status": r.status_code,
                        "x_cache": r.headers.get("X-Cache", "N/A"),
                        # Only convert to int if the header exists; otherwise None
                        "age": int(raw_age) if raw_age is not None else None,
                        "cache_key": r.headers.get("X-Cache-Key", ""),
                        "true_key": r.headers.get("X-True-Cache-Key", "N/A"),
                        "vary": r.headers.get("Vary", "None"),
                        "cache_control": r.headers.get("Cache-Control", "N/A"),
                        "request_id": r.headers.get("X-Akamai-Request-Id", "N/A"),
                        "eu_flag": "unknown",
                    }

                    # Extract x-eu-country flag from the cache key
                    if "x-eu-country=" in data["cache_key"]:
                        data["eu_flag"] = (
                            data["cache_key"].split("x-eu-country=")[1].split()[0]
                        )

                    self.report_line(i, data)
                    self.history.append(data)

            except Exception as e:
                print(f"[{i:02d}] 🛑 CONNECTION ERROR: {e}")

            if i < count:
                time.sleep(interval)

        self.print_final_summary()

    def report_line(self, idx, curr):
        # Determine if it was a Cache Hit
        is_hit = any(x in curr["x_cache"] for x in ["TCP_HIT", "TCP_MEM_HIT"])
        indicator = "✅ HIT " if is_hit else "❌ MISS"

        # Build Age string only if the header was present
        age_output = f" | Age: {curr['age']:<4}s" if curr["age"] is not None else ""

        print(
            f"[{idx:02d}] {indicator} | {curr['x_cache'].split(' from ')[0]:<15}{age_output} | ID: {curr['request_id']}"
        )

        # Real-time Checks
        if curr["status"] != 200:
            print(f"     ! ALERT: Non-200 Status Code: {curr['status']}")

        if curr["vary"] != "None" and any(
            v in curr["vary"] for v in ["Cookie", "User-Agent"]
        ):
            print(
                f"     ! CRITICAL: 'Vary: {curr['vary']}' detected. This will fragment the cache."
            )

        if len(self.history) > 0:
            prev = self.history[-1]

            # Check for x-eu-country toggle (Cache Fragmentation)
            if curr["eu_flag"] != prev["eu_flag"]:
                print(
                    f"     ! FLIP: x-eu-country changed ({prev['eu_flag']} -> {curr['eu_flag']})"
                )
                print(f"        Key: {curr['cache_key']}")

            # Check for Age Reset (Unexpected re-validation)
            # Only perform check if both current and previous Age are known
            if (
                is_hit
                and curr["age"] is not None
                and prev["age"] is not None
                and curr["age"] < prev["age"]
            ):
                print(
                    f"     ! RESET: Cache Age dropped from {prev['age']}s to {curr['age']}s. Possible purge or re-fetch."
                )

            # Check for Cache Key Mismatch
            if curr["cache_key"] != prev["cache_key"]:
                print(
                    f"     ! MISMATCH: X-Cache-Key changed! Previous was different from current."
                )

    def print_final_summary(self):
        total = len(self.history)
        if total == 0:
            return

        hits = sum(
            1
            for d in self.history
            if any(x in d["x_cache"] for x in ["HIT", "MEM_HIT"])
        )
        vary_headers = [d["vary"] for d in self.history]

        print("\n" + "=" * 80)
        print(f"FINAL CACHE INTEGRITY SUMMARY")
        print(f"Success Rate: {hits}/{total} ({(hits/total)*100:.1f}%)")
        print("-" * 80)
        print(f"Observed Vary Headers: {set(vary_headers)}")

        if hits / total < 0.6:
            print("\n💡 DIAGNOSTIC ADVICE: Low Hit Rate detected.")
            print(
                " - If 'Vary: Cookie' is present, Akamai is creating unique cache objects per user."
            )
            print(
                " - Check if your 'Old Stories' rule is being overridden by Origin Cache-Control."
            )
            print(
                " - Ensure query strings aren't forcing misses if they aren't part of the Cache Key."
            )
        print("=" * 80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Advanced Akamai Cache Integrity Validator"
    )
    parser.add_argument("url", help="Full URL to test")
    parser.add_argument(
        "-c", "--count", type=int, default=5, help="Number of requests (default: 5)"
    )
    parser.add_argument(
        "-s",
        "--seconds",
        type=int,
        default=1,
        help="Interval between requests (default: 1)",
    )

    args = parser.parse_args()

    try:
        validator = AkamaiValidator(args.url)
        validator.validate(args.count, args.seconds)
    except KeyboardInterrupt:
        print("\nTest aborted by user.")
        sys.exit(0)
