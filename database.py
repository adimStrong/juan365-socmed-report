"""
Juan365 Socmed Report Database Module
SQLite database connection and schema management
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

# Database configuration
DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "juan365_socmed.db"
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_db_path() -> Path:
    """Get the database file path, creating directory if needed."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return DB_PATH


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Get a database connection with row factory enabled.

    Args:
        db_path: Optional custom database path

    Returns:
        SQLite connection object
    """
    path = db_path or get_db_path()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_connection(db_path: Optional[Path] = None):
    """
    Context manager for database connections.

    Usage:
        with db_connection() as conn:
            cursor = conn.execute("SELECT * FROM posts")
    """
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database(db_path: Optional[Path] = None) -> bool:
    """
    Initialize the database with the schema from migrations.

    Args:
        db_path: Optional custom database path

    Returns:
        True if successful
    """
    schema_file = MIGRATIONS_DIR / "001_initial_schema.sql"

    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")

    with open(schema_file, 'r') as f:
        schema_sql = f.read()

    with db_connection(db_path) as conn:
        conn.executescript(schema_sql)
        print(f"Database initialized at: {db_path or get_db_path()}")

    return True


def is_initialized(db_path: Optional[Path] = None) -> bool:
    """Check if the database has been initialized with tables."""
    path = db_path or get_db_path()
    if not path.exists():
        return False

    with db_connection(path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='posts'"
        )
        return cursor.fetchone() is not None


def ensure_initialized(db_path: Optional[Path] = None) -> None:
    """Initialize database if not already done."""
    if not is_initialized(db_path):
        init_database(db_path)


# =============================================================================
# Page Operations
# =============================================================================

def upsert_page(
    page_id: str,
    page_name: str,
    page_url: Optional[str] = None,
    fan_count: Optional[int] = None,
    followers_count: Optional[int] = None,
    talking_about_count: Optional[int] = None,
    overall_star_rating: Optional[float] = None,
    rating_count: Optional[int] = None,
    is_competitor: bool = False,
    conn: Optional[sqlite3.Connection] = None
) -> None:
    """Insert or update a page record."""
    sql = """
        INSERT INTO pages (
            page_id, page_name, page_url, fan_count, followers_count,
            talking_about_count, overall_star_rating, rating_count,
            is_competitor, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(page_id) DO UPDATE SET
            page_name = excluded.page_name,
            page_url = COALESCE(excluded.page_url, page_url),
            fan_count = COALESCE(excluded.fan_count, fan_count),
            followers_count = COALESCE(excluded.followers_count, followers_count),
            talking_about_count = COALESCE(excluded.talking_about_count, talking_about_count),
            overall_star_rating = COALESCE(excluded.overall_star_rating, overall_star_rating),
            rating_count = COALESCE(excluded.rating_count, rating_count),
            is_competitor = excluded.is_competitor,
            updated_at = excluded.updated_at
    """

    def execute(c):
        c.execute(sql, (
            page_id, page_name, page_url, fan_count, followers_count,
            talking_about_count, overall_star_rating, rating_count,
            is_competitor, datetime.now().isoformat()
        ))

    if conn:
        execute(conn)
    else:
        with db_connection() as c:
            execute(c)


def get_page(page_id: str) -> Optional[Dict[str, Any]]:
    """Get a page by ID."""
    with db_connection() as conn:
        cursor = conn.execute("SELECT * FROM pages WHERE page_id = ?", (page_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_pages(include_competitors: bool = True) -> List[Dict[str, Any]]:
    """Get all pages."""
    with db_connection() as conn:
        if include_competitors:
            cursor = conn.execute("SELECT * FROM pages ORDER BY page_name")
        else:
            cursor = conn.execute(
                "SELECT * FROM pages WHERE is_competitor = 0 ORDER BY page_name"
            )
        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# Post Operations
# =============================================================================

def upsert_post(
    post_id: str,
    page_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    post_type: Optional[str] = None,
    publish_time: Optional[str] = None,
    permalink: Optional[str] = None,
    is_crosspost: bool = False,
    is_share: bool = False,
    duration_sec: Optional[int] = None,
    conn: Optional[sqlite3.Connection] = None
) -> None:
    """Insert or update a post record."""
    sql = """
        INSERT INTO posts (
            post_id, page_id, title, description, post_type,
            publish_time, permalink, is_crosspost, is_share, duration_sec
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(post_id) DO UPDATE SET
            title = COALESCE(excluded.title, title),
            description = COALESCE(excluded.description, description),
            post_type = COALESCE(excluded.post_type, post_type),
            publish_time = COALESCE(excluded.publish_time, publish_time),
            permalink = COALESCE(excluded.permalink, permalink),
            is_crosspost = excluded.is_crosspost,
            is_share = excluded.is_share,
            duration_sec = COALESCE(excluded.duration_sec, duration_sec)
    """

    def execute(c):
        c.execute(sql, (
            post_id, page_id, title, description, post_type,
            publish_time, permalink, is_crosspost, is_share, duration_sec
        ))

    if conn:
        execute(conn)
    else:
        with db_connection() as c:
            execute(c)


def get_post(post_id: str) -> Optional[Dict[str, Any]]:
    """Get a post by ID with latest metrics."""
    with db_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM enhanced_metrics WHERE post_id = ?",
            (post_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_posts(
    page_id: Optional[str] = None,
    post_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 1000,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get posts with optional filters."""
    conditions = []
    params = []

    if page_id:
        conditions.append("page_id = ?")
        params.append(page_id)
    if post_type:
        conditions.append("post_type = ?")
        params.append(post_type)
    if start_date:
        conditions.append("DATE(publish_time) >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("DATE(publish_time) <= ?")
        params.append(end_date)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    sql = f"""
        SELECT * FROM enhanced_metrics
        WHERE {where_clause}
        ORDER BY publish_time DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    with db_connection() as conn:
        cursor = conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def get_post_count(page_id: Optional[str] = None) -> int:
    """Get total post count."""
    with db_connection() as conn:
        if page_id:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM posts WHERE page_id = ?",
                (page_id,)
            )
        else:
            cursor = conn.execute("SELECT COUNT(*) FROM posts")
        return cursor.fetchone()[0]


# =============================================================================
# Metrics Operations
# =============================================================================

def insert_metrics(
    post_id: str,
    metric_date: str,
    reactions: int = 0,
    comments: int = 0,
    shares: int = 0,
    views: int = 0,
    reach: int = 0,
    total_clicks: int = 0,
    link_clicks: int = 0,
    other_clicks: int = 0,
    like_count: int = 0,
    love_count: int = 0,
    haha_count: int = 0,
    wow_count: int = 0,
    sad_count: int = 0,
    angry_count: int = 0,
    source: str = 'csv',
    conn: Optional[sqlite3.Connection] = None
) -> None:
    """Insert metrics for a post (update if exists for same date/source)."""
    sql = """
        INSERT INTO post_metrics (
            post_id, metric_date, reactions, comments, shares, views, reach,
            total_clicks, link_clicks, other_clicks,
            like_count, love_count, haha_count, wow_count, sad_count, angry_count,
            source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(post_id, metric_date, source) DO UPDATE SET
            reactions = excluded.reactions,
            comments = excluded.comments,
            shares = excluded.shares,
            views = excluded.views,
            reach = excluded.reach,
            total_clicks = excluded.total_clicks,
            link_clicks = excluded.link_clicks,
            other_clicks = excluded.other_clicks,
            like_count = excluded.like_count,
            love_count = excluded.love_count,
            haha_count = excluded.haha_count,
            wow_count = excluded.wow_count,
            sad_count = excluded.sad_count,
            angry_count = excluded.angry_count
    """

    def execute(c):
        c.execute(sql, (
            post_id, metric_date, reactions, comments, shares, views, reach,
            total_clicks, link_clicks, other_clicks,
            like_count, love_count, haha_count, wow_count, sad_count, angry_count,
            source
        ))

    if conn:
        execute(conn)
    else:
        with db_connection() as c:
            execute(c)


# =============================================================================
# Sync Metrics to Posts
# =============================================================================

def sync_metrics_to_posts():
    """
    Update posts table with latest metrics from post_metrics.
    This ensures the posts table has up-to-date engagement data.

    Note: API post_ids have format 'pageId_postId', CSV post_ids are just 'postId'.
    We match by extracting the postId part after the underscore.
    """
    sql = """
        UPDATE posts
        SET
            reactions_total = COALESCE((
                SELECT pm.reactions FROM post_metrics pm
                WHERE pm.post_id = SUBSTR(posts.post_id, INSTR(posts.post_id, '_') + 1)
                   OR pm.post_id = posts.post_id
                ORDER BY pm.metric_date DESC LIMIT 1
            ), reactions_total, 0),
            comments_count = COALESCE((
                SELECT pm.comments FROM post_metrics pm
                WHERE pm.post_id = SUBSTR(posts.post_id, INSTR(posts.post_id, '_') + 1)
                   OR pm.post_id = posts.post_id
                ORDER BY pm.metric_date DESC LIMIT 1
            ), comments_count, 0),
            shares_count = COALESCE((
                SELECT pm.shares FROM post_metrics pm
                WHERE pm.post_id = SUBSTR(posts.post_id, INSTR(posts.post_id, '_') + 1)
                   OR pm.post_id = posts.post_id
                ORDER BY pm.metric_date DESC LIMIT 1
            ), shares_count, 0),
            views_count = COALESCE((
                SELECT pm.views FROM post_metrics pm
                WHERE pm.post_id = SUBSTR(posts.post_id, INSTR(posts.post_id, '_') + 1)
                   OR pm.post_id = posts.post_id
                ORDER BY pm.metric_date DESC LIMIT 1
            ), views_count, 0),
            reach_count = COALESCE((
                SELECT pm.reach FROM post_metrics pm
                WHERE pm.post_id = SUBSTR(posts.post_id, INSTR(posts.post_id, '_') + 1)
                   OR pm.post_id = posts.post_id
                ORDER BY pm.metric_date DESC LIMIT 1
            ), reach_count, 0),
            total_engagement = COALESCE((
                SELECT pm.reactions + pm.comments + pm.shares FROM post_metrics pm
                WHERE pm.post_id = SUBSTR(posts.post_id, INSTR(posts.post_id, '_') + 1)
                   OR pm.post_id = posts.post_id
                ORDER BY pm.metric_date DESC LIMIT 1
            ), total_engagement, 0)
        WHERE EXISTS (
            SELECT 1 FROM post_metrics pm
            WHERE pm.post_id = SUBSTR(posts.post_id, INSTR(posts.post_id, '_') + 1)
               OR pm.post_id = posts.post_id
        )
    """
    with db_connection() as conn:
        cursor = conn.execute(sql)
        updated = cursor.rowcount
        print(f"Synced metrics to {updated} posts")
        return updated


# =============================================================================
# Import History Operations
# =============================================================================

def record_import(
    filename: str,
    file_path: Optional[str] = None,
    rows_imported: int = 0,
    rows_updated: int = 0,
    rows_skipped: int = 0,
    date_range_start: Optional[str] = None,
    date_range_end: Optional[str] = None,
    page_filter: Optional[str] = None,
    status: str = 'completed'
) -> int:
    """Record a CSV import in history."""
    sql = """
        INSERT INTO csv_imports (
            filename, file_path, rows_imported, rows_updated, rows_skipped,
            date_range_start, date_range_end, page_filter, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    with db_connection() as conn:
        cursor = conn.execute(sql, (
            filename, file_path, rows_imported, rows_updated, rows_skipped,
            date_range_start, date_range_end, page_filter, status
        ))
        return cursor.lastrowid


def get_import_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent import history."""
    with db_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM csv_imports ORDER BY import_date DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# Analytics Queries
# =============================================================================

def get_daily_engagement(
    page_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get daily engagement summary."""
    conditions = []
    params = []

    if page_id:
        conditions.append("page_id = ?")
        params.append(page_id)
    if start_date:
        conditions.append("post_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("post_date <= ?")
        params.append(end_date)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    sql = f"""
        SELECT * FROM daily_engagement
        WHERE {where_clause}
        ORDER BY post_date DESC
    """

    with db_connection() as conn:
        cursor = conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def get_post_type_performance(page_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get performance metrics by post type."""
    with db_connection() as conn:
        if page_id:
            cursor = conn.execute(
                "SELECT * FROM post_type_performance WHERE page_id = ?",
                (page_id,)
            )
        else:
            cursor = conn.execute("SELECT * FROM post_type_performance")
        return [dict(row) for row in cursor.fetchall()]


def get_database_stats() -> Dict[str, Any]:
    """Get database statistics."""
    with db_connection() as conn:
        stats = {}

        # Page count
        cursor = conn.execute("SELECT COUNT(*) FROM pages")
        stats['page_count'] = cursor.fetchone()[0]

        # Post count
        cursor = conn.execute("SELECT COUNT(*) FROM posts")
        stats['post_count'] = cursor.fetchone()[0]

        # Metrics count
        cursor = conn.execute("SELECT COUNT(*) FROM post_metrics")
        stats['metrics_count'] = cursor.fetchone()[0]

        # Date range
        cursor = conn.execute("""
            SELECT MIN(publish_time) as earliest, MAX(publish_time) as latest
            FROM posts
        """)
        row = cursor.fetchone()
        stats['earliest_post'] = row['earliest']
        stats['latest_post'] = row['latest']

        # Import history count
        cursor = conn.execute("SELECT COUNT(*) FROM csv_imports")
        stats['import_count'] = cursor.fetchone()[0]

        # Database file size
        db_path = get_db_path()
        if db_path.exists():
            stats['db_size_mb'] = round(db_path.stat().st_size / (1024 * 1024), 2)
        else:
            stats['db_size_mb'] = 0

        return stats


# =============================================================================
# CLI Commands
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python database.py <command>")
        print("Commands:")
        print("  init     - Initialize database")
        print("  stats    - Show database statistics")
        print("  history  - Show import history")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        init_database()
        print("Database initialized successfully!")

    elif command == "stats":
        ensure_initialized()
        stats = get_database_stats()
        print("\nDatabase Statistics:")
        print(f"  Pages: {stats['page_count']}")
        print(f"  Posts: {stats['post_count']}")
        print(f"  Metrics Records: {stats['metrics_count']}")
        print(f"  Date Range: {stats['earliest_post']} to {stats['latest_post']}")
        print(f"  Imports: {stats['import_count']}")
        print(f"  Database Size: {stats['db_size_mb']} MB")

    elif command == "history":
        ensure_initialized()
        history = get_import_history()
        print("\nRecent Imports:")
        for h in history:
            print(f"  {h['import_date']}: {h['filename']} - "
                  f"{h['rows_imported']} imported, {h['rows_updated']} updated")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
