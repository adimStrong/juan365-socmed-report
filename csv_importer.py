#!/usr/bin/env python3
"""
JuanBabes CSV Importer
Import Meta Business Suite CSV exports into SQLite database
"""

import csv
import sys
import argparse
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple

from database import (
    ensure_initialized, db_connection, upsert_page, upsert_post,
    insert_metrics, record_import, get_import_history, get_database_stats
)
from models import ImportResult
from config import COLUMN_MAPPING, EXPORTS_DIR, CSV_DOWNLOADS_DIR


# Column name variations that Meta might use
COLUMN_ALIASES = {
    'post_id': ['Post ID', 'PostID', 'post_id', 'id'],
    'page_id': ['Page ID', 'PageID', 'page_id'],
    'page_name': ['Page name', 'PageName', 'page_name', 'Page'],
    'title': ['Title', 'title', 'Message', 'message'],
    'description': ['Description', 'description', 'Caption'],
    'post_type': ['Post type', 'PostType', 'post_type', 'Type'],
    'publish_time': ['Publish time', 'PublishTime', 'publish_time', 'Created', 'Date'],
    'permalink': ['Permalink', 'permalink', 'URL', 'Link'],
    'reactions': ['Reactions', 'reactions', 'Total Reactions', 'Likes'],
    'comments': ['Comments', 'comments', 'Total Comments'],
    'shares': ['Shares', 'shares', 'Total Shares'],
    'views': ['Views', 'views', 'Video Views', 'Post Views'],
    'reach': ['Reach', 'reach', 'Total Reach', 'Post Reach'],
    'total_clicks': ['Total clicks', 'TotalClicks', 'total_clicks', 'Clicks'],
    'link_clicks': ['Link clicks', 'LinkClicks', 'link_clicks'],
    'other_clicks': ['Other clicks', 'OtherClicks', 'other_clicks'],
    'duration_sec': ['Duration (sec)', 'Duration', 'duration_sec', 'Video Length'],
    'is_crosspost': ['Is crosspost', 'IsCrosspost', 'is_crosspost', 'Crosspost'],
    'is_share': ['Is share', 'IsShare', 'is_share', 'Shared'],
}


def detect_columns(header: List[str]) -> Dict[str, int]:
    """
    Detect column indices from CSV header.

    Args:
        header: List of column names from CSV

    Returns:
        Dict mapping our field names to column indices
    """
    column_map = {}
    header_lower = [h.strip().lower() for h in header]

    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            alias_lower = alias.lower()
            if alias_lower in header_lower:
                column_map[field] = header_lower.index(alias_lower)
                break

    return column_map


def parse_int(value: Any) -> int:
    """Parse a value to int, handling empty strings and None."""
    if value is None or value == '' or value == 'N/A':
        return 0
    try:
        # Handle comma-separated numbers like "1,234"
        if isinstance(value, str):
            value = value.replace(',', '').strip()
        return int(float(value))
    except (ValueError, TypeError):
        return 0


def parse_bool(value: Any) -> bool:
    """Parse a value to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', 'yes', '1', 'y')
    return bool(value)


# Philippine Time offset from UTC
PHT_OFFSET = timedelta(hours=8)


def parse_datetime(value: str) -> Optional[str]:
    """Parse datetime string and convert UTC to Philippine Time (UTC+8)."""
    if not value or value == 'N/A':
        return None

    # Common date formats from Meta exports (all in UTC)
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S%z',
        '%m/%d/%Y %H:%M:%S',
        '%m/%d/%Y %H:%M',
        '%m/%d/%Y %I:%M %p',
        '%d/%m/%Y %H:%M:%S',
        '%Y-%m-%d',
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(value.strip(), fmt)
            # Convert UTC to PHT (+8 hours)
            dt_pht = dt + PHT_OFFSET
            # Return in MM/DD/YYYY HH:MM format for consistency with existing data
            return dt_pht.strftime('%m/%d/%Y %H:%M')
        except ValueError:
            continue

    # If all formats fail, return as-is
    return value


def get_cell(row: List[str], column_map: Dict[str, int], field: str, default: Any = None) -> Any:
    """Get a cell value from a row using the column map."""
    idx = column_map.get(field)
    if idx is None or idx >= len(row):
        return default
    value = row[idx].strip() if row[idx] else default
    return value if value != '' else default


def import_csv(
    file_path: Path,
    mode: str = 'merge',
    page_filter: Optional[str] = None,
    dry_run: bool = False
) -> ImportResult:
    """
    Import a CSV file into the database.

    Args:
        file_path: Path to the CSV file
        mode: Import mode - 'merge' (update existing), 'append' (skip existing), 'replace' (clear first)
        page_filter: Only import posts from pages containing this string
        dry_run: If True, don't actually write to database

    Returns:
        ImportResult with statistics
    """
    result = ImportResult(
        filename=file_path.name,
        file_path=str(file_path),
        page_filter=page_filter
    )

    if not file_path.exists():
        result.status = 'failed'
        result.error_message = f"File not found: {file_path}"
        return result

    # Ensure database is initialized
    if not dry_run:
        ensure_initialized()

    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader)

            # Detect columns
            column_map = detect_columns(header)

            if 'post_id' not in column_map:
                result.status = 'failed'
                result.error_message = "Could not find Post ID column"
                return result

            print(f"Detected columns: {list(column_map.keys())}")

            # Track date range
            dates = []
            pages_seen = set()

            # Process rows
            with db_connection() as conn:
                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Get basic fields
                        post_id = get_cell(row, column_map, 'post_id')
                        if not post_id:
                            result.rows_skipped += 1
                            continue

                        page_id = get_cell(row, column_map, 'page_id', 'unknown')
                        page_name = get_cell(row, column_map, 'page_name', 'Unknown Page')

                        # Apply page filter
                        if page_filter:
                            if page_filter.lower() not in page_name.lower():
                                result.rows_skipped += 1
                                continue

                        # Track pages
                        pages_seen.add((page_id, page_name))

                        # Parse fields
                        publish_time = parse_datetime(get_cell(row, column_map, 'publish_time', ''))
                        if publish_time:
                            try:
                                dt = datetime.fromisoformat(publish_time.replace('Z', '+00:00'))
                                dates.append(dt.date())
                            except ValueError:
                                pass

                        # Check if exists (for mode handling)
                        existing = None
                        if mode != 'replace' and not dry_run:
                            cursor = conn.execute(
                                "SELECT post_id FROM posts WHERE post_id = ?",
                                (post_id,)
                            )
                            existing = cursor.fetchone()

                        if existing and mode == 'append':
                            result.rows_skipped += 1
                            continue

                        if not dry_run:
                            # Upsert page
                            upsert_page(
                                page_id=page_id,
                                page_name=page_name,
                                conn=conn
                            )

                            # Upsert post
                            upsert_post(
                                post_id=post_id,
                                page_id=page_id,
                                title=get_cell(row, column_map, 'title'),
                                description=get_cell(row, column_map, 'description'),
                                post_type=get_cell(row, column_map, 'post_type'),
                                publish_time=publish_time,
                                permalink=get_cell(row, column_map, 'permalink'),
                                is_crosspost=parse_bool(get_cell(row, column_map, 'is_crosspost', False)),
                                is_share=parse_bool(get_cell(row, column_map, 'is_share', False)),
                                duration_sec=parse_int(get_cell(row, column_map, 'duration_sec')),
                                conn=conn
                            )

                            # Insert metrics
                            metric_date = date.today().isoformat()
                            insert_metrics(
                                post_id=post_id,
                                metric_date=metric_date,
                                reactions=parse_int(get_cell(row, column_map, 'reactions')),
                                comments=parse_int(get_cell(row, column_map, 'comments')),
                                shares=parse_int(get_cell(row, column_map, 'shares')),
                                views=parse_int(get_cell(row, column_map, 'views')),
                                reach=parse_int(get_cell(row, column_map, 'reach')),
                                total_clicks=parse_int(get_cell(row, column_map, 'total_clicks')),
                                link_clicks=parse_int(get_cell(row, column_map, 'link_clicks')),
                                other_clicks=parse_int(get_cell(row, column_map, 'other_clicks')),
                                source='csv',
                                conn=conn
                            )

                        if existing:
                            result.rows_updated += 1
                        else:
                            result.rows_imported += 1

                    except Exception as e:
                        print(f"Error on row {row_num}: {e}")
                        result.rows_skipped += 1
                        continue

            # Set date range
            if dates:
                result.date_range_start = min(dates)
                result.date_range_end = max(dates)

            # Record import in history
            if not dry_run and result.total_processed > 0:
                result.import_id = record_import(
                    filename=result.filename,
                    file_path=result.file_path,
                    rows_imported=result.rows_imported,
                    rows_updated=result.rows_updated,
                    rows_skipped=result.rows_skipped,
                    date_range_start=result.date_range_start.isoformat() if result.date_range_start else None,
                    date_range_end=result.date_range_end.isoformat() if result.date_range_end else None,
                    page_filter=page_filter,
                    status='completed'
                )

            result.status = 'completed'
            print(f"\nPages found: {[p[1] for p in pages_seen]}")

    except Exception as e:
        result.status = 'failed'
        result.error_message = str(e)
        import traceback
        traceback.print_exc()

    return result


def import_all_csvs(
    folder: Path,
    mode: str = 'merge',
    page_filter: Optional[str] = None,
    pattern: str = '*.csv'
) -> List[ImportResult]:
    """Import all CSV files from a folder."""
    results = []
    csv_files = list(folder.glob(pattern))

    if not csv_files:
        print(f"No CSV files found in {folder}")
        return results

    print(f"Found {len(csv_files)} CSV files")

    for csv_file in sorted(csv_files):
        print(f"\n--- Importing: {csv_file.name} ---")
        result = import_csv(csv_file, mode=mode, page_filter=page_filter)
        results.append(result)
        print(result)

    return results


def validate_csv(file_path: Path) -> Dict[str, Any]:
    """Validate a CSV file without importing."""
    validation = {
        'valid': False,
        'file': str(file_path),
        'rows': 0,
        'columns_detected': [],
        'columns_missing': [],
        'pages': [],
        'date_range': None,
        'errors': []
    }

    if not file_path.exists():
        validation['errors'].append(f"File not found: {file_path}")
        return validation

    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader)

            column_map = detect_columns(header)
            validation['columns_detected'] = list(column_map.keys())

            # Check required columns
            required = ['post_id', 'page_id', 'page_name']
            for col in required:
                if col not in column_map:
                    validation['columns_missing'].append(col)

            if validation['columns_missing']:
                validation['errors'].append(f"Missing required columns: {validation['columns_missing']}")

            # Count rows and extract info
            pages = set()
            dates = []

            for row in reader:
                validation['rows'] += 1
                page_name = get_cell(row, column_map, 'page_name', 'Unknown')
                pages.add(page_name)

                publish_time = parse_datetime(get_cell(row, column_map, 'publish_time', ''))
                if publish_time:
                    try:
                        dt = datetime.fromisoformat(publish_time.replace('Z', '+00:00'))
                        dates.append(dt.date())
                    except ValueError:
                        pass

            validation['pages'] = list(pages)
            if dates:
                validation['date_range'] = {
                    'start': min(dates).isoformat(),
                    'end': max(dates).isoformat()
                }

            validation['valid'] = len(validation['errors']) == 0

    except Exception as e:
        validation['errors'].append(str(e))

    return validation


def find_new_csvs(downloads_dir: Optional[Path] = None) -> List[Path]:
    """Find new Meta export CSVs in downloads folder."""
    folder = downloads_dir or CSV_DOWNLOADS_DIR
    if not folder.exists():
        return []

    # Common Meta export patterns
    patterns = [
        '*_*_*.csv',  # Date range pattern: Nov-01-2025_Dec-15-2025_xxx.csv
        'Post*.csv',
        'Content*.csv',
        '*export*.csv',
    ]

    found = set()
    for pattern in patterns:
        found.update(folder.glob(pattern))

    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='JuanBabes CSV Importer - Import Meta Business Suite exports'
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Import command
    import_parser = subparsers.add_parser('import', help='Import a CSV file')
    import_parser.add_argument('file', type=Path, help='CSV file to import')
    import_parser.add_argument('--mode', choices=['merge', 'append', 'replace'],
                              default='merge', help='Import mode (default: merge)')
    import_parser.add_argument('--page-filter', type=str, help='Only import posts from matching pages')
    import_parser.add_argument('--dry-run', action='store_true', help='Validate without importing')

    # Import-all command
    import_all_parser = subparsers.add_parser('import-all', help='Import all CSVs from folder')
    import_all_parser.add_argument('folder', type=Path, nargs='?', default=EXPORTS_DIR,
                                   help=f'Folder containing CSVs (default: {EXPORTS_DIR})')
    import_all_parser.add_argument('--mode', choices=['merge', 'append', 'replace'],
                                   default='merge', help='Import mode')
    import_all_parser.add_argument('--page-filter', type=str, help='Only import posts from matching pages')
    import_all_parser.add_argument('--pattern', type=str, default='*.csv', help='File pattern to match')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate a CSV file')
    validate_parser.add_argument('file', type=Path, help='CSV file to validate')

    # History command
    subparsers.add_parser('history', help='Show import history')

    # Stats command
    subparsers.add_parser('stats', help='Show database statistics')

    # Find command
    find_parser = subparsers.add_parser('find', help='Find new CSVs in Downloads')
    find_parser.add_argument('--folder', type=Path, help='Folder to search')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'import':
        result = import_csv(
            args.file,
            mode=args.mode,
            page_filter=args.page_filter,
            dry_run=args.dry_run
        )
        print(f"\n{result}")
        if result.status == 'failed':
            print(f"Error: {result.error_message}")
            sys.exit(1)

    elif args.command == 'import-all':
        results = import_all_csvs(
            args.folder,
            mode=args.mode,
            page_filter=args.page_filter,
            pattern=args.pattern
        )
        print(f"\n=== Summary ===")
        total_imported = sum(r.rows_imported for r in results)
        total_updated = sum(r.rows_updated for r in results)
        total_skipped = sum(r.rows_skipped for r in results)
        print(f"Files processed: {len(results)}")
        print(f"Total imported: {total_imported}")
        print(f"Total updated: {total_updated}")
        print(f"Total skipped: {total_skipped}")

    elif args.command == 'validate':
        result = validate_csv(args.file)
        print(f"\nValidation Results for: {args.file}")
        print(f"  Valid: {result['valid']}")
        print(f"  Rows: {result['rows']}")
        print(f"  Columns detected: {result['columns_detected']}")
        if result['columns_missing']:
            print(f"  Missing columns: {result['columns_missing']}")
        print(f"  Pages: {result['pages']}")
        if result['date_range']:
            print(f"  Date range: {result['date_range']['start']} to {result['date_range']['end']}")
        if result['errors']:
            print(f"  Errors: {result['errors']}")

    elif args.command == 'history':
        ensure_initialized()
        history = get_import_history()
        print("\nRecent Imports:")
        print("-" * 80)
        for h in history:
            print(f"  {h['import_date'][:19]}: {h['filename']}")
            print(f"    Imported: {h['rows_imported']}, Updated: {h['rows_updated']}, "
                  f"Skipped: {h['rows_skipped']}")
            if h['date_range_start']:
                print(f"    Date range: {h['date_range_start']} to {h['date_range_end']}")
            print()

    elif args.command == 'stats':
        ensure_initialized()
        stats = get_database_stats()
        print("\nDatabase Statistics:")
        print("-" * 40)
        print(f"  Pages: {stats['page_count']}")
        print(f"  Posts: {stats['post_count']}")
        print(f"  Metrics Records: {stats['metrics_count']}")
        print(f"  Date Range: {stats['earliest_post'] or 'N/A'} to {stats['latest_post'] or 'N/A'}")
        print(f"  Imports: {stats['import_count']}")
        print(f"  Database Size: {stats['db_size_mb']} MB")

    elif args.command == 'find':
        folder = args.folder if hasattr(args, 'folder') and args.folder else None
        csvs = find_new_csvs(folder)
        if csvs:
            print(f"\nFound {len(csvs)} CSV files:")
            for csv_file in csvs[:10]:  # Show top 10
                size_kb = csv_file.stat().st_size / 1024
                mtime = datetime.fromtimestamp(csv_file.stat().st_mtime)
                print(f"  {csv_file.name} ({size_kb:.1f} KB, {mtime:%Y-%m-%d %H:%M})")
        else:
            print("No CSV files found")


if __name__ == '__main__':
    main()
