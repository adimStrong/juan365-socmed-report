#!/usr/bin/env python3
"""
Export static JSON data for Vercel deployment.

Run this after importing new CSV data to update the Vercel deployment.
The output goes to frontend/public/data/analytics.json

Usage:
    python export_static_data.py
"""

import json
import sqlite3
import os
from datetime import datetime, timedelta
from database import sync_metrics_to_posts

DATABASE_PATH = "data/juan365_socmed.db"
OUTPUT_PATH = "frontend/public/data/analytics.json"
HISTORY_PATH = "data/analytics_history.json"

def get_last_complete_week_end():
    """Get the end date of the last complete week (Saturday before current week)."""
    today = datetime.now()
    # Find Monday of current week
    days_since_monday = today.weekday()
    current_week_start = today - timedelta(days=days_since_monday)
    # Last complete week ended on Sunday before current week started
    last_complete_week_end = current_week_start - timedelta(days=1)
    return last_complete_week_end.strftime("%Y-%m-%d")

# Analytics Report Page: Compare Juan365 vs Live Stream (Dec-Jan period)
JUAN365_PAGE_IDS = [
    "61572881214141",  # Juan365 (1105 posts)
    "580104038511364", # Juan365 (61 posts)
]
LIVE_STREAM_PAGE_IDS = [
    "61569634500241",  # Juan365 Live Stream (818 posts)
    "481447078389174", # Juan365 Live Stream (57 posts)
]
ANALYSIS_PAGE_IDS = JUAN365_PAGE_IDS + LIVE_STREAM_PAGE_IDS  # All for combined queries
ANALYSIS_START_DATE = "2025-12-01"
# Use dynamic end date to exclude incomplete current week
ANALYSIS_END_DATE = get_last_complete_week_end()


def get_conn():
    return sqlite3.connect(DATABASE_PATH, timeout=30)


def export_stats():
    """Export dashboard stats (all pages + per-page)."""
    conn = get_conn()
    cursor = conn.cursor()

    # Get all pages first
    cursor.execute("SELECT DISTINCT page_id FROM posts WHERE reactions_total > 0")
    page_ids = [row[0] for row in cursor.fetchall()]

    # Aggregate stats
    cursor.execute("""
        SELECT
            COALESCE(SUM(reactions_total), 0) as total_reactions,
            COALESCE(SUM(comments_count), 0) as total_comments,
            COALESCE(SUM(shares_count), 0) as total_shares,
            COALESCE(SUM(total_engagement), 0) as total_engagement,
            COALESCE(SUM(pes), 0) as total_pes,
            COUNT(*) as total_posts,
            COALESCE(SUM(views_count), 0) as total_views,
            COALESCE(SUM(reach_count), 0) as total_reach
        FROM posts
        WHERE reactions_total > 0 OR comments_count > 0 OR shares_count > 0
    """)
    row = cursor.fetchone()

    cursor.execute("""
        SELECT MIN(publish_time), MAX(publish_time)
        FROM posts WHERE publish_time IS NOT NULL
    """)
    dates = cursor.fetchone()

    cursor.execute("SELECT COUNT(DISTINCT page_id) FROM posts WHERE reactions_total > 0")
    active_pages = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pages")
    total_pages_count = cursor.fetchone()[0]

    post_count = row[5]
    total_engagement = row[3]
    total_pes = row[4]
    total_views = row[6]
    total_reach = row[7]

    all_stats = {
        "total_posts": post_count,
        "total_pages": active_pages,
        "all_pages": total_pages_count,
        "total_reactions": row[0],
        "total_comments": row[1],
        "total_shares": row[2],
        "total_engagement": total_engagement,
        "total_pes": round(total_pes, 1),
        "total_views": total_views,
        "total_reach": total_reach,
        "avg_engagement": round(total_engagement / post_count, 1) if post_count > 0 else 0,
        "avg_pes": round(total_pes / post_count, 1) if post_count > 0 else 0,
        "avg_views": round(total_views / post_count, 1) if post_count > 0 else 0,
        "avg_reach": round(total_reach / post_count, 1) if post_count > 0 else 0,
        "date_range_start": str(dates[0])[:10] if dates[0] else None,
        "date_range_end": str(dates[1])[:10] if dates[1] else None,
    }

    # Per-page stats
    by_page = {}
    for page_id in page_ids:
        cursor.execute("""
            SELECT
                COALESCE(SUM(reactions_total), 0) as total_reactions,
                COALESCE(SUM(comments_count), 0) as total_comments,
                COALESCE(SUM(shares_count), 0) as total_shares,
                COALESCE(SUM(total_engagement), 0) as total_engagement,
                COALESCE(SUM(pes), 0) as total_pes,
                COUNT(*) as total_posts,
                COALESCE(SUM(views_count), 0) as total_views,
                COALESCE(SUM(reach_count), 0) as total_reach
            FROM posts
            WHERE page_id = ? AND (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
        """, (page_id,))
        prow = cursor.fetchone()

        cursor.execute("""
            SELECT MIN(publish_time), MAX(publish_time)
            FROM posts WHERE page_id = ? AND publish_time IS NOT NULL
        """, (page_id,))
        pdates = cursor.fetchone()

        ppost_count = prow[5]
        ptotal_engagement = prow[3]
        ptotal_pes = prow[4]
        ptotal_views = prow[6]
        ptotal_reach = prow[7]

        by_page[page_id] = {
            "total_posts": ppost_count,
            "total_pages": 1,
            "all_pages": 1,
            "total_reactions": prow[0],
            "total_comments": prow[1],
            "total_shares": prow[2],
            "total_engagement": ptotal_engagement,
            "total_pes": round(ptotal_pes, 1),
            "total_views": ptotal_views,
            "total_reach": ptotal_reach,
            "avg_engagement": round(ptotal_engagement / ppost_count, 1) if ppost_count > 0 else 0,
            "avg_pes": round(ptotal_pes / ppost_count, 1) if ppost_count > 0 else 0,
            "avg_views": round(ptotal_views / ppost_count, 1) if ppost_count > 0 else 0,
            "avg_reach": round(ptotal_reach / ppost_count, 1) if ppost_count > 0 else 0,
            "date_range_start": str(pdates[0])[:10] if pdates[0] else None,
            "date_range_end": str(pdates[1])[:10] if pdates[1] else None,
        }

    conn.close()
    return {"all": all_stats, "byPage": by_page}


def export_pages():
    """Export page comparison data."""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            pg.page_id,
            pg.page_name,
            pg.fan_count,
            pg.followers_count,
            COUNT(p.post_id) as post_count,
            COALESCE(SUM(p.reactions_total), 0) as total_reactions,
            COALESCE(SUM(p.comments_count), 0) as total_comments,
            COALESCE(SUM(p.shares_count), 0) as total_shares,
            COALESCE(SUM(p.total_engagement), 0) as total_engagement,
            COALESCE(AVG(p.pes), 0) as avg_pes,
            COALESCE(SUM(p.views_count), 0) as total_views,
            COALESCE(SUM(p.reach_count), 0) as total_reach
        FROM pages pg
        LEFT JOIN posts p ON pg.page_id = p.page_id
            AND (p.reactions_total > 0 OR p.comments_count > 0 OR p.shares_count > 0)
        GROUP BY pg.page_id
        HAVING COUNT(p.post_id) > 0
        ORDER BY total_engagement DESC
    """)

    result = []
    for row in cursor.fetchall():
        post_count = row[4]
        total_engagement = row[8]
        result.append({
            "page_id": row[0],
            "name": row[1],  # For frontend compatibility
            "page_name": row[1],
            "fan_count": row[2],
            "followers_count": row[3],
            "post_count": post_count,
            "total_reactions": row[5],
            "total_comments": row[6],
            "total_shares": row[7],
            "total_engagement": total_engagement,
            "avg_engagement": round(total_engagement / post_count, 1) if post_count > 0 else 0,
            "avg_reach": round(row[11] / post_count, 1) if post_count > 0 else 0,
            "total_views": row[10],
            "total_reach": row[11]
        })

    conn.close()
    return result


def export_post_types():
    """Export post type statistics (all pages + per-page)."""
    conn = get_conn()
    cursor = conn.cursor()

    # Get all pages first
    cursor.execute("SELECT DISTINCT page_id FROM posts WHERE reactions_total > 0")
    page_ids = [row[0] for row in cursor.fetchall()]

    # Aggregate post types
    cursor.execute("""
        SELECT
            COALESCE(post_type, 'Unknown') as post_type,
            COUNT(*) as count,
            COALESCE(SUM(reactions_total), 0) as reactions,
            COALESCE(SUM(comments_count), 0) as comments,
            COALESCE(SUM(shares_count), 0) as shares,
            COALESCE(SUM(total_engagement), 0) as total_engagement,
            COALESCE(AVG(pes), 0) as avg_pes
        FROM posts
        WHERE reactions_total > 0 OR comments_count > 0 OR shares_count > 0
        GROUP BY post_type
        ORDER BY count DESC
    """)

    all_types = []
    for row in cursor.fetchall():
        count = row[1]
        total_engagement = row[5]
        all_types.append({
            "post_type": row[0],
            "count": count,
            "reactions": row[2],
            "comments": row[3],
            "shares": row[4],
            "total_engagement": total_engagement,
            "avg_engagement": round(total_engagement / count, 1) if count > 0 else 0,
            "avg_pes": round(row[6], 1)
        })

    # Per-page post types
    by_page = {}
    for page_id in page_ids:
        cursor.execute("""
            SELECT
                COALESCE(post_type, 'Unknown') as post_type,
                COUNT(*) as count,
                COALESCE(SUM(reactions_total), 0) as reactions,
                COALESCE(SUM(comments_count), 0) as comments,
                COALESCE(SUM(shares_count), 0) as shares,
                COALESCE(SUM(total_engagement), 0) as total_engagement,
                COALESCE(AVG(pes), 0) as avg_pes
            FROM posts
            WHERE page_id = ? AND (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
            GROUP BY post_type
            ORDER BY count DESC
        """, (page_id,))

        page_types = []
        for row in cursor.fetchall():
            count = row[1]
            total_engagement = row[5]
            page_types.append({
                "post_type": row[0],
                "count": count,
                "reactions": row[2],
                "comments": row[3],
                "shares": row[4],
                "total_engagement": total_engagement,
                "avg_engagement": round(total_engagement / count, 1) if count > 0 else 0,
                "avg_pes": round(row[6], 1)
            })
        by_page[page_id] = page_types

    conn.close()
    return {"all": all_types, "byPage": by_page}


def export_daily():
    """Export daily engagement data (all pages + per-page)."""
    conn = get_conn()
    cursor = conn.cursor()

    # Get all pages first
    cursor.execute("SELECT DISTINCT page_id FROM posts WHERE reactions_total > 0")
    page_ids = [row[0] for row in cursor.fetchall()]

    # Handle both date formats:
    # CSV format: "10/01/2025 00:01" -> "2025-10-01"
    # ISO format: "2025-10-01T00:01:00" -> "2025-10-01"
    date_expr = """CASE
        WHEN publish_time LIKE '____-__-__%' THEN substr(publish_time, 1, 10)
        ELSE substr(publish_time, 7, 4) || '-' || substr(publish_time, 1, 2) || '-' || substr(publish_time, 4, 2)
    END"""

    # Aggregate daily data
    cursor.execute(f"""
        SELECT
            {date_expr} as post_date,
            COUNT(*) as post_count,
            COALESCE(SUM(reactions_total), 0) as reactions,
            COALESCE(SUM(comments_count), 0) as comments,
            COALESCE(SUM(shares_count), 0) as shares,
            COALESCE(SUM(total_engagement), 0) as engagement,
            COALESCE(SUM(pes), 0) as pes,
            COALESCE(SUM(views_count), 0) as views,
            COALESCE(SUM(reach_count), 0) as reach
        FROM posts
        WHERE publish_time IS NOT NULL
            AND (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
        GROUP BY {date_expr}
        ORDER BY post_date
    """)

    all_daily = []
    for row in cursor.fetchall():
        all_daily.append({
            "date": row[0],
            "posts": row[1],
            "reactions": row[2],
            "comments": row[3],
            "shares": row[4],
            "engagement": row[5],
            "pes": round(row[6], 1),
            "views": row[7],
            "reach": row[8]
        })

    # Per-page daily data
    by_page = {}
    for page_id in page_ids:
        cursor.execute(f"""
            SELECT
                {date_expr} as post_date,
                COUNT(*) as post_count,
                COALESCE(SUM(reactions_total), 0) as reactions,
                COALESCE(SUM(comments_count), 0) as comments,
                COALESCE(SUM(shares_count), 0) as shares,
                COALESCE(SUM(total_engagement), 0) as engagement,
                COALESCE(SUM(pes), 0) as pes,
                COALESCE(SUM(views_count), 0) as views,
                COALESCE(SUM(reach_count), 0) as reach
            FROM posts
            WHERE page_id = ? AND publish_time IS NOT NULL
                AND (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
            GROUP BY {date_expr}
            ORDER BY post_date
        """, (page_id,))

        page_daily = []
        for row in cursor.fetchall():
            page_daily.append({
                "date": row[0],
                "posts": row[1],
                "reactions": row[2],
                "comments": row[3],
                "shares": row[4],
                "engagement": row[5],
                "pes": round(row[6], 1),
                "views": row[7],
                "reach": row[8]
            })
        by_page[page_id] = page_daily

    conn.close()
    return {"all": all_daily, "byPage": by_page}


def export_time_series():
    """Export time series data: monthly, weekly, and day-of-week analytics."""
    conn = get_conn()
    cursor = conn.cursor()

    # Handle both date formats:
    # CSV format: "10/01/2025 00:01" -> "2025-10-01"
    # ISO format: "2025-10-01T00:01:00" -> "2025-10-01"
    date_expr = """CASE
        WHEN publish_time LIKE '____-__-__%' THEN substr(publish_time, 1, 10)
        ELSE substr(publish_time, 7, 4) || '-' || substr(publish_time, 1, 2) || '-' || substr(publish_time, 4, 2)
    END"""
    month_expr = """CASE
        WHEN publish_time LIKE '____-__-__%' THEN substr(publish_time, 1, 7)
        ELSE substr(publish_time, 7, 4) || '-' || substr(publish_time, 1, 2)
    END"""

    # Monthly data
    cursor.execute(f"""
        SELECT
            {month_expr} as month,
            COUNT(*) as post_count,
            COALESCE(SUM(reactions_total), 0) as reactions,
            COALESCE(SUM(comments_count), 0) as comments,
            COALESCE(SUM(shares_count), 0) as shares,
            COALESCE(SUM(views_count), 0) as views,
            COALESCE(SUM(reach_count), 0) as reach,
            COALESCE(SUM(total_engagement), 0) as engagement,
            COALESCE(AVG(total_engagement), 0) as avg_engagement
        FROM posts
        WHERE publish_time IS NOT NULL
            AND (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
        GROUP BY {month_expr}
        ORDER BY month DESC
        LIMIT 6
    """)

    monthly = []
    prev_engagement = None
    rows = list(cursor.fetchall())
    for row in reversed(rows):  # Oldest first for MoM calculation
        engagement = row[7]
        mom_change = None
        if prev_engagement and prev_engagement > 0:
            mom_change = round(((engagement - prev_engagement) / prev_engagement) * 100, 1)
        monthly.append({
            "month": row[0],
            "posts": row[1],
            "reactions": row[2],
            "comments": row[3],
            "shares": row[4],
            "views": row[5],
            "reach": row[6],
            "engagement": engagement,
            "avg_engagement": round(row[8], 1),
            "mom_change": mom_change
        })
        prev_engagement = engagement

    # Weekly data (last 4 weeks)
    # Week expression: use strftime on the converted ISO date
    week_expr = f"strftime('%Y-%W', {date_expr})"
    cursor.execute(f"""
        SELECT
            {week_expr} as week,
            MIN({date_expr}) as week_start,
            MAX({date_expr}) as week_end,
            COUNT(*) as post_count,
            COALESCE(SUM(reactions_total), 0) as reactions,
            COALESCE(SUM(comments_count), 0) as comments,
            COALESCE(SUM(shares_count), 0) as shares,
            COALESCE(SUM(views_count), 0) as views,
            COALESCE(SUM(reach_count), 0) as reach,
            COALESCE(SUM(total_engagement), 0) as engagement,
            COALESCE(AVG(total_engagement), 0) as avg_engagement
        FROM posts
        WHERE publish_time IS NOT NULL
            AND {date_expr} >= DATE('now', '-28 days')
            AND (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
        GROUP BY {week_expr}
        ORDER BY week DESC
        LIMIT 4
    """)

    weekly = []
    prev_weekly_engagement = None
    rows = list(cursor.fetchall())
    for row in reversed(rows):  # Oldest first for WoW calculation
        engagement = row[9]
        wow_change = None
        if prev_weekly_engagement and prev_weekly_engagement > 0:
            wow_change = round(((engagement - prev_weekly_engagement) / prev_weekly_engagement) * 100, 1)
        weekly.append({
            "week": row[0],
            "week_start": row[1],
            "week_end": row[2],
            "posts": row[3],
            "reactions": row[4],
            "comments": row[5],
            "shares": row[6],
            "views": row[7],
            "reach": row[8],
            "engagement": engagement,
            "avg_engagement": round(row[10], 1),
            "wow_change": wow_change
        })
        prev_weekly_engagement = engagement

    # Day of week analysis
    dow_expr = f"CAST(strftime('%w', {date_expr}) AS INTEGER)"
    cursor.execute(f"""
        SELECT
            CASE {dow_expr}
                WHEN 0 THEN 'Sun'
                WHEN 1 THEN 'Mon'
                WHEN 2 THEN 'Tue'
                WHEN 3 THEN 'Wed'
                WHEN 4 THEN 'Thu'
                WHEN 5 THEN 'Fri'
                WHEN 6 THEN 'Sat'
            END as day_name,
            {dow_expr} as day_num,
            COUNT(*) as post_count,
            COALESCE(SUM(total_engagement), 0) as total_engagement,
            COALESCE(AVG(total_engagement), 0) as avg_engagement,
            COALESCE(SUM(views_count), 0) as views,
            COALESCE(SUM(reach_count), 0) as reach
        FROM posts
        WHERE publish_time IS NOT NULL
            AND (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
        GROUP BY day_num
        ORDER BY day_num
    """)

    day_of_week = []
    max_avg = 0
    rows = list(cursor.fetchall())
    for row in rows:
        avg_eng = row[4]
        if avg_eng > max_avg:
            max_avg = avg_eng

    for row in rows:
        avg_eng = row[4]
        day_of_week.append({
            "day": row[0],
            "day_num": row[1],
            "posts": row[2],
            "total_engagement": row[3],
            "avg_engagement": round(avg_eng, 1),
            "views": row[5],
            "reach": row[6],
            "is_best": avg_eng == max_avg
        })

    # Page rankings (sorted by engagement)
    cursor.execute("""
        SELECT
            pg.page_id,
            pg.page_name,
            COUNT(p.post_id) as post_count,
            COALESCE(SUM(p.views_count), 0) as views,
            COALESCE(SUM(p.reach_count), 0) as reach,
            COALESCE(SUM(p.total_engagement), 0) as engagement,
            COALESCE(AVG(p.total_engagement), 0) as avg_engagement
        FROM pages pg
        LEFT JOIN posts p ON pg.page_id = p.page_id
            AND (p.reactions_total > 0 OR p.comments_count > 0 OR p.shares_count > 0)
        GROUP BY pg.page_id
        HAVING COUNT(p.post_id) > 0
        ORDER BY engagement DESC
    """)

    page_rankings = []
    for i, row in enumerate(cursor.fetchall()):
        page_rankings.append({
            "rank": i + 1,
            "page_id": row[0],
            "name": row[1],  # For frontend compatibility
            "page_name": row[1],
            "posts": row[2],
            "views": row[3],
            "reach": row[4],
            "engagement": row[5],
            "avg_engagement": round(row[6], 1)
        })

    # Post type performance
    cursor.execute("""
        SELECT
            COALESCE(post_type, 'Unknown') as post_type,
            COUNT(*) as count,
            COALESCE(SUM(views_count), 0) as views,
            COALESCE(SUM(reach_count), 0) as reach,
            COALESCE(SUM(total_engagement), 0) as engagement,
            COALESCE(AVG(total_engagement), 0) as avg_engagement,
            COALESCE(AVG(views_count), 0) as avg_views
        FROM posts
        WHERE reactions_total > 0 OR comments_count > 0 OR shares_count > 0
        GROUP BY post_type
        ORDER BY avg_engagement DESC
    """)

    post_type_perf = []
    best_type = None
    max_avg_eng = 0
    for row in cursor.fetchall():
        avg_eng = row[5]
        if avg_eng > max_avg_eng:
            max_avg_eng = avg_eng
            best_type = row[0]
        post_type_perf.append({
            "type": row[0],
            "count": row[1],
            "views": row[2],
            "reach": row[3],
            "engagement": row[4],
            "avg_engagement": round(avg_eng, 1),
            "avg_views": round(row[6], 1)
        })

    conn.close()

    return {
        "monthly": list(reversed(monthly)),  # Most recent first
        "weekly": list(reversed(weekly)),    # Most recent first
        "dayOfWeek": day_of_week,
        "pageRankings": page_rankings,
        "postTypePerf": post_type_perf,
        "insights": generate_insights(monthly, weekly, day_of_week, page_rankings, post_type_perf, best_type)
    }


def generate_insights(monthly, weekly, day_of_week, page_rankings, post_type_perf, best_type):
    """Generate AI-style insights based on data."""
    insights = []

    # Monthly trend insight
    if len(monthly) >= 2:
        recent = monthly[-1]
        prev = monthly[-2]
        if recent['mom_change']:
            if recent['mom_change'] > 0:
                insights.append({
                    "type": "trend_up",
                    "title": "Engagement Growing",
                    "text": f"Engagement increased {recent['mom_change']}% from {prev['month']} to {recent['month']}"
                })
            elif recent['mom_change'] < -10:
                insights.append({
                    "type": "trend_down",
                    "title": "Engagement Declining",
                    "text": f"Engagement dropped {abs(recent['mom_change'])}% - consider increasing content quality"
                })

    # Best performing day
    best_day = next((d for d in day_of_week if d['is_best']), None)
    if best_day:
        insights.append({
            "type": "best_day",
            "title": f"{best_day['day']} is Best",
            "text": f"{best_day['day']} generates {best_day['avg_engagement']:.0f} avg engagement - 📈 optimal for posting"
        })

    # Best content type
    if best_type and post_type_perf:
        best = next((p for p in post_type_perf if p['type'] == best_type), None)
        if best:
            insights.append({
                "type": "content_type",
                "title": f"{best_type} Perform Best",
                "text": f"{best_type} average {best['avg_engagement']:.0f} engagement vs others"
            })

    # Top page insight
    if page_rankings:
        top_page = page_rankings[0]
        insights.append({
            "type": "top_page",
            "title": f"{top_page['page_name'].replace('Juana Babe ', '')} Leads",
            "text": f"Top performer with {top_page['engagement']:,} total engagement ({top_page['avg_engagement']:.0f}/post)"
        })

    # Weekly momentum
    if len(weekly) >= 2:
        recent_week = weekly[-1]
        if recent_week.get('wow_change') and recent_week['wow_change'] > 5:
            insights.append({
                "type": "momentum",
                "title": "Strong Week",
                "text": f"This week up {recent_week['wow_change']}% vs last week - keep the momentum!"
            })

    return insights[:5]  # Limit to 5 insights


def export_page_comparison():
    """Export detailed page comparison data for the Overlap/Comparison page."""
    conn = get_conn()
    cursor = conn.cursor()

    # Get comprehensive page stats
    cursor.execute("""
        SELECT
            pg.page_id,
            pg.page_name,
            pg.fan_count,
            COUNT(p.post_id) as posts,
            COALESCE(SUM(p.total_engagement), 0) as engagement,
            COALESCE(AVG(p.total_engagement), 0) as avg_engagement,
            COALESCE(SUM(p.views_count), 0) as views,
            COALESCE(SUM(p.reach_count), 0) as reach,
            COALESCE(SUM(p.reactions_total), 0) as reactions,
            COALESCE(SUM(p.comments_count), 0) as comments,
            COALESCE(SUM(p.shares_count), 0) as shares,
            COALESCE(AVG(p.pes), 0) as avg_pes
        FROM pages pg
        LEFT JOIN posts p ON pg.page_id = p.page_id
        GROUP BY pg.page_id
        ORDER BY engagement DESC
    """)

    pages = []
    total_engagement = 0
    for row in cursor.fetchall():
        total_engagement += row[4]
        pages.append({
            "page_id": row[0],
            "name": row[1],  # For frontend compatibility
            "page_name": row[1],
            "fan_count": row[2],
            "posts": row[3],
            "engagement": row[4],
            "avg_engagement": round(row[5], 1),
            "views": row[6],
            "reach": row[7],
            "reactions": row[8],
            "comments": row[9],
            "shares": row[10],
            "avg_pes": round(row[11], 1)
        })

    # Add rankings and percentages
    for i, page in enumerate(pages):
        page["rank"] = i + 1
        page["engagement_share"] = round((page["engagement"] / total_engagement) * 100, 1) if total_engagement > 0 else 0

    # Get post type distribution by page
    cursor.execute("""
        SELECT
            p.page_id,
            COALESCE(p.post_type, 'Unknown') as post_type,
            COUNT(*) as count,
            COALESCE(SUM(p.total_engagement), 0) as engagement,
            COALESCE(AVG(p.total_engagement), 0) as avg_engagement
        FROM posts p
        GROUP BY p.page_id, p.post_type
        ORDER BY p.page_id, count DESC
    """)

    post_types_by_page = {}
    for row in cursor.fetchall():
        page_id = row[0]
        if page_id not in post_types_by_page:
            post_types_by_page[page_id] = []
        post_types_by_page[page_id].append({
            "type": row[1],
            "count": row[2],
            "engagement": row[3],
            "avg_engagement": round(row[4], 1)
        })

    # Calculate content strategy similarity (which pages focus on same content types)
    # Find dominant content type for each page
    dominant_types = {}
    for page_id, types in post_types_by_page.items():
        if types:
            total = sum(t["count"] for t in types)
            dominant_types[page_id] = {
                "type": types[0]["type"],
                "percentage": round((types[0]["count"] / total) * 100, 1) if total > 0 else 0
            }

    conn.close()

    return {
        "pages": pages,
        "postTypesByPage": post_types_by_page,
        "dominantTypes": dominant_types
    }


def export_per_post_engagement_trend():
    """Export per-post engagement trend for trend chart.

    Filtered to ANALYSIS_PAGE_IDS and ANALYSIS_START_DATE to ANALYSIS_END_DATE.
    """
    conn = get_conn()
    cursor = conn.cursor()

    # Week expression for aggregation
    date_expr = """CASE
        WHEN publish_time LIKE '____-__-__%' THEN substr(publish_time, 1, 10)
        ELSE substr(publish_time, 7, 4) || '-' || substr(publish_time, 1, 2) || '-' || substr(publish_time, 4, 2)
    END"""
    week_expr = f"strftime('%Y-%W', {date_expr})"

    # Build page filter
    page_placeholders = ','.join('?' * len(ANALYSIS_PAGE_IDS))

    # Weekly per-post engagement trend
    cursor.execute(f"""
        SELECT
            {week_expr} as week,
            MIN({date_expr}) as week_start,
            COUNT(*) as post_count,
            COALESCE(SUM(total_engagement), 0) as total_engagement,
            COALESCE(AVG(total_engagement), 0) as avg_engagement_per_post,
            COALESCE(AVG(views_count), 0) as avg_views_per_post,
            COALESCE(AVG(reach_count), 0) as avg_reach_per_post
        FROM posts
        WHERE publish_time IS NOT NULL
            AND (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
            AND page_id IN ({page_placeholders})
            AND {date_expr} >= ?
            AND {date_expr} <= ?
        GROUP BY {week_expr}
        HAVING COUNT(*) >= 1
        ORDER BY week DESC
        LIMIT 35
    """, ANALYSIS_PAGE_IDS + [ANALYSIS_START_DATE, ANALYSIS_END_DATE])

    weekly_trend = []
    rows = list(cursor.fetchall())

    # Calculate week-over-week changes
    for i, row in enumerate(reversed(rows)):  # Process oldest first
        engagement = row[3]
        avg_eng = row[4]
        prev_avg = None
        wow_change = None

        if i > 0 and weekly_trend:
            prev_avg = weekly_trend[-1]['avg_engagement']
            if prev_avg > 0:
                wow_change = round(((avg_eng - prev_avg) / prev_avg) * 100, 1)

        weekly_trend.append({
            "week": row[0],
            "week_start": row[1],
            "posts": row[2],
            "total_engagement": engagement,
            "avg_engagement": round(avg_eng, 1),
            "avg_views": round(row[5], 1),
            "avg_reach": round(row[6], 1),
            "wow_change": wow_change
        })

    # Calculate overall trend (comparing recent 4 weeks vs previous 4 weeks)
    recent_4_weeks = weekly_trend[-4:] if len(weekly_trend) >= 4 else weekly_trend
    prev_4_weeks = weekly_trend[-8:-4] if len(weekly_trend) >= 8 else []

    recent_avg = sum(w['avg_engagement'] for w in recent_4_weeks) / len(recent_4_weeks) if recent_4_weeks else 0
    prev_avg = sum(w['avg_engagement'] for w in prev_4_weeks) / len(prev_4_weeks) if prev_4_weeks else 0

    overall_trend = None
    if prev_avg > 0:
        overall_trend = round(((recent_avg - prev_avg) / prev_avg) * 100, 1)

    conn.close()

    return {
        "weekly": list(reversed(weekly_trend)),  # Most recent first
        "recentAvg": round(recent_avg, 1),
        "prevAvg": round(prev_avg, 1),
        "overallTrend": overall_trend,
        "status": "growing" if overall_trend and overall_trend > 5 else "declining" if overall_trend and overall_trend < -5 else "stable"
    }


def export_live_stream_health():
    """Export Live stream health indicator data.

    Filtered to ANALYSIS_PAGE_IDS and ANALYSIS_START_DATE to ANALYSIS_END_DATE.
    """
    conn = get_conn()
    cursor = conn.cursor()

    date_expr = """CASE
        WHEN publish_time LIKE '____-__-__%' THEN substr(publish_time, 1, 10)
        ELSE substr(publish_time, 7, 4) || '-' || substr(publish_time, 1, 2) || '-' || substr(publish_time, 4, 2)
    END"""
    week_expr = f"strftime('%Y-%W', {date_expr})"

    # Build page filter
    page_placeholders = ','.join('?' * len(ANALYSIS_PAGE_IDS))

    # Weekly Live stream performance
    cursor.execute(f"""
        SELECT
            {week_expr} as week,
            MIN({date_expr}) as week_start,
            COUNT(*) as live_count,
            COALESCE(SUM(total_engagement), 0) as total_engagement,
            COALESCE(AVG(total_engagement), 0) as avg_engagement,
            COALESCE(AVG(reactions_total), 0) as avg_reactions,
            COALESCE(AVG(comments_count), 0) as avg_comments,
            COALESCE(AVG(shares_count), 0) as avg_shares,
            COALESCE(SUM(views_count), 0) as total_views,
            COALESCE(AVG(views_count), 0) as avg_views
        FROM posts
        WHERE post_type = 'Live'
            AND publish_time IS NOT NULL
            AND (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
            AND page_id IN ({page_placeholders})
            AND {date_expr} >= ?
            AND {date_expr} <= ?
        GROUP BY {week_expr}
        ORDER BY week DESC
        LIMIT 12
    """, ANALYSIS_PAGE_IDS + [ANALYSIS_START_DATE, ANALYSIS_END_DATE])

    weekly_live = []
    rows = list(cursor.fetchall())

    for row in rows:
        weekly_live.append({
            "week": row[0],
            "week_start": row[1],
            "live_count": row[2],
            "total_engagement": row[3],
            "avg_engagement": round(row[4], 1),
            "avg_reactions": round(row[5], 1),
            "avg_comments": round(row[6], 1),
            "avg_shares": round(row[7], 1),
            "total_views": row[8],
            "avg_views": round(row[9], 1)
        })

    # Calculate health metrics
    if len(weekly_live) >= 2:
        recent = weekly_live[0]  # Most recent week
        prev = weekly_live[1]    # Previous week

        # Week over week change
        wow_change = None
        if prev['avg_engagement'] > 0:
            wow_change = round(((recent['avg_engagement'] - prev['avg_engagement']) / prev['avg_engagement']) * 100, 1)

        # Peak comparison (recent vs best)
        peak_engagement = max(w['avg_engagement'] for w in weekly_live) if weekly_live else 0
        vs_peak = round(((recent['avg_engagement'] - peak_engagement) / peak_engagement) * 100, 1) if peak_engagement > 0 else 0

        health_score = 100
        if wow_change and wow_change < -20:
            health_score -= 30
        if vs_peak < -50:
            health_score -= 30
        if recent['live_count'] < 5:
            health_score -= 20

        status = "critical" if health_score < 50 else "warning" if health_score < 75 else "healthy"
    else:
        wow_change = None
        vs_peak = None
        health_score = 0
        status = "insufficient_data"

    # Compare Live vs other content types (with same filters)
    cursor.execute(f"""
        SELECT
            CASE WHEN post_type = 'Live' THEN 'Live' ELSE 'Other' END as type,
            COALESCE(AVG(total_engagement), 0) as avg_engagement,
            COUNT(*) as post_count
        FROM posts
        WHERE (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
            AND page_id IN ({page_placeholders})
            AND {date_expr} >= ?
            AND {date_expr} <= ?
        GROUP BY CASE WHEN post_type = 'Live' THEN 'Live' ELSE 'Other' END
    """, ANALYSIS_PAGE_IDS + [ANALYSIS_START_DATE, ANALYSIS_END_DATE])

    live_vs_other = {"liveAvg": 0, "liveCount": 0, "otherAvg": 0, "otherCount": 0}
    for row in cursor.fetchall():
        if row[0] == 'Live':
            live_vs_other["liveAvg"] = round(row[1], 1)
            live_vs_other["liveCount"] = row[2]
        else:
            live_vs_other["otherAvg"] = round(row[1], 1)
            live_vs_other["otherCount"] = row[2]

    conn.close()

    return {
        "weekly": weekly_live,
        "health": {
            "score": health_score,
            "status": status,
            "wowChange": wow_change,
            "vsPeak": vs_peak
        },
        "liveVsOther": live_vs_other
    }


def export_page_group_health():
    """Export health metrics for both Juan365 and Live Stream page groups separately.

    Shows weekly performance, health scores, and trends for each group.
    """
    conn = get_conn()
    cursor = conn.cursor()

    date_expr = """CASE
        WHEN publish_time LIKE '____-__-__%' THEN substr(publish_time, 1, 10)
        ELSE substr(publish_time, 7, 4) || '-' || substr(publish_time, 1, 2) || '-' || substr(publish_time, 4, 2)
    END"""
    week_expr = f"strftime('%Y-%W', {date_expr})"

    def get_group_health(page_ids, group_name):
        """Calculate health metrics for a page group."""
        page_placeholders = ','.join('?' * len(page_ids))

        # Weekly performance
        cursor.execute(f"""
            SELECT
                {week_expr} as week,
                MIN({date_expr}) as week_start,
                COUNT(*) as post_count,
                COALESCE(SUM(total_engagement), 0) as total_engagement,
                COALESCE(AVG(total_engagement), 0) as avg_engagement,
                COALESCE(AVG(reactions_total), 0) as avg_reactions,
                COALESCE(AVG(comments_count), 0) as avg_comments,
                COALESCE(AVG(shares_count), 0) as avg_shares,
                COALESCE(SUM(views_count), 0) as total_views,
                COALESCE(AVG(views_count), 0) as avg_views
            FROM posts
            WHERE publish_time IS NOT NULL
                AND (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
                AND page_id IN ({page_placeholders})
                AND {date_expr} >= ?
                AND {date_expr} <= ?
            GROUP BY {week_expr}
            ORDER BY week DESC
            LIMIT 12
        """, page_ids + [ANALYSIS_START_DATE, ANALYSIS_END_DATE])

        weekly = []
        rows = list(cursor.fetchall())

        for row in rows:
            weekly.append({
                "week": row[0],
                "week_start": row[1],
                "post_count": row[2],
                "total_engagement": row[3],
                "avg_engagement": round(row[4], 1),
                "avg_reactions": round(row[5], 1),
                "avg_comments": round(row[6], 1),
                "avg_shares": round(row[7], 1),
                "total_views": row[8],
                "avg_views": round(row[9], 1)
            })

        # Calculate health metrics
        if len(weekly) >= 2:
            recent = weekly[0]  # Most recent week
            prev = weekly[1]    # Previous week

            # Week over week change
            wow_change = None
            if prev['avg_engagement'] > 0:
                wow_change = round(((recent['avg_engagement'] - prev['avg_engagement']) / prev['avg_engagement']) * 100, 1)

            # Peak comparison (recent vs best)
            peak_engagement = max(w['avg_engagement'] for w in weekly) if weekly else 0
            vs_peak = round(((recent['avg_engagement'] - peak_engagement) / peak_engagement) * 100, 1) if peak_engagement > 0 else 0

            # Health score calculation
            health_score = 100
            if wow_change and wow_change < -20:
                health_score -= 30
            if vs_peak < -50:
                health_score -= 30
            if recent['post_count'] < 5:
                health_score -= 20

            status = "critical" if health_score < 50 else "warning" if health_score < 75 else "healthy"
        else:
            wow_change = None
            vs_peak = None
            health_score = 0
            status = "insufficient_data"

        # Post type breakdown for this group
        cursor.execute(f"""
            SELECT
                COALESCE(post_type, 'Unknown') as post_type,
                COUNT(*) as count,
                COALESCE(AVG(total_engagement), 0) as avg_engagement
            FROM posts
            WHERE (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
                AND page_id IN ({page_placeholders})
                AND {date_expr} >= ?
                AND {date_expr} <= ?
            GROUP BY post_type
            ORDER BY count DESC
        """, page_ids + [ANALYSIS_START_DATE, ANALYSIS_END_DATE])

        post_types = []
        for row in cursor.fetchall():
            post_types.append({
                "type": row[0],
                "count": row[1],
                "avg_engagement": round(row[2], 1)
            })

        # Overall stats
        cursor.execute(f"""
            SELECT
                COUNT(*) as total_posts,
                COALESCE(SUM(total_engagement), 0) as total_engagement,
                COALESCE(AVG(total_engagement), 0) as avg_engagement,
                COALESCE(SUM(views_count), 0) as total_views,
                COALESCE(AVG(views_count), 0) as avg_views
            FROM posts
            WHERE (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
                AND page_id IN ({page_placeholders})
                AND {date_expr} >= ?
                AND {date_expr} <= ?
        """, page_ids + [ANALYSIS_START_DATE, ANALYSIS_END_DATE])

        overall = cursor.fetchone()

        return {
            "name": group_name,
            "weekly": weekly,
            "health": {
                "score": health_score,
                "status": status,
                "wowChange": wow_change,
                "vsPeak": vs_peak
            },
            "postTypes": post_types,
            "overall": {
                "totalPosts": overall[0],
                "totalEngagement": overall[1],
                "avgEngagement": round(overall[2], 1),
                "totalViews": overall[3],
                "avgViews": round(overall[4], 1)
            }
        }

    # Get health for both groups
    juan365_health = get_group_health(JUAN365_PAGE_IDS, "Juan365")
    live_stream_health = get_group_health(LIVE_STREAM_PAGE_IDS, "Juan365 Live Stream")

    # Generate comparison insights
    insights = []

    j_score = juan365_health["health"]["score"]
    l_score = live_stream_health["health"]["score"]

    if j_score > l_score:
        insights.append(f"Juan365 is healthier (score: {j_score}) vs Live Stream ({l_score})")
    else:
        insights.append(f"Live Stream is healthier (score: {l_score}) vs Juan365 ({j_score})")

    j_wow = juan365_health["health"]["wowChange"]
    l_wow = live_stream_health["health"]["wowChange"]

    if j_wow is not None:
        trend = "growing" if j_wow > 0 else "declining"
        insights.append(f"Juan365 is {trend} ({j_wow:+.1f}% WoW)")
    if l_wow is not None:
        trend = "growing" if l_wow > 0 else "declining"
        insights.append(f"Live Stream is {trend} ({l_wow:+.1f}% WoW)")

    conn.close()

    return {
        "juan365": juan365_health,
        "liveStream": live_stream_health,
        "insights": insights,
        "period": {
            "start": ANALYSIS_START_DATE,
            "end": ANALYSIS_END_DATE
        }
    }


def export_video_duration_analysis():
    """Export video duration vs engagement analysis.

    Filtered to ANALYSIS_PAGE_IDS and ANALYSIS_START_DATE to ANALYSIS_END_DATE.
    """
    conn = get_conn()
    cursor = conn.cursor()

    # Date expression for filtering
    date_expr = """CASE
        WHEN publish_time LIKE '____-__-__%' THEN substr(publish_time, 1, 10)
        ELSE substr(publish_time, 7, 4) || '-' || substr(publish_time, 1, 2) || '-' || substr(publish_time, 4, 2)
    END"""

    # Build page filter
    page_placeholders = ','.join('?' * len(ANALYSIS_PAGE_IDS))

    # Duration buckets analysis
    cursor.execute(f"""
        SELECT
            CASE
                WHEN duration_sec IS NULL OR duration_sec = 0 THEN 'Unknown'
                WHEN duration_sec <= 15 THEN '0-15s'
                WHEN duration_sec <= 30 THEN '16-30s'
                WHEN duration_sec <= 60 THEN '31-60s'
                WHEN duration_sec <= 120 THEN '61-120s'
                WHEN duration_sec <= 300 THEN '2-5min'
                ELSE '5min+'
            END as duration_bucket,
            COUNT(*) as video_count,
            COALESCE(AVG(total_engagement), 0) as avg_engagement,
            COALESCE(AVG(views_count), 0) as avg_views,
            COALESCE(AVG(reactions_total), 0) as avg_reactions,
            COALESCE(AVG(comments_count), 0) as avg_comments,
            COALESCE(AVG(shares_count), 0) as avg_shares,
            MIN(duration_sec) as min_duration,
            MAX(duration_sec) as max_duration,
            AVG(duration_sec) as avg_duration
        FROM posts
        WHERE post_type IN ('Videos', 'Reels', 'Live')
            AND (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
            AND page_id IN ({page_placeholders})
            AND {date_expr} >= ?
            AND {date_expr} <= ?
        GROUP BY duration_bucket
        ORDER BY
            CASE duration_bucket
                WHEN '0-15s' THEN 1
                WHEN '16-30s' THEN 2
                WHEN '31-60s' THEN 3
                WHEN '61-120s' THEN 4
                WHEN '2-5min' THEN 5
                WHEN '5min+' THEN 6
                ELSE 7
            END
    """, ANALYSIS_PAGE_IDS + [ANALYSIS_START_DATE, ANALYSIS_END_DATE])

    duration_buckets = []
    best_bucket = None
    max_avg_eng = 0

    for row in cursor.fetchall():
        avg_eng = row[2]
        bucket = {
            "bucket": row[0],
            "count": row[1],
            "avg_engagement": round(avg_eng, 1),
            "avg_views": round(row[3], 1),
            "avg_reactions": round(row[4], 1),
            "avg_comments": round(row[5], 1),
            "avg_shares": round(row[6], 1),
            "duration_range": f"{row[7] or 0}-{row[8] or 0}s",
            "avg_duration_sec": round(row[9] or 0, 1)
        }
        duration_buckets.append(bucket)

        if avg_eng > max_avg_eng and row[0] != 'Unknown':
            max_avg_eng = avg_eng
            best_bucket = row[0]

    # Get overall video stats (with same filters)
    cursor.execute(f"""
        SELECT
            COUNT(*) as total_videos,
            AVG(duration_sec) as avg_duration,
            AVG(total_engagement) as avg_engagement
        FROM posts
        WHERE post_type IN ('Videos', 'Reels', 'Live')
            AND duration_sec > 0
            AND page_id IN ({page_placeholders})
            AND {date_expr} >= ?
            AND {date_expr} <= ?
    """, ANALYSIS_PAGE_IDS + [ANALYSIS_START_DATE, ANALYSIS_END_DATE])
    overall = cursor.fetchone()

    # Video watch time stats (if available, with same filters)
    cursor.execute(f"""
        SELECT
            COUNT(*) as videos_with_watch_time,
            AVG(avg_watch_time_ms) as avg_watch_time_ms,
            AVG(video_views_complete) as avg_complete_views,
            AVG(watch_completion_rate) as avg_completion_rate
        FROM posts
        WHERE post_type IN ('Videos', 'Reels')
            AND avg_watch_time_ms > 0
            AND page_id IN ({page_placeholders})
            AND {date_expr} >= ?
            AND {date_expr} <= ?
    """, ANALYSIS_PAGE_IDS + [ANALYSIS_START_DATE, ANALYSIS_END_DATE])
    watch_time_row = cursor.fetchone()

    watch_time_stats = None
    if watch_time_row and watch_time_row[0] > 0:
        watch_time_stats = {
            "videosWithData": watch_time_row[0],
            "avgWatchTimeSec": round((watch_time_row[1] or 0) / 1000, 1),
            "avgCompleteViews": round(watch_time_row[2] or 0, 1),
            "avgCompletionRate": round(watch_time_row[3] or 0, 1)
        }

    conn.close()

    return {
        "buckets": duration_buckets,
        "bestBucket": best_bucket,
        "overall": {
            "totalVideos": overall[0] if overall else 0,
            "avgDurationSec": round(overall[1] or 0, 1) if overall else 0,
            "avgEngagement": round(overall[2] or 0, 1) if overall else 0
        },
        "watchTimeStats": watch_time_stats,
        "recommendation": f"Videos in the {best_bucket} range perform best with {max_avg_eng:.0f} avg engagement" if best_bucket else None
    }


def export_analytics_report(stats_data, per_post_trend_data, live_stream_health_data, video_duration_data):
    """Export analytics report with history tracking."""

    # Create current snapshot
    now = datetime.now()
    current_snapshot = {
        "date": now.isoformat(),
        "totalPosts": stats_data["all"]["total_posts"],
        "avgEngagement": stats_data["all"]["avg_engagement"],
        "liveHealthScore": live_stream_health_data.get("health", {}).get("score", 0),
        "status": per_post_trend_data.get("status", "unknown"),
        "perPostTrend": per_post_trend_data.get("overallTrend", 0),
        "videoBestBucket": video_duration_data.get("bestBucket", "N/A")
    }

    # Load existing history
    history = []
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, 'r') as f:
                history = json.load(f)
        except:
            history = []

    # Check if we already have an entry for today
    today_str = now.strftime("%Y-%m-%d")
    history = [h for h in history if not h.get("date", "").startswith(today_str)]

    # Append current snapshot
    history.append(current_snapshot)

    # Keep only last 30 entries
    history = history[-30:]

    # Save updated history
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, 'w') as f:
        json.dump(history, f, indent=2)

    return {
        "generatedAt": now.isoformat(),
        "history": history
    }


def export_comment_analysis():
    """Export self-comment vs organic comment analysis data."""
    conn = get_conn()
    cursor = conn.cursor()

    # Overall self-comment stats
    cursor.execute("""
        SELECT
            COUNT(*) as total_posts_with_comments,
            COALESCE(SUM(page_comments), 0) as total_self_comments,
            COALESCE(SUM(comments_count), 0) as total_comments_db,
            COUNT(CASE WHEN has_page_comment = 1 THEN 1 END) as posts_with_self_comment,
            COUNT(CASE WHEN page_comments IS NOT NULL AND page_comments >= 0 THEN 1 END) as posts_analyzed
        FROM posts
        WHERE comments_count > 0
    """)
    row = cursor.fetchone()

    total_posts = row[0]
    self_comments = row[1]
    total_db_comments = row[2]
    posts_with_self = row[3]
    posts_analyzed = row[4]

    # Estimate organic as total minus self (from analyzed posts)
    cursor.execute("""
        SELECT COALESCE(SUM(comments_count - page_comments), 0)
        FROM posts
        WHERE page_comments IS NOT NULL AND comments_count > 0
    """)
    organic_comments = cursor.fetchone()[0]

    summary = {
        "total_posts_with_comments": total_posts,
        "posts_analyzed": posts_analyzed,
        "posts_with_self_comment": posts_with_self,
        "total_self_comments": self_comments,
        "total_organic_comments": organic_comments,
        "self_comment_rate": round((self_comments / (self_comments + organic_comments)) * 100, 1) if (self_comments + organic_comments) > 0 else 0,
        "posts_with_self_pct": round((posts_with_self / posts_analyzed) * 100, 1) if posts_analyzed > 0 else 0
    }

    # Self-comment analysis by page
    cursor.execute("""
        SELECT
            pg.page_name,
            p.page_id,
            COUNT(*) as posts_with_comments,
            COALESCE(SUM(p.page_comments), 0) as self_comments,
            COALESCE(SUM(p.comments_count - p.page_comments), 0) as organic_comments,
            COUNT(CASE WHEN p.has_page_comment = 1 THEN 1 END) as posts_with_self
        FROM posts p
        LEFT JOIN pages pg ON p.page_id = pg.page_id
        WHERE p.comments_count > 0 AND p.page_comments IS NOT NULL
        GROUP BY p.page_id
        ORDER BY self_comments DESC
    """)

    by_page = []
    for row in cursor.fetchall():
        total = row[3] + row[4]
        by_page.append({
            "page_name": row[0],
            "page_id": row[1],
            "posts_with_comments": row[2],
            "self_comments": row[3],
            "organic_comments": row[4],
            "posts_with_self": row[5],
            "self_rate": round((row[3] / total) * 100, 1) if total > 0 else 0
        })

    # Engagement comparison: posts WITH self-comment vs WITHOUT
    cursor.execute("""
        SELECT
            AVG(CASE WHEN has_page_comment = 1 THEN total_engagement END) as avg_eng_with_self,
            AVG(CASE WHEN has_page_comment = 0 OR has_page_comment IS NULL THEN total_engagement END) as avg_eng_without_self,
            AVG(CASE WHEN has_page_comment = 1 THEN reactions_total END) as avg_react_with,
            AVG(CASE WHEN has_page_comment = 0 OR has_page_comment IS NULL THEN reactions_total END) as avg_react_without
        FROM posts
        WHERE comments_count > 0 AND page_comments IS NOT NULL
    """)
    eng_row = cursor.fetchone()

    avg_with = eng_row[0] or 0
    avg_without = eng_row[1] or 0
    engagement_boost = round(((avg_with - avg_without) / avg_without) * 100, 1) if avg_without > 0 else 0

    effectivity = {
        "avg_engagement_with_self": round(avg_with, 1),
        "avg_engagement_without_self": round(avg_without, 1),
        "engagement_boost_pct": engagement_boost,
        "avg_reactions_with": round(eng_row[2] or 0, 1),
        "avg_reactions_without": round(eng_row[3] or 0, 1)
    }

    # Top posts with most self-comments
    cursor.execute("""
        SELECT
            p.post_id,
            pg.page_name,
            p.title,
            p.page_comments,
            p.comments_count,
            p.total_engagement,
            p.permalink
        FROM posts p
        LEFT JOIN pages pg ON p.page_id = pg.page_id
        WHERE p.page_comments > 0
        ORDER BY p.page_comments DESC
        LIMIT 10
    """)

    top_self_commented = []
    for row in cursor.fetchall():
        top_self_commented.append({
            "post_id": row[0],
            "page_name": row[1],
            "title": row[2][:50] if row[2] else "Untitled",
            "self_comments": row[3],
            "total_comments": row[4],
            "engagement": row[5],
            "permalink": row[6]
        })

    conn.close()

    return {
        "summary": summary,
        "byPage": by_page,
        "effectivity": effectivity,
        "topSelfCommented": top_self_commented
    }


def export_all_posts():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.post_id,
            p.page_id,
            pg.page_name,
            p.title,
            p.post_type,
            p.publish_time,
            p.permalink,
            COALESCE(p.reactions_total, 0) as reactions,
            COALESCE(p.comments_count, 0) as comments,
            COALESCE(p.shares_count, 0) as shares,
            COALESCE(p.views_count, 0) as views,
            COALESCE(p.reach_count, 0) as reach,
            COALESCE(p.total_engagement, 0) as engagement,
            COALESCE(p.pes, 0) as pes
        FROM posts p
        LEFT JOIN pages pg ON p.page_id = pg.page_id
        WHERE p.reactions_total > 0 OR p.comments_count > 0 OR p.shares_count > 0
        ORDER BY p.publish_time DESC
    """)

    all_posts = []
    for row in cursor.fetchall():
        all_posts.append({
            "post_id": row[0],
            "page_id": row[1],
            "page_name": row[2],
            "title": row[3],
            "post_type": row[4],
            "publish_time": row[5],
            "permalink": row[6],
            "reactions": row[7],
            "comments": row[8],
            "shares": row[9],
            "views": row[10],
            "reach": row[11],
            "engagement": row[12],
            "pes": round(row[13], 1)
        })

    conn.close()
    return all_posts


def export_top_posts(limit=10):
    """Export top performing posts (all pages + per-page)."""
    conn = get_conn()
    cursor = conn.cursor()

    # Get all pages first
    cursor.execute("SELECT DISTINCT page_id FROM posts WHERE reactions_total > 0")
    page_ids = [row[0] for row in cursor.fetchall()]

    # All pages top posts
    cursor.execute(f"""
        SELECT
            p.post_id,
            p.page_id,
            pg.page_name,
            p.title,
            p.post_type,
            p.publish_time,
            p.permalink,
            COALESCE(p.reactions_total, 0) as reactions,
            COALESCE(p.comments_count, 0) as comments,
            COALESCE(p.shares_count, 0) as shares,
            COALESCE(p.total_engagement, 0) as engagement,
            COALESCE(p.pes, 0) as pes
        FROM posts p
        LEFT JOIN pages pg ON p.page_id = pg.page_id
        WHERE p.reactions_total > 0 OR p.comments_count > 0 OR p.shares_count > 0
        ORDER BY p.total_engagement DESC
        LIMIT {limit}
    """)

    all_posts = []
    for row in cursor.fetchall():
        all_posts.append({
            "post_id": row[0],
            "page_id": row[1],
            "page_name": row[2],
            "title": row[3],
            "post_type": row[4],
            "publish_time": row[5],
            "permalink": row[6],
            "reactions": row[7],
            "comments": row[8],
            "shares": row[9],
            "engagement": row[10],
            "pes": round(row[11], 1)
        })

    # Per-page top posts
    by_page = {}
    for page_id in page_ids:
        cursor.execute(f"""
            SELECT
                p.post_id,
                p.page_id,
                pg.page_name,
                p.title,
                p.post_type,
                p.publish_time,
                p.permalink,
                COALESCE(p.reactions_total, 0) as reactions,
                COALESCE(p.comments_count, 0) as comments,
                COALESCE(p.shares_count, 0) as shares,
                COALESCE(p.total_engagement, 0) as engagement,
                COALESCE(p.pes, 0) as pes
            FROM posts p
            LEFT JOIN pages pg ON p.page_id = pg.page_id
            WHERE p.page_id = ? AND (p.reactions_total > 0 OR p.comments_count > 0 OR p.shares_count > 0)
            ORDER BY p.total_engagement DESC
            LIMIT {limit}
        """, (page_id,))

        page_posts = []
        for row in cursor.fetchall():
            page_posts.append({
                "post_id": row[0],
                "page_id": row[1],
                "page_name": row[2],
                "title": row[3],
                "post_type": row[4],
                "publish_time": row[5],
                "permalink": row[6],
                "reactions": row[7],
                "comments": row[8],
                "shares": row[9],
                "engagement": row[10],
                "pes": round(row[11], 1)
            })
        by_page[page_id] = page_posts

    conn.close()
    return {"all": all_posts, "byPage": by_page}


def export_page_group_comparison():
    """Export side-by-side comparison: Juan365 vs Live Stream pages.

    Breaks down by December 2025 vs January 2026 with averages.
    """
    conn = get_conn()
    cursor = conn.cursor()

    date_expr = """CASE
        WHEN publish_time LIKE '____-__-__%' THEN substr(publish_time, 1, 10)
        ELSE substr(publish_time, 7, 4) || '-' || substr(publish_time, 1, 2) || '-' || substr(publish_time, 4, 2)
    END"""
    month_expr = """CASE
        WHEN publish_time LIKE '____-__-__%' THEN substr(publish_time, 1, 7)
        ELSE substr(publish_time, 7, 4) || '-' || substr(publish_time, 1, 2)
    END"""

    def get_group_stats(page_ids, group_name):
        """Get stats for a group of pages by month."""
        page_placeholders = ','.join('?' * len(page_ids))

        # Monthly breakdown (Dec 2025 and Jan 2026)
        cursor.execute(f"""
            SELECT
                {month_expr} as month,
                COUNT(*) as post_count,
                COALESCE(SUM(reactions_total), 0) as total_reactions,
                COALESCE(SUM(comments_count), 0) as total_comments,
                COALESCE(SUM(shares_count), 0) as total_shares,
                COALESCE(SUM(total_engagement), 0) as total_engagement,
                COALESCE(AVG(total_engagement), 0) as avg_engagement,
                COALESCE(SUM(views_count), 0) as total_views,
                COALESCE(AVG(views_count), 0) as avg_views,
                COALESCE(SUM(reach_count), 0) as total_reach,
                COALESCE(AVG(reach_count), 0) as avg_reach
            FROM posts
            WHERE page_id IN ({page_placeholders})
                AND {date_expr} >= ?
                AND {date_expr} <= ?
                AND (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
            GROUP BY {month_expr}
            ORDER BY month
        """, page_ids + [ANALYSIS_START_DATE, ANALYSIS_END_DATE])

        monthly = {}
        for row in cursor.fetchall():
            monthly[row[0]] = {
                "month": row[0],
                "posts": row[1],
                "total_reactions": row[2],
                "total_comments": row[3],
                "total_shares": row[4],
                "total_engagement": row[5],
                "avg_engagement": round(row[6], 1),
                "total_views": row[7],
                "avg_views": round(row[8], 1),
                "total_reach": row[9],
                "avg_reach": round(row[10], 1)
            }

        # Overall period stats
        cursor.execute(f"""
            SELECT
                COUNT(*) as post_count,
                COALESCE(SUM(reactions_total), 0) as total_reactions,
                COALESCE(SUM(comments_count), 0) as total_comments,
                COALESCE(SUM(shares_count), 0) as total_shares,
                COALESCE(SUM(total_engagement), 0) as total_engagement,
                COALESCE(AVG(total_engagement), 0) as avg_engagement,
                COALESCE(SUM(views_count), 0) as total_views,
                COALESCE(AVG(views_count), 0) as avg_views,
                COALESCE(SUM(reach_count), 0) as total_reach,
                COALESCE(AVG(reach_count), 0) as avg_reach
            FROM posts
            WHERE page_id IN ({page_placeholders})
                AND {date_expr} >= ?
                AND {date_expr} <= ?
                AND (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
        """, page_ids + [ANALYSIS_START_DATE, ANALYSIS_END_DATE])

        total_row = cursor.fetchone()
        total = {
            "posts": total_row[0],
            "total_reactions": total_row[1],
            "total_comments": total_row[2],
            "total_shares": total_row[3],
            "total_engagement": total_row[4],
            "avg_engagement": round(total_row[5], 1),
            "total_views": total_row[6],
            "avg_views": round(total_row[7], 1),
            "total_reach": total_row[8],
            "avg_reach": round(total_row[9], 1)
        }

        # Post type breakdown
        cursor.execute(f"""
            SELECT
                COALESCE(post_type, 'Unknown') as post_type,
                COUNT(*) as count,
                COALESCE(SUM(total_engagement), 0) as engagement,
                COALESCE(AVG(total_engagement), 0) as avg_engagement
            FROM posts
            WHERE page_id IN ({page_placeholders})
                AND {date_expr} >= ?
                AND {date_expr} <= ?
                AND (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
            GROUP BY post_type
            ORDER BY count DESC
        """, page_ids + [ANALYSIS_START_DATE, ANALYSIS_END_DATE])

        post_types = []
        for row in cursor.fetchall():
            post_types.append({
                "type": row[0],
                "count": row[1],
                "total_engagement": row[2],
                "avg_engagement": round(row[3], 1)
            })

        return {
            "name": group_name,
            "pageIds": page_ids,
            "december": monthly.get("2025-12", {"month": "2025-12", "posts": 0, "total_engagement": 0, "avg_engagement": 0, "total_views": 0, "avg_views": 0, "total_reach": 0, "avg_reach": 0}),
            "january": monthly.get("2026-01", {"month": "2026-01", "posts": 0, "total_engagement": 0, "avg_engagement": 0, "total_views": 0, "avg_views": 0, "total_reach": 0, "avg_reach": 0}),
            "total": total,
            "postTypes": post_types
        }

    # Get stats for both groups
    juan365_stats = get_group_stats(JUAN365_PAGE_IDS, "Juan365")
    live_stream_stats = get_group_stats(LIVE_STREAM_PAGE_IDS, "Juan365 Live Stream")

    # Calculate month-over-month changes for each group
    def calc_mom_change(dec_val, jan_val):
        if dec_val and dec_val > 0:
            return round(((jan_val - dec_val) / dec_val) * 100, 1)
        return None

    juan365_mom = {
        "engagement": calc_mom_change(juan365_stats["december"].get("total_engagement", 0), juan365_stats["january"].get("total_engagement", 0)),
        "avg_engagement": calc_mom_change(juan365_stats["december"].get("avg_engagement", 0), juan365_stats["january"].get("avg_engagement", 0)),
        "posts": calc_mom_change(juan365_stats["december"].get("posts", 0), juan365_stats["january"].get("posts", 0)),
        "views": calc_mom_change(juan365_stats["december"].get("total_views", 0), juan365_stats["january"].get("total_views", 0))
    }

    live_mom = {
        "engagement": calc_mom_change(live_stream_stats["december"].get("total_engagement", 0), live_stream_stats["january"].get("total_engagement", 0)),
        "avg_engagement": calc_mom_change(live_stream_stats["december"].get("avg_engagement", 0), live_stream_stats["january"].get("avg_engagement", 0)),
        "posts": calc_mom_change(live_stream_stats["december"].get("posts", 0), live_stream_stats["january"].get("posts", 0)),
        "views": calc_mom_change(live_stream_stats["december"].get("total_views", 0), live_stream_stats["january"].get("total_views", 0))
    }

    juan365_stats["momChange"] = juan365_mom
    live_stream_stats["momChange"] = live_mom

    # Generate comparison insights
    insights = []

    # Compare total engagement
    j_total = juan365_stats["total"]["total_engagement"]
    l_total = live_stream_stats["total"]["total_engagement"]
    if j_total > l_total:
        diff_pct = round(((j_total - l_total) / l_total) * 100, 1) if l_total > 0 else 0
        insights.append(f"Juan365 has {diff_pct}% more total engagement than Live Stream")
    else:
        diff_pct = round(((l_total - j_total) / j_total) * 100, 1) if j_total > 0 else 0
        insights.append(f"Live Stream has {diff_pct}% more total engagement than Juan365")

    # Compare average engagement
    j_avg = juan365_stats["total"]["avg_engagement"]
    l_avg = live_stream_stats["total"]["avg_engagement"]
    if j_avg > l_avg:
        insights.append(f"Juan365 averages {j_avg:.0f} engagement per post vs Live Stream's {l_avg:.0f}")
    else:
        insights.append(f"Live Stream averages {l_avg:.0f} engagement per post vs Juan365's {j_avg:.0f}")

    # MoM trends
    if juan365_mom["avg_engagement"]:
        trend = "increased" if juan365_mom["avg_engagement"] > 0 else "decreased"
        insights.append(f"Juan365 avg engagement {trend} by {abs(juan365_mom['avg_engagement'])}% from Dec to Jan")

    if live_mom["avg_engagement"]:
        trend = "increased" if live_mom["avg_engagement"] > 0 else "decreased"
        insights.append(f"Live Stream avg engagement {trend} by {abs(live_mom['avg_engagement'])}% from Dec to Jan")

    conn.close()

    return {
        "juan365": juan365_stats,
        "liveStream": live_stream_stats,
        "insights": insights,
        "period": {
            "start": ANALYSIS_START_DATE,
            "end": ANALYSIS_END_DATE
        }
    }


def export_watch_time_analysis():
    """Export watch time data for Juan365 and Live Stream pages.

    Includes avg watch time, 3-second views, complete views, and completion rate.
    """
    conn = get_conn()
    cursor = conn.cursor()

    date_expr = """CASE
        WHEN publish_time LIKE '____-__-__%' THEN substr(publish_time, 1, 10)
        ELSE substr(publish_time, 7, 4) || '-' || substr(publish_time, 1, 2) || '-' || substr(publish_time, 4, 2)
    END"""
    month_expr = """CASE
        WHEN publish_time LIKE '____-__-__%' THEN substr(publish_time, 1, 7)
        ELSE substr(publish_time, 7, 4) || '-' || substr(publish_time, 1, 2)
    END"""

    def get_watch_time_stats(page_ids, group_name):
        """Get watch time stats for a group of pages."""
        page_placeholders = ','.join('?' * len(page_ids))

        # Overall watch time stats
        # Total watch time = avg_watch_time × views (actual accumulated watch time)
        cursor.execute(f"""
            SELECT
                COUNT(*) as total_posts,
                COUNT(avg_watch_time_ms) as posts_with_watch_time,
                COALESCE(SUM(CAST(avg_watch_time_ms AS REAL) * COALESCE(views_count, 0)), 0) / 1000.0 / 3600.0 as total_watch_hours,
                COALESCE(AVG(avg_watch_time_ms), 0) / 1000.0 as avg_watch_time_sec,
                COALESCE(SUM(video_views_3sec), 0) as total_3sec_views,
                COALESCE(SUM(video_views_complete), 0) as total_complete_views,
                COALESCE(SUM(views_count), 0) as total_views
            FROM posts
            WHERE page_id IN ({page_placeholders})
                AND {date_expr} >= ?
                AND {date_expr} <= ?
                AND avg_watch_time_ms IS NOT NULL
                AND avg_watch_time_ms > 0
        """, page_ids + [ANALYSIS_START_DATE, ANALYSIS_END_DATE])

        row = cursor.fetchone()
        overall = {
            "totalPosts": row[0],
            "postsWithWatchTime": row[1],
            "totalWatchTimeHours": round(row[2], 1),
            "avgWatchTimeSec": round(row[3], 1),
            "total3SecViews": row[4] or 0,
            "totalCompleteViews": row[5] or 0,
            "totalViews": row[6] or 0
        }

        # Monthly breakdown
        cursor.execute(f"""
            SELECT
                {month_expr} as month,
                COUNT(*) as posts,
                COALESCE(SUM(CAST(avg_watch_time_ms AS REAL) * COALESCE(views_count, 0)), 0) / 1000.0 / 3600.0 as total_watch_hours,
                COALESCE(AVG(avg_watch_time_ms), 0) / 1000.0 as avg_watch_sec,
                COALESCE(SUM(views_count), 0) as total_views
            FROM posts
            WHERE page_id IN ({page_placeholders})
                AND {date_expr} >= ?
                AND {date_expr} <= ?
                AND avg_watch_time_ms IS NOT NULL
                AND avg_watch_time_ms > 0
            GROUP BY {month_expr}
            ORDER BY month
        """, page_ids + [ANALYSIS_START_DATE, ANALYSIS_END_DATE])

        monthly = {}
        for row in cursor.fetchall():
            monthly[row[0]] = {
                "month": row[0],
                "posts": row[1],
                "totalWatchTimeHours": round(row[2], 1),
                "avgWatchTimeSec": round(row[3], 1),
                "totalViews": row[4] or 0
            }

        # Calculate MoM change
        dec = monthly.get("2025-12", {})
        jan = monthly.get("2026-01", {})
        mom_change = None
        if dec.get("avgWatchTimeSec", 0) > 0:
            mom_change = round(((jan.get("avgWatchTimeSec", 0) - dec.get("avgWatchTimeSec", 0)) / dec.get("avgWatchTimeSec", 0)) * 100, 1)

        return {
            "name": group_name,
            "pageIds": page_ids,
            "overall": overall,
            "december": monthly.get("2025-12", {"month": "2025-12", "posts": 0, "avgWatchTimeSec": 0, "totalWatchTimeHours": 0, "totalViews": 0}),
            "january": monthly.get("2026-01", {"month": "2026-01", "posts": 0, "avgWatchTimeSec": 0, "totalWatchTimeHours": 0, "totalViews": 0}),
            "momChange": mom_change
        }

    # Get watch time for both groups
    juan365_watch = get_watch_time_stats(JUAN365_PAGE_IDS, "Juan365")
    live_stream_watch = get_watch_time_stats(LIVE_STREAM_PAGE_IDS, "Juan365 Live Stream")

    # Generate insights
    insights = []

    j_avg = juan365_watch["overall"]["avgWatchTimeSec"]
    l_avg = live_stream_watch["overall"]["avgWatchTimeSec"]

    if l_avg > j_avg and j_avg > 0:
        diff = round(l_avg - j_avg, 1)
        pct = round((diff / j_avg) * 100, 1)
        insights.append(f"Live Stream videos retain viewers {diff}s longer ({pct}% more) than Juan365")
    elif j_avg > l_avg and l_avg > 0:
        diff = round(j_avg - l_avg, 1)
        pct = round((diff / l_avg) * 100, 1)
        insights.append(f"Juan365 videos retain viewers {diff}s longer ({pct}% more) than Live Stream")

    if juan365_watch["momChange"]:
        trend = "increased" if juan365_watch["momChange"] > 0 else "decreased"
        insights.append(f"Juan365 avg watch time {trend} by {abs(juan365_watch['momChange'])}% from Dec to Jan")

    if live_stream_watch["momChange"]:
        trend = "increased" if live_stream_watch["momChange"] > 0 else "decreased"
        insights.append(f"Live Stream avg watch time {trend} by {abs(live_stream_watch['momChange'])}% from Dec to Jan")

    conn.close()

    return {
        "juan365": juan365_watch,
        "liveStream": live_stream_watch,
        "insights": insights,
        "period": {
            "start": ANALYSIS_START_DATE,
            "end": ANALYSIS_END_DATE
        }
    }


def export_deep_dive_analysis_for_page(page_id, page_name):
    """Export deep dive analysis for a specific page: weekly trends, CTA analysis, and insights."""
    conn = get_conn()
    cursor = conn.cursor()

    # 1. Weekly engagement trend
    cursor.execute('''
        SELECT
            strftime('%Y-W%W', publish_time) as week,
            MIN(DATE(publish_time)) as week_start,
            MAX(DATE(publish_time)) as week_end,
            COUNT(*) as posts,
            ROUND(AVG(total_engagement), 0) as avg_eng,
            SUM(total_engagement) as total_eng,
            MAX(total_engagement) as max_eng
        FROM posts
        WHERE page_id = ?
            AND publish_time >= ?
            AND publish_time <= ?
        GROUP BY week
        ORDER BY week
    ''', (page_id, ANALYSIS_START_DATE, ANALYSIS_END_DATE))

    weekly_data = []
    rows = list(cursor.fetchall())
    prev_avg = None
    for row in rows:
        wow_change = None
        if prev_avg and prev_avg > 0:
            wow_change = round(((row[4] - prev_avg) / prev_avg) * 100, 1)
        weekly_data.append({
            "week": row[0],
            "weekStart": row[1],
            "weekEnd": row[2],
            "posts": row[3],
            "avgEngagement": row[4],
            "totalEngagement": row[5],
            "maxEngagement": row[6],
            "wowChange": wow_change
        })
        prev_avg = row[4]

    # 2. Viral posts (top performers)
    cursor.execute('''
        SELECT
            strftime('%Y-%m-%d', publish_time) as date,
            strftime('%Y-W%W', publish_time) as week,
            post_type,
            total_engagement,
            reactions_total,
            comments_count,
            shares_count,
            views_count,
            SUBSTR(COALESCE(title, ''), 1, 60) as title,
            post_id,
            permalink
        FROM posts
        WHERE page_id = ?
            AND publish_time >= ?
            AND publish_time <= ?
        ORDER BY total_engagement DESC
        LIMIT 10
    ''', (page_id, ANALYSIS_START_DATE, ANALYSIS_END_DATE))

    viral_posts = []
    for row in cursor.fetchall():
        viral_posts.append({
            "date": row[0],
            "week": row[1],
            "postType": row[2],
            "engagement": row[3],
            "reactions": row[4],
            "comments": row[5],
            "shares": row[6],
            "views": row[7] or 0,
            "title": row[8] or "",
            "postId": row[9],
            "permalink": row[10]
        })

    # 3. Post type comparison (Dec vs Jan)
    cursor.execute('''
        SELECT
            post_type,
            SUM(CASE WHEN publish_time < '2026-01-01' THEN 1 ELSE 0 END) as dec_posts,
            ROUND(AVG(CASE WHEN publish_time < '2026-01-01' THEN total_engagement END), 0) as dec_avg,
            SUM(CASE WHEN publish_time >= '2026-01-01' THEN 1 ELSE 0 END) as jan_posts,
            ROUND(AVG(CASE WHEN publish_time >= '2026-01-01' THEN total_engagement END), 0) as jan_avg
        FROM posts
        WHERE page_id = ?
            AND publish_time >= ?
            AND publish_time <= ?
        GROUP BY post_type
        ORDER BY dec_posts DESC
    ''', (page_id, ANALYSIS_START_DATE, ANALYSIS_END_DATE))

    post_type_comparison = []
    for row in cursor.fetchall():
        dec_avg = row[2] or 0
        jan_avg = row[4] or 0
        change = round(((jan_avg - dec_avg) / dec_avg * 100), 1) if dec_avg > 0 else 0
        post_type_comparison.append({
            "type": row[0],
            "decPosts": row[1],
            "decAvg": dec_avg,
            "janPosts": row[3],
            "janAvg": jan_avg,
            "change": change
        })

    # 4. CTA Analysis
    cursor.execute('''
        SELECT
            publish_time,
            LOWER(COALESCE(title, '') || ' ' || COALESCE(description, '')) as content,
            total_engagement
        FROM posts
        WHERE page_id = ?
            AND publish_time >= ?
            AND publish_time <= ?
    ''', (page_id, ANALYSIS_START_DATE, ANALYSIS_END_DATE))

    posts = cursor.fetchall()
    dec_posts = [p for p in posts if p[0] < '2026-01-01']
    jan_posts = [p for p in posts if p[0] >= '2026-01-01']

    cta_keywords = {
        'comment': ['comment', 'i-comment', 'mag-comment'],
        'react': ['react', 'like', 'heart', 'love'],
        'share': ['share', 'i-share', 'tag'],
        'giveaway': ['giveaway', 'raffle', 'win', 'prize', 'free', 'regalo', 'bonus', 'pamasko'],
        'question': ['ano', 'sino', 'saan', 'kailan', 'paano', 'what', 'who', 'where', 'when', 'how', '?']
    }

    def analyze_cta(posts_list):
        results = {}
        total = len(posts_list)
        for cta_type, keywords in cta_keywords.items():
            count = 0
            total_eng = 0
            for post in posts_list:
                content = post[1]
                engagement = post[2] or 0
                if any(kw in content for kw in keywords):
                    count += 1
                    total_eng += engagement
            results[cta_type] = {
                "count": count,
                "percentage": round(count / total * 100, 1) if total > 0 else 0,
                "avgEngagement": round(total_eng / count, 0) if count > 0 else 0
            }
        return results

    cta_analysis = {
        "december": analyze_cta(dec_posts),
        "january": analyze_cta(jan_posts),
        "decTotalPosts": len(dec_posts),
        "janTotalPosts": len(jan_posts)
    }

    # 5. Viral distribution
    cursor.execute('''
        SELECT
            CASE WHEN publish_time < '2026-01-01' THEN 'December' ELSE 'January' END as month,
            COUNT(*) as viral_posts,
            SUM(total_engagement) as total_eng,
            MAX(total_engagement) as top_post
        FROM posts
        WHERE page_id = ?
            AND publish_time >= ?
            AND publish_time <= ?
            AND total_engagement > 2000
        GROUP BY month
    ''', (page_id, ANALYSIS_START_DATE, ANALYSIS_END_DATE))

    viral_distribution = {}
    for row in cursor.fetchall():
        viral_distribution[row[0].lower()] = {
            "viralPosts": row[1],
            "totalEngagement": row[2],
            "topPost": row[3]
        }

    # 6. Generate key insights
    insights = []

    # Viral post insight
    if viral_posts and viral_posts[0]["engagement"] > 5000:
        top = viral_posts[0]
        insights.append({
            "type": "viral",
            "title": f"Top Performer on {page_name}",
            "detail": f"The '{top['title'][:40]}...' on {top['date']} generated {top['engagement']:,} engagement and {top['views']:,} views."
        })

    # CTA insight
    dec_comment = cta_analysis["december"].get("comment", {}).get("percentage", 0)
    jan_comment = cta_analysis["january"].get("comment", {}).get("percentage", 0)
    if dec_comment > jan_comment + 5:
        insights.append({
            "type": "cta",
            "title": "Call-to-Action Usage Changed",
            "detail": f"December had {dec_comment}% posts with comment CTAs vs {jan_comment}% in January."
        })
    elif jan_comment > dec_comment + 5:
        insights.append({
            "type": "cta",
            "title": "CTA Usage Increased",
            "detail": f"January had {jan_comment}% posts with comment CTAs vs {dec_comment}% in December."
        })

    # Post type insight - check for significant changes
    for pt in post_type_comparison:
        if pt["decPosts"] > 0 and pt["janPosts"] > 0:
            if pt["change"] < -30:
                insights.append({
                    "type": "content",
                    "title": f"{pt['type']} Performance Declined",
                    "detail": f"{pt['type']} avg engagement dropped {abs(pt['change'])}% from December ({pt['decAvg']:,.0f}) to January ({pt['janAvg']:,.0f})."
                })
                break
            elif pt["change"] > 30:
                insights.append({
                    "type": "content",
                    "title": f"{pt['type']} Performance Improved",
                    "detail": f"{pt['type']} avg engagement increased {pt['change']}% from December ({pt['decAvg']:,.0f}) to January ({pt['janAvg']:,.0f})."
                })
                break

    # Recommendation based on data
    dec_total = sum(pt["decPosts"] for pt in post_type_comparison)
    jan_total = sum(pt["janPosts"] for pt in post_type_comparison)
    if jan_total < dec_total * 0.8:
        insights.append({
            "type": "recommendation",
            "title": "Increase Posting Frequency",
            "detail": f"January had {jan_total} posts vs December's {dec_total}. Consider maintaining consistent posting volume."
        })
    else:
        insights.append({
            "type": "recommendation",
            "title": "Optimize Content Mix",
            "detail": "Analyze top performing posts and replicate successful content formats with clear CTAs."
        })

    conn.close()

    return {
        "weeklyTrend": weekly_data,
        "viralPosts": viral_posts,
        "postTypeComparison": post_type_comparison,
        "ctaAnalysis": cta_analysis,
        "viralDistribution": viral_distribution,
        "insights": insights,
        "period": {
            "start": ANALYSIS_START_DATE,
            "end": ANALYSIS_END_DATE
        }
    }


def export_deep_dive_analysis():
    """Export deep dive analysis for both Juan365 and Live Stream pages."""
    print("\n  Exporting deep dive analysis...")

    JUAN365_MAIN = "61572881214141"
    LIVESTREAM_MAIN = "61569634500241"

    juan365_data = export_deep_dive_analysis_for_page(JUAN365_MAIN, "Juan365")
    livestream_data = export_deep_dive_analysis_for_page(LIVESTREAM_MAIN, "Live Stream")

    return {
        "juan365": juan365_data,
        "liveStream": livestream_data
    }


def main():
    print("=" * 60)
    print("Exporting Static Data for Vercel")
    print("=" * 60)

    # Sync latest metrics from post_metrics to posts table
    print("\nSyncing metrics...")
    try:
        sync_metrics_to_posts()
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            print("  Warning: Database locked, skipping sync (using cached metrics)")
        else:
            raise

    stats_data = export_stats()
    pages_data = export_pages()
    post_types_data = export_post_types()
    daily_data = export_daily()
    top_posts_data = export_top_posts(10)
    all_posts_data = export_all_posts()
    time_series_data = export_time_series()

    # Export comment analysis (self-comments vs organic)
    comment_analysis_data = export_comment_analysis()

    page_comparison_data = export_page_comparison()

    # New dashboard analytics
    per_post_trend_data = export_per_post_engagement_trend()
    live_stream_health_data = export_live_stream_health()
    video_duration_data = export_video_duration_analysis()

    # Page group comparison (Juan365 vs Live Stream, Dec vs Jan)
    page_group_comparison_data = export_page_group_comparison()

    # Page group health (separate health for Juan365 and Live Stream)
    page_group_health_data = export_page_group_health()

    # Watch time analysis (Juan365 vs Live Stream)
    watch_time_data = export_watch_time_analysis()

    # Deep dive analysis (weekly trends, CTA analysis, insights)
    deep_dive_data = export_deep_dive_analysis()

    # Analytics Report with history tracking
    analytics_report_data = export_analytics_report(
        stats_data, per_post_trend_data, live_stream_health_data, video_duration_data
    )

    data = {
        "stats": stats_data,
        "pages": pages_data,
        "postTypes": post_types_data,
        "daily": daily_data,
        "topPosts": top_posts_data,
        "posts": all_posts_data,
        "overlaps": [],  # Empty for now, prevents errors
        "timeSeries": time_series_data,
        "commentAnalysis": comment_analysis_data,
        "pageComparison": page_comparison_data,
        "perPostTrend": per_post_trend_data,
        "liveStreamHealth": live_stream_health_data,
        "videoDurationAnalysis": video_duration_data,
        "analyticsReport": analytics_report_data,
        "pageGroupComparison": page_group_comparison_data,
        "pageGroupHealth": page_group_health_data,
        "watchTime": watch_time_data,
        "deepDive": deep_dive_data
    }

    # Pretty print summary
    all_stats = stats_data["all"]
    print(f"\nStats:")
    print(f"  Posts: {all_stats['total_posts']}")
    print(f"  Pages: {all_stats['total_pages']}")
    print(f"  Date range: {all_stats['date_range_start']} to {all_stats['date_range_end']}")
    print(f"  Total Engagement: {all_stats['total_engagement']:,}")

    print(f"\nPages: {len(pages_data)}")
    for page in pages_data:
        print(f"  - {page['page_name']}: {page['post_count']} posts, {page['total_engagement']:,} engagement")

    print(f"\nPost Types: {len(post_types_data['all'])}")
    print(f"Daily Data Points: {len(daily_data['all'])}")
    print(f"Top Posts: {len(top_posts_data['all'])}")
    print(f"All Posts (for Posts page): {len(all_posts_data)}")
    print(f"Per-page data: {len(stats_data['byPage'])} pages")

    print(f"\nTime Series Analytics:")
    print(f"  Monthly periods: {len(time_series_data['monthly'])}")
    print(f"  Weekly periods: {len(time_series_data['weekly'])}")
    print(f"  AI Insights: {len(time_series_data['insights'])}")

    if comment_analysis_data.get("summary", {}).get("posts_analyzed", 0) > 0:
        summary = comment_analysis_data["summary"]
        print(f"\nComment Analysis:")
        print(f"  Posts analyzed: {summary['posts_analyzed']}")
        print(f"  Self-comments: {summary['total_self_comments']}")
        print(f"  Organic: {summary['total_organic_comments']}")
        print(f"  Self-comment rate: {summary['self_comment_rate']}%")
    else:
        print(f"\nComment Analysis: No data (run fetch_comments.py first)")

    # New Dashboard Analytics Summary
    print(f"\nPer-Post Engagement Trend:")
    print(f"  Weekly data points: {len(per_post_trend_data.get('weekly', []))}")
    print(f"  Status: {per_post_trend_data.get('status', 'N/A')}")
    print(f"  Recent avg: {per_post_trend_data.get('recentAvg', 0):.1f}")

    print(f"\nLive Stream Health:")
    health = live_stream_health_data.get('health', {})
    print(f"  Health score: {health.get('score', 0):.1f}")
    print(f"  Status: {health.get('status', 'N/A')}")
    print(f"  WoW change: {health.get('wowChange', 0):+.1f}%")

    print(f"\nVideo Duration Analysis:")
    print(f"  Duration buckets: {len(video_duration_data.get('buckets', []))}")
    print(f"  Best performing: {video_duration_data.get('bestBucket', 'N/A')}")
    print(f"  Recommendation: {video_duration_data.get('recommendation', 'N/A')[:60]}...")

    print(f"\nAnalytics Report:")
    print(f"  Generated at: {analytics_report_data.get('generatedAt', 'N/A')}")
    print(f"  History entries: {len(analytics_report_data.get('history', []))}")

    print(f"\nPage Group Comparison (Juan365 vs Live Stream):")
    j365 = page_group_comparison_data.get('juan365', {})
    ls = page_group_comparison_data.get('liveStream', {})
    print(f"  Juan365:")
    print(f"    Dec 2025: {j365.get('december', {}).get('posts', 0)} posts, {j365.get('december', {}).get('total_engagement', 0):,} engagement, {j365.get('december', {}).get('avg_engagement', 0):.1f} avg")
    print(f"    Jan 2026: {j365.get('january', {}).get('posts', 0)} posts, {j365.get('january', {}).get('total_engagement', 0):,} engagement, {j365.get('january', {}).get('avg_engagement', 0):.1f} avg")
    print(f"    MoM Change: {j365.get('momChange', {}).get('avg_engagement', 'N/A')}%")
    print(f"  Live Stream:")
    print(f"    Dec 2025: {ls.get('december', {}).get('posts', 0)} posts, {ls.get('december', {}).get('total_engagement', 0):,} engagement, {ls.get('december', {}).get('avg_engagement', 0):.1f} avg")
    print(f"    Jan 2026: {ls.get('january', {}).get('posts', 0)} posts, {ls.get('january', {}).get('total_engagement', 0):,} engagement, {ls.get('january', {}).get('avg_engagement', 0):.1f} avg")
    print(f"    MoM Change: {ls.get('momChange', {}).get('avg_engagement', 'N/A')}%")
    print(f"  Insights:")
    for insight in page_group_comparison_data.get('insights', [])[:3]:
        print(f"    - {insight}")

    print(f"\nPage Group Health (Juan365 vs Live Stream):")
    j365_health = page_group_health_data.get('juan365', {})
    ls_health = page_group_health_data.get('liveStream', {})
    print(f"  Juan365:")
    print(f"    Health Score: {j365_health.get('health', {}).get('score', 0):.1f}/100")
    print(f"    Status: {j365_health.get('health', {}).get('status', 'N/A')}")
    print(f"    WoW Change: {j365_health.get('health', {}).get('wowChange', 0):+.1f}%")
    print(f"  Live Stream:")
    print(f"    Health Score: {ls_health.get('health', {}).get('score', 0):.1f}/100")
    print(f"    Status: {ls_health.get('health', {}).get('status', 'N/A')}")
    print(f"    WoW Change: {ls_health.get('health', {}).get('wowChange', 0):+.1f}%")
    if page_group_health_data.get('comparison', {}).get('insights'):
        print(f"  Comparison Insights:")
        for insight in page_group_health_data.get('comparison', {}).get('insights', [])[:3]:
            print(f"    - {insight}")

    print(f"\nWatch Time Analysis (Juan365 vs Live Stream):")
    j365_watch = watch_time_data.get('juan365', {})
    ls_watch = watch_time_data.get('liveStream', {})
    print(f"  Juan365:")
    print(f"    Posts with watch data: {j365_watch.get('overall', {}).get('postsWithWatchTime', 0)}")
    print(f"    Avg watch time: {j365_watch.get('overall', {}).get('avgWatchTimeSec', 0):.1f}s")
    print(f"    Total watch time: {j365_watch.get('overall', {}).get('totalWatchTimeHours', 0):,.1f} hours")
    print(f"  Live Stream:")
    print(f"    Posts with watch data: {ls_watch.get('overall', {}).get('postsWithWatchTime', 0)}")
    print(f"    Avg watch time: {ls_watch.get('overall', {}).get('avgWatchTimeSec', 0):.1f}s")
    print(f"    Total watch time: {ls_watch.get('overall', {}).get('totalWatchTimeHours', 0):,.1f} hours")
    if watch_time_data.get('insights'):
        print(f"  Insights:")
        for insight in watch_time_data.get('insights', [])[:3]:
            print(f"    - {insight}")

    # Save to file
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n[OK] Exported to: {OUTPUT_PATH}")
    print("\nTo update Vercel:")
    print("  git add frontend/public/data/analytics.json")
    print("  git commit -m 'Update analytics data'")
    print("  git push")


if __name__ == "__main__":
    main()
