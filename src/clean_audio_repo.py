#!/usr/bin/env python3
"""
Script to clean up orphaned silence audio files from the meditations/silence/
directory in the R2 bucket, and update meditations_repo_log.json accordingly.

Workflow:
  1. Download scripts_repo_log.json from R2 (scripts/ prefix).
  2. Download meditations_repo_log.json from R2 (meditations/ prefix).
  3. Build a set of (duration, level, variation) tuples that exist in scripts.
  4. For each entry in meditations that has music="silence", check if a
     matching script exists. If not, it's orphaned — delete the corresponding
     .opus file from meditations/silence/ and remove the entry from the log.
  5. Upload the cleaned meditations_repo_log.json back to R2.
"""

import json
import os
import re
import sys
from dotenv import load_dotenv
import boto3

load_dotenv()

# --- Configuration -----------------------------------------------------------
SCRIPTS_LOG_KEY = "scripts/scripts_repo_log.json"
MEDITATIONS_LOG_KEY = "meditations/meditations_repo_log.json"
MEDITATIONS_SILENCE_PREFIX = "meditations/silence/"

# Regex to parse duration from "10 min" -> 10
DURATION_PATTERN = re.compile(r"^(\d+)\s*min$")

# Regex to match silence audio filenames: e.g. "10_avanzado_1.opus"
SILENCE_FILE_PATTERN = re.compile(r"^(\d+)_([a-z]+)_(\d+)\.opus$")

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


def download_json_from_r2(s3, bucket, key):
    """Download and parse a JSON file from R2."""
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        content = obj["Body"].read().decode("utf-8")
        return json.loads(content)
    except s3.exceptions.NoSuchKey:
        print(f"  File not found in R2: {key}")
        return None
    except Exception as e:
        raise Exception(f"Failed to download {key} from R2: {e}")


def upload_json_to_r2(s3, bucket, key, data):
    """Upload a JSON object to R2."""
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, ensure_ascii=False, indent=2),
        ContentType="application/json",
    )


def delete_file_from_r2(s3, bucket, key):
    """Delete a single file from R2."""
    s3.delete_object(Bucket=bucket, Key=key)


def parse_scripts_log(log_data):
    """
    Extract a set of (duration_str, level, variation) tuples from the
    scripts log. duration_str is in "X min" format to match the log entries.
    """
    scripts_set = set()
    for entry in log_data.get("scripts", []):
        dur = entry.get("duration")
        lvl = entry.get("level")
        var = entry.get("variation")
        if dur and lvl and var is not None:
            scripts_set.add((dur, lvl, var))
    return scripts_set


def parse_meditations_log(log_data):
    """
    Extract all entries from the meditations log, returning the list.
    """
    return log_data.get("meditations", [])


def build_silence_key(duration_str, level, variation):
    """
    Build the R2 key for a silence audio file.
    Example: ("10 min", "avanzado", 1) -> "meditations/silence/10_avanzado_1.opus"
    """
    match = DURATION_PATTERN.match(duration_str)
    if not match:
        return None
    dur_num = match.group(1)
    return f"{MEDITATIONS_SILENCE_PREFIX}{dur_num}_{level}_{variation}.opus"


def is_silence_with_music(entry):
    """Check if an entry has music='silence'."""
    return entry.get("music", "").strip().lower() == "silence"


# --- Main --------------------------------------------------------------------
def main():
    print("=== Clean Orphaned Silence Audio Files ===")
    print("This script will:")
    print("  1. Compare scripts_repo_log.json with meditations_repo_log.json")
    print("  2. Remove silence audio files whose script no longer exists")
    print("  3. Update meditations_repo_log.json in R2\n")

    # Connect to R2
    s3 = get_s3_client()
    bucket = get_bucket_name()
    if not bucket:
        print("ERROR: R2_BUCKET_NAME environment variable not set.")
        sys.exit(1)

    # 1. Download scripts_repo_log.json
    print("[1/4] Downloading scripts_repo_log.json from R2...")
    scripts_log = download_json_from_r2(s3, bucket, SCRIPTS_LOG_KEY)
    if scripts_log is None:
        print("  FATAL: scripts_repo_log.json not found. Cannot proceed.")
        sys.exit(1)
    existing_scripts = parse_scripts_log(scripts_log)
    print(f"  Found {len(existing_scripts)} script(s) in the log.\n")

    # 2. Download meditations_repo_log.json
    print("[2/4] Downloading meditations_repo_log.json from R2...")
    meditations_log = download_json_from_r2(s3, bucket, MEDITATIONS_LOG_KEY)
    if meditations_log is None:
        print("  No meditations log found. Nothing to clean.")
        sys.exit(0)
    meditations_entries = parse_meditations_log(meditations_log)
    print(f"  Found {len(meditations_entries)} meditation(s) in the log.\n")

    # 3. Identify orphaned silence entries and delete files
    print("[3/4] Checking for orphaned silence entries...")
    kept_entries = []
    deleted_files = []
    skipped_no_match = []

    for entry in meditations_entries:
        dur = entry.get("duration")
        lvl = entry.get("level")
        var = entry.get("variation")

        # Build the key tuple as it appears in scripts log
        script_key = (dur, lvl, var)

        if is_silence_with_music(entry):
            if script_key not in existing_scripts:
                # --- Orphaned silence entry → delete the file ---
                silence_key = build_silence_key(dur, lvl, var)
                if silence_key:
                    try:
                        delete_file_from_r2(s3, bucket, silence_key)
                        desc = f"  ✗ DELETED: {silence_key}"
                        deleted_files.append(desc)
                        print(desc)
                    except Exception as e:
                        print(f"  ✗ FAILED to delete {silence_key}: {e}")
                else:
                    desc = f"  ⚠ SKIPPED (could not parse duration): {dur}, {lvl}, var {var}"
                    skipped_no_match.append(desc)
                    print(desc)
                # Do NOT keep this entry in the log
            else:
                # Silence entry has a matching script → keep it
                kept_entries.append(entry)
        else:
            # Non-silence entries are kept as-is
            kept_entries.append(entry)

    print(f"\n  Summary:")
    print(f"    - Entries kept:          {len(kept_entries)}")
    print(f"    - Files deleted:         {len(deleted_files)}")
    print(f"    - Skipped (name issue):  {len(skipped_no_match)}\n")

    # 4. Upload updated meditations_repo_log.json if any changes were made
    if len(kept_entries) != len(meditations_entries):
        print("[4/4] Updating meditations_repo_log.json in R2...")
        meditations_log["meditations"] = kept_entries

        # Save locally as fallback
        local_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "web-ui",
            "public",
            "meditations_repo_log.json",
        )
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(meditations_log, f, ensure_ascii=False, indent=2)

        # Upload to R2
        try:
            upload_json_to_r2(s3, bucket, MEDITATIONS_LOG_KEY, meditations_log)
            print(f"  ✓ Uploaded updated log to R2 ({MEDITATIONS_LOG_KEY})")
            print(f"  ✓ Saved local copy ({local_path})")
        except Exception as e:
            print(f"  ✗ Failed to upload to R2: {e}")
    else:
        print("[4/4] No changes needed — log is already clean.")

    if deleted_files:
        print("\n  Deleted files:")
        for d in deleted_files:
            print(f"    {d}")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()