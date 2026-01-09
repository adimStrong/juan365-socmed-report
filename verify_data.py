#!/usr/bin/env python3
"""
Verify data integrity before pushing to production.
Returns exit code 0 if OK, 1 if issues found.

INCLUDES PROJECT IDENTITY CHECK - prevents pushing wrong project data!
"""

import sqlite3
import json
import sys
import os

# Get script directory for relative paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(SCRIPT_DIR, "data", "juan365_socmed.db")
JSON_PATH = os.path.join(SCRIPT_DIR, "frontend", "public", "data", "analytics.json")

# Thresholds for Juan365 Socmed
MIN_PAGES = 6
MIN_POSTS = 100
PROJECT_NAME = "Juan365 Socmed"
EXPECTED_PAGE_PATTERN = "Juan"  # Juan365, JuanBingo, JuanSports all match


def verify():
    print("=" * 60)
    print(f"DATA VERIFICATION - {PROJECT_NAME}")
    print("=" * 60)

    errors = []
    warnings = []

    # Check database
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()

        # PROJECT IDENTITY CHECK - verify we have the right data!
        cur.execute("SELECT page_name FROM pages")
        page_names = [r[0] for r in cur.fetchall()]
        matching_pages = [p for p in page_names if EXPECTED_PAGE_PATTERN in p]

        print(f"Project identity: Looking for '{EXPECTED_PAGE_PATTERN}' pages")
        print(f"  Found: {len(matching_pages)} matching pages")

        if len(matching_pages) == 0:
            errors.append(f"WRONG PROJECT DATA! No '{EXPECTED_PAGE_PATTERN}' pages found!")
            errors.append(f"  Found pages: {page_names[:3]}...")

        # Page count
        page_count = len(page_names)
        print(f"Pages in database: {page_count}")
        if page_count < MIN_PAGES:
            errors.append(f"Missing pages! Expected {MIN_PAGES}, found {page_count}")

        # Post count
        cur.execute("SELECT COUNT(*) FROM posts")
        post_count = cur.fetchone()[0]
        print(f"Posts in database: {post_count}")
        if post_count < MIN_POSTS:
            errors.append(f"Too few posts! Expected {MIN_POSTS}+, found {post_count}")

        # Follower check
        cur.execute("SELECT COUNT(*) FROM pages WHERE followers_count > 0 OR fan_count > 0")
        pages_with_followers = cur.fetchone()[0]
        print(f"Pages with followers: {pages_with_followers}")
        if pages_with_followers < MIN_PAGES:
            warnings.append(f"Some pages missing follower data")

        conn.close()
    except Exception as e:
        errors.append(f"Database error: {e}")

    # Check JSON export
    try:
        with open(JSON_PATH, 'r') as f:
            data = json.load(f)

        json_posts = len(data.get('posts', []))
        json_pages = len(data.get('pages', []))
        print(f"JSON posts: {json_posts}")
        print(f"JSON pages: {json_pages}")

        if json_pages < MIN_PAGES:
            errors.append(f"JSON missing pages! Expected {MIN_PAGES}, found {json_pages}")
        if json_posts < MIN_POSTS:
            errors.append(f"JSON too few posts! Expected {MIN_POSTS}+, found {json_posts}")
    except Exception as e:
        errors.append(f"JSON error: {e}")

    print()
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  - {w}")
        print()

    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  - {e}")
        print()
        print("VERIFICATION FAILED - Do not push!")
        return 1
    else:
        print("VERIFICATION PASSED - Safe to push!")
        return 0


if __name__ == "__main__":
    sys.exit(verify())
