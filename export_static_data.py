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
from datetime import datetime
from database import sync_metrics_to_posts

DATABASE_PATH = "data/juan365_socmed.db"
OUTPUT_PATH = "frontend/public/data/analytics.json"


def get_conn():
    return sqlite3.connect(DATABASE_PATH)


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


def main():
    print("=" * 60)
    print("Exporting Static Data for Vercel")
    print("=" * 60)

    # Sync latest metrics from post_metrics to posts table
    print("\nSyncing metrics...")
    sync_metrics_to_posts()

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
        "pageComparison": page_comparison_data
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
