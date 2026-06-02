#!/usr/bin/env python3
"""
Script to clean up scripts_repo_log.json by removing entries for scripts
that no longer exist in the R2 bucket's scripts/ directory.

Workflow:
  1. List all meditation script files in the R2 bucket's scripts/ directory
     (excluding the log file itself and any non-script files).
  2. Download scripts_repo_log.json from R2.
  3. For each entry in the log, check whether the corresponding
     {duration}_{level}_{variation}.json file still exists in the bucket.
  4. Remove any log entry whose file is missing.
  5. Upload the cleaned log back to R2 (and save a local copy as fallback).
"""

import json
import os
import re
import sys
from dotenv import load_dotenv
import boto3

load_dotenv()

# --- Configuration -----------------------------------------------------------
LOG_R2_KEY = "scripts/scripts_repo_log.json"
LOG_LOCAL_PATH = os.path.join(os.path.dirname(__file__), "scripts_repo_log.json")

# Regex to match meditation script files: e.g. "5_principiante_1.json"
SCRIPT_PATTERN = re.compile(r"^(\d+)_([a-z]+)_(\d+)\.json$")

# Expected levels (for validation)
VALID_LEVELS = {"principiante", "intermedio", "avanzado"}


# --- R2 helpers --------------------------------------------------------------
def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )


def get_bucket_name():
    return os.getenv("R2_BUCKET_NAME")


def list_script_files(s3, bucket):
    """
    List all meditation script files in the scripts/ prefix of the bucket.
    Returns a set of (duration_str, level, variation) tuples that exist as files.
    Only considers files matching the pattern {duration}_{level}_{variation}.json
    and ignores scripts_repo_log.json.
    """
    existing_scripts = set()
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix="scripts/")

    for page in pages:
        if "Contents" not in page:
            continue
        for obj in page["Contents"]:
            key = obj["Key"]
            # Skip the log file itself
            if key == LOG_R2_KEY:
                continue
            filename = key.split("/")[-1]
            match = SCRIPT_PATTERN.match(filename)
            if match:
                duration_val = int(match.group(1))
                level = match.group(2)
                variation = int(match.group(3))
                if level in VALID_LEVELS and variation in (1, 2, 3):
                    duration_str = f"{duration_val} min"
                    existing_scripts.add((duration_str, level, variation))

    return existing_scripts


def download_log_from_r2(s3, bucket):
    """Download and parse scripts_repo_log.json from R2."""
    try:
        obj = s3.get_object(Bucket=bucket, Key=LOG_R2_KEY)
        content = obj["Body"].read().decode("utf-8")
        log_data = json.loads(content)
        if "scripts" not in log_data:
            log_data["scripts"] = []
        return log_data
    except s3.exceptions.NoSuchKey:
        print("  Log file not found in R2. Nothing to clean.")
        sys.exit(0)
    except Exception as e:
        raise Exception(f"Failed to download log from R2: {e}")


def upload_log_to_r2(s3, bucket, log_data):
    """Upload scripts_repo_log.json to R2."""
    s3.put_object(
        Bucket=bucket,
        Key=LOG_R2_KEY,
        Body=json.dumps(log_data, ensure_ascii=False, indent=2),
        ContentType="application/json",
    )


# --- Main --------------------------------------------------------------------
def main():
    print("=== Script Repo Log Cleanup ===")
    print("This script will remove log entries whose corresponding JSON files")
    print("no longer exist in the R2 bucket's scripts/ directory.\n")

    # Connect to R2
    s3 = get_s3_client()
    bucket = get_bucket_name()
    if not bucket:
        print("ERROR: R2_BUCKET_NAME environment variable not set.")
        sys.exit(1)

    # 1. List actual script files in the bucket
    print("[1/3] Listing meditation script files in R2 bucket...")
    actual_files = list_script_files(s3, bucket)
    print(f"  Found {len(actual_files)} script file(s) in the bucket.")
    for f in sorted(actual_files):
        print(f"    - {f[0]}, {f[1]}, variation {f[2]}")
    print()

    # 2. Download the log
    print("[2/3] Downloading scripts_repo_log.json from R2...")
    log_data = download_log_from_r2(s3, bucket)
    entries_before = len(log_data["scripts"])
    print(f"  Log contains {entries_before} entry(ies).\n")

    # 3. Filter out entries that have no matching file
    print("[3/3] Comparing log entries against actual files...")
    kept_entries = []
    removed_entries = []

    for entry in log_data["scripts"]:
        key = (entry["duration"], entry["level"], entry["variation"])
        if key in actual_files:
            kept_entries.append(entry)
        else:
            # Build a meaningful description for the removed entry
            desc = f"  ✗ REMOVED: {entry['duration']}, {entry['level']}, variation {entry['variation']}"
            if "date_generated" in entry:
                desc += f" (generated: {entry['date_generated']})"
            removed_entries.append(desc)

    log_data["scripts"] = kept_entries
    entries_after = len(log_data["scripts"])
    entries_removed = entries_before - entries_after

    # Print summary
    if removed_entries:
        print(f"  Removed {entries_removed} stale entry(ies):")
        for desc in removed_entries:
            print(desc)
    else:
        print("  No stale entries found — log is already clean.")

    print(f"\n  Entries before: {entries_before}")
    print(f"  Entries after:  {entries_after}")
    print(f"  Removed:        {entries_removed}\n")

    # 4. Upload the cleaned log back to R2 and save locally
    if entries_removed > 0:
        print("Saving cleaned log...")
        # Local fallback
        with open(LOG_LOCAL_PATH, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        # Upload to R2
        try:
            upload_log_to_r2(s3, bucket, log_data)
            print(f"  ✓ Uploaded cleaned log to R2 ({LOG_R2_KEY})")
            print(f"  ✓ Saved local copy ({LOG_LOCAL_PATH})")
        except Exception as e:
            print(f"  ✗ Failed to upload to R2: {e}")
    else:
        print("No changes needed — log is up to date.")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()