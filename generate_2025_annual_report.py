"""
Juan365 2025 Annual Report Generator
Generates a professional HTML report with deep analysis for 2025 social media performance
"""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "juan365_socmed.db"
OUTPUT_PATH = Path(__file__).parent / "reports" / "Juan365_2025_Annual_Report.html"

def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def format_number(n):
    """Format large numbers with K/M suffix"""
    if n is None:
        return "0"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{n:,}"

def format_pct(n):
    """Format percentage"""
    if n is None:
        return "0%"
    return f"{n:.2f}%"

def generate_report():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Date range for 2025 (June-December based on available data)
    start_date = "2025-06-01"
    end_date = "2025-12-31"

    # 1. Overall 2025 Stats
    cursor.execute("""
        SELECT
            COUNT(*) as total_posts,
            COALESCE(SUM(views_count), 0) as total_views,
            COALESCE(SUM(reach_count), 0) as total_reach,
            COALESCE(SUM(reactions_total), 0) as total_reactions,
            COALESCE(SUM(comments_count), 0) as total_comments,
            COALESCE(SUM(shares_count), 0) as total_shares,
            COALESCE(SUM(total_engagement), 0) as total_engagement,
            COALESCE(AVG(total_engagement), 0) as avg_engagement_per_post,
            COALESCE(AVG(views_count), 0) as avg_views_per_post
        FROM posts
        WHERE substr(publish_time, 1, 10) BETWEEN ? AND ?
    """, (start_date, end_date))
    overall = cursor.fetchone()

    # Calculate engagement rate
    engagement_rate = (overall['total_engagement'] / overall['total_reach'] * 100) if overall['total_reach'] > 0 else 0

    # 2. Monthly Breakdown with detailed growth (use substr to handle timezone suffix)
    cursor.execute("""
        SELECT
            substr(publish_time, 1, 7) as month,
            COUNT(*) as posts,
            COALESCE(SUM(views_count), 0) as views,
            COALESCE(SUM(reach_count), 0) as reach,
            COALESCE(SUM(reactions_total), 0) as reactions,
            COALESCE(SUM(comments_count), 0) as comments,
            COALESCE(SUM(shares_count), 0) as shares,
            COALESCE(SUM(total_engagement), 0) as engagement,
            COALESCE(AVG(total_engagement), 0) as avg_engagement
        FROM posts
        WHERE substr(publish_time, 1, 10) BETWEEN ? AND ?
        GROUP BY month
        ORDER BY month
    """, (start_date, end_date))
    monthly_data = cursor.fetchall()

    # 3. Page Ranking with engagement rate
    cursor.execute("""
        SELECT
            p.page_name,
            COALESCE(p.fan_count, 0) as followers,
            COUNT(*) as posts,
            COALESCE(SUM(posts.views_count), 0) as views,
            COALESCE(SUM(posts.reach_count), 0) as reach,
            COALESCE(SUM(posts.total_engagement), 0) as engagement,
            COALESCE(AVG(posts.total_engagement), 0) as avg_engagement
        FROM posts
        JOIN pages p ON posts.page_id = p.page_id
        WHERE substr(posts.publish_time, 1, 10) BETWEEN ? AND ?
        GROUP BY p.page_name
        ORDER BY engagement DESC
    """, (start_date, end_date))
    page_ranking = cursor.fetchall()

    # 4. Content Type Analysis (combine Videos + Reels)
    cursor.execute("""
        SELECT
            CASE
                WHEN post_type IN ('Videos', 'Video', 'Reels', 'Reel') THEN 'Video/Reels'
                WHEN post_type = 'Photos' THEN 'Photos'
                WHEN post_type = 'Live' THEN 'Live'
                WHEN post_type = 'Text' THEN 'Text'
                ELSE 'Other'
            END as content_type,
            COUNT(*) as posts,
            COALESCE(SUM(views_count), 0) as views,
            COALESCE(SUM(reach_count), 0) as reach,
            COALESCE(SUM(total_engagement), 0) as engagement,
            COALESCE(AVG(total_engagement), 0) as avg_engagement,
            COALESCE(AVG(views_count), 0) as avg_views
        FROM posts
        WHERE substr(publish_time, 1, 10) BETWEEN ? AND ?
        GROUP BY content_type
        ORDER BY engagement DESC
    """, (start_date, end_date))
    content_types = cursor.fetchall()

    # 5. Best Day of Week Analysis
    cursor.execute("""
        SELECT
            CASE CAST(strftime('%w', publish_time) AS INTEGER)
                WHEN 0 THEN 'Sunday'
                WHEN 1 THEN 'Monday'
                WHEN 2 THEN 'Tuesday'
                WHEN 3 THEN 'Wednesday'
                WHEN 4 THEN 'Thursday'
                WHEN 5 THEN 'Friday'
                WHEN 6 THEN 'Saturday'
            END as day_name,
            CAST(strftime('%w', publish_time) AS INTEGER) as day_num,
            COUNT(*) as posts,
            COALESCE(SUM(total_engagement), 0) as engagement,
            COALESCE(AVG(total_engagement), 0) as avg_engagement,
            COALESCE(SUM(views_count), 0) as views
        FROM posts
        WHERE substr(publish_time, 1, 10) BETWEEN ? AND ?
        GROUP BY day_num
        ORDER BY avg_engagement DESC
    """, (start_date, end_date))
    day_performance = cursor.fetchall()

    # 6. Best Hour Analysis (convert UTC to PHT +8 hours)
    cursor.execute("""
        SELECT
            (CAST(strftime('%H', publish_time) AS INTEGER) + 8) % 24 as hour_pht,
            COUNT(*) as posts,
            COALESCE(SUM(total_engagement), 0) as engagement,
            COALESCE(AVG(total_engagement), 0) as avg_engagement
        FROM posts
        WHERE substr(publish_time, 1, 10) BETWEEN ? AND ?
        GROUP BY hour_pht
        ORDER BY avg_engagement DESC
        LIMIT 10
    """, (start_date, end_date))
    hour_performance = cursor.fetchall()

    # 7. Top 20 Posts
    cursor.execute("""
        SELECT
            p.page_name,
            posts.title,
            posts.post_type,
            posts.publish_time,
            posts.permalink,
            COALESCE(posts.views_count, 0) as views,
            COALESCE(posts.reach_count, 0) as reach,
            COALESCE(posts.reactions_total, 0) as reactions,
            COALESCE(posts.comments_count, 0) as comments,
            COALESCE(posts.shares_count, 0) as shares,
            COALESCE(posts.total_engagement, 0) as engagement
        FROM posts
        JOIN pages p ON posts.page_id = p.page_id
        WHERE substr(posts.publish_time, 1, 10) BETWEEN ? AND ?
        ORDER BY posts.total_engagement DESC
        LIMIT 20
    """, (start_date, end_date))
    top_posts = cursor.fetchall()

    # 8. Viral Posts (highest shares ratio) - min 1000 views to avoid anomalies
    cursor.execute("""
        SELECT
            p.page_name,
            posts.title,
            posts.post_type,
            posts.permalink,
            COALESCE(posts.shares_count, 0) as shares,
            COALESCE(posts.views_count, 0) as views,
            COALESCE(posts.total_engagement, 0) as engagement,
            CASE WHEN posts.views_count > 0
                THEN CAST(posts.shares_count AS FLOAT) / posts.views_count * 100
                ELSE 0 END as share_rate
        FROM posts
        JOIN pages p ON posts.page_id = p.page_id
        WHERE substr(posts.publish_time, 1, 10) BETWEEN ? AND ?
            AND posts.shares_count > 100
            AND posts.views_count >= 1000
        ORDER BY share_rate DESC
        LIMIT 10
    """, (start_date, end_date))
    viral_posts = cursor.fetchall()

    # 9. Current Followers
    cursor.execute("""
        SELECT page_name, COALESCE(fan_count, 0) as followers
        FROM pages
        ORDER BY followers DESC
    """)
    followers = cursor.fetchall()

    # 10. Weekly Trend (last 4 weeks of available data)
    cursor.execute("""
        SELECT
            strftime('%Y-W%W', publish_time) as week,
            COUNT(*) as posts,
            COALESCE(SUM(total_engagement), 0) as engagement,
            COALESCE(AVG(total_engagement), 0) as avg_engagement
        FROM posts
        WHERE substr(publish_time, 1, 10) BETWEEN ? AND ?
        GROUP BY week
        ORDER BY week DESC
        LIMIT 12
    """, (start_date, end_date))
    weekly_trend = list(reversed(cursor.fetchall()))

    conn.close()

    # Calculate growth trajectory with more metrics
    growth_data = []
    prev = {'views': 0, 'reach': 0, 'engagement': 0}
    for m in monthly_data:
        views_growth = ((m['views'] - prev['views']) / prev['views'] * 100) if prev['views'] > 0 else 0
        reach_growth = ((m['reach'] - prev['reach']) / prev['reach'] * 100) if prev['reach'] > 0 else 0
        eng_growth = ((m['engagement'] - prev['engagement']) / prev['engagement'] * 100) if prev['engagement'] > 0 else 0

        growth_data.append({
            'month': m['month'],
            'posts': m['posts'],
            'views': m['views'],
            'reach': m['reach'],
            'engagement': m['engagement'],
            'avg_engagement': m['avg_engagement'],
            'views_growth': views_growth,
            'reach_growth': reach_growth,
            'eng_growth': eng_growth
        })
        prev = {'views': m['views'], 'reach': m['reach'], 'engagement': m['engagement']}

    # Calculate total followers
    total_followers = sum(f['followers'] for f in followers)

    # Find best performing content type
    best_content = content_types[0] if content_types else None

    # Find best day and hour
    best_day = day_performance[0] if day_performance else None
    best_hour = hour_performance[0] if hour_performance else None

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Juan365 2025 Annual Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}

        .header {{
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .subtitle {{ font-size: 1.2em; opacity: 0.9; }}
        .header .date-range {{ margin-top: 15px; font-size: 0.9em; opacity: 0.8; }}

        .section {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            backdrop-filter: blur(10px);
        }}
        .section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .section h3 {{
            color: #a78bfa;
            margin: 20px 0 15px 0;
            font-size: 1.2em;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, rgba(102,126,234,0.2) 0%, rgba(118,75,162,0.2) 100%);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .stat-card .value {{ font-size: 1.8em; font-weight: bold; color: #667eea; }}
        .stat-card .label {{ font-size: 0.85em; opacity: 0.8; margin-top: 5px; }}
        .stat-card.highlight {{ background: linear-gradient(135deg, rgba(74,222,128,0.2) 0%, rgba(34,197,94,0.2) 100%); border-color: #4ade80; }}
        .stat-card.highlight .value {{ color: #4ade80; }}

        .insights-box {{
            background: linear-gradient(135deg, rgba(251,191,36,0.1) 0%, rgba(245,158,11,0.1) 100%);
            border: 1px solid rgba(251,191,36,0.3);
            border-radius: 12px;
            padding: 20px;
            margin-top: 20px;
        }}
        .insights-box h3 {{ color: #fbbf24; margin-bottom: 15px; }}
        .insights-box ul {{ list-style: none; }}
        .insights-box li {{ padding: 8px 0; padding-left: 25px; position: relative; }}
        .insights-box li:before {{ content: "✓"; position: absolute; left: 0; color: #4ade80; }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        th {{
            background: rgba(102,126,234,0.3);
            font-weight: 600;
            color: #667eea;
        }}
        tr:hover {{ background: rgba(255,255,255,0.05); }}

        .rank {{
            display: inline-block;
            width: 28px;
            height: 28px;
            line-height: 28px;
            text-align: center;
            border-radius: 50%;
            background: #667eea;
            font-weight: bold;
            margin-right: 10px;
        }}
        .rank.gold {{ background: linear-gradient(135deg, #f5af19, #f12711); }}
        .rank.silver {{ background: linear-gradient(135deg, #bdc3c7, #2c3e50); }}
        .rank.bronze {{ background: linear-gradient(135deg, #b8860b, #8b4513); }}

        .post-link {{ color: #667eea; text-decoration: none; }}
        .post-link:hover {{ text-decoration: underline; }}

        .growth-positive {{ color: #4ade80; }}
        .growth-negative {{ color: #f87171; }}

        .bar-chart {{
            display: flex;
            align-items: flex-end;
            height: 150px;
            gap: 10px;
            margin: 20px 0;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.2);
        }}
        .bar {{
            flex: 1;
            background: linear-gradient(to top, #667eea, #764ba2);
            border-radius: 5px 5px 0 0;
            position: relative;
            min-width: 30px;
            transition: all 0.3s;
        }}
        .bar:hover {{ opacity: 0.8; }}
        .bar .bar-label {{
            position: absolute;
            bottom: -25px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 0.7em;
            white-space: nowrap;
        }}
        .bar .bar-value {{
            position: absolute;
            top: -20px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 0.75em;
            color: #a78bfa;
        }}

        .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        @media (max-width: 768px) {{ .two-col {{ grid-template-columns: 1fr; }} }}

        .footer {{
            text-align: center;
            padding: 20px;
            opacity: 0.7;
            font-size: 0.9em;
        }}

        @media print {{
            body {{ background: #fff; color: #333; }}
            .section {{ background: #f5f5f5; }}
            .stat-card {{ background: #e8e8e8; }}
            .stat-card .value {{ color: #333; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Juan365 2025 Annual Report</h1>
            <div class="subtitle">Deep Performance Analysis</div>
            <div class="date-range">June 1, 2025 - December 31, 2025 (7 Months)</div>
        </div>

        <!-- Executive Summary -->
        <div class="section">
            <h2>Executive Summary</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="value">{format_number(overall['total_posts'])}</div>
                    <div class="label">Total Posts</div>
                </div>
                <div class="stat-card highlight">
                    <div class="value">{format_number(overall['total_views'])}</div>
                    <div class="label">Total Views</div>
                </div>
                <div class="stat-card highlight">
                    <div class="value">{format_number(overall['total_reach'])}</div>
                    <div class="label">Total Reach</div>
                </div>
                <div class="stat-card">
                    <div class="value">{format_number(overall['total_reactions'])}</div>
                    <div class="label">Reactions</div>
                </div>
                <div class="stat-card">
                    <div class="value">{format_number(overall['total_comments'])}</div>
                    <div class="label">Comments</div>
                </div>
                <div class="stat-card">
                    <div class="value">{format_number(overall['total_shares'])}</div>
                    <div class="label">Shares</div>
                </div>
                <div class="stat-card highlight">
                    <div class="value">{format_number(overall['total_engagement'])}</div>
                    <div class="label">Total Engagement</div>
                </div>
                <div class="stat-card">
                    <div class="value">{format_pct(engagement_rate)}</div>
                    <div class="label">Engagement Rate</div>
                </div>
            </div>

            <h3>Average Per Post</h3>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="value">{format_number(int(overall['avg_views_per_post']))}</div>
                    <div class="label">Avg Views/Post</div>
                </div>
                <div class="stat-card">
                    <div class="value">{format_number(int(overall['avg_engagement_per_post']))}</div>
                    <div class="label">Avg Engagement/Post</div>
                </div>
                <div class="stat-card">
                    <div class="value">{format_number(total_followers)}</div>
                    <div class="label">Total Followers</div>
                </div>
            </div>
        </div>

        <!-- Key Insights -->
        <div class="section">
            <h2>Key Insights & Recommendations</h2>
            <div class="insights-box">
                <h3>Performance Highlights</h3>
                <ul>
                    <li><strong>Best Content Type:</strong> {best_content['content_type'] if best_content else 'N/A'} with {format_number(int(best_content['avg_engagement'])) if best_content else '0'} avg engagement per post</li>
                    <li><strong>Best Day to Post:</strong> {best_day['day_name'] if best_day else 'N/A'} with {format_number(int(best_day['avg_engagement'])) if best_day else '0'} avg engagement</li>
                    <li><strong>Best Hour to Post:</strong> {f"{best_hour['hour_pht']:02d}:00 PHT" if best_hour else 'N/A'} with {format_number(int(best_hour['avg_engagement'])) if best_hour else '0'} avg engagement</li>
                    <li><strong>Engagement Rate:</strong> {format_pct(engagement_rate)} (engagement / reach)</li>
                    <li><strong>Growth Trend:</strong> Posts increased from {growth_data[0]['posts'] if growth_data else 0} (June) to {growth_data[-1]['posts'] if growth_data else 0} (December) - {((growth_data[-1]['posts'] - growth_data[0]['posts']) / growth_data[0]['posts'] * 100) if growth_data and growth_data[0]['posts'] > 0 else 0:.0f}% growth</li>
                </ul>
            </div>
        </div>

        <!-- Monthly Growth Analysis -->
        <div class="section">
            <h2>Monthly Growth Analysis</h2>
            <table>
                <thead>
                    <tr>
                        <th>Month</th>
                        <th>Posts</th>
                        <th>Views</th>
                        <th>Views Growth</th>
                        <th>Reach</th>
                        <th>Reach Growth</th>
                        <th>Engagement</th>
                        <th>Eng Growth</th>
                    </tr>
                </thead>
                <tbody>
"""

    month_names = {
        '2025-06': 'June', '2025-07': 'July', '2025-08': 'August',
        '2025-09': 'September', '2025-10': 'October',
        '2025-11': 'November', '2025-12': 'December'
    }

    for g in growth_data:
        month_display = month_names.get(g['month'], g['month'])
        views_class = "growth-positive" if g['views_growth'] >= 0 else "growth-negative"
        reach_class = "growth-positive" if g['reach_growth'] >= 0 else "growth-negative"
        eng_class = "growth-positive" if g['eng_growth'] >= 0 else "growth-negative"

        html += f"""
                    <tr>
                        <td><strong>{month_display}</strong></td>
                        <td>{g['posts']}</td>
                        <td>{format_number(g['views'])}</td>
                        <td class="{views_class}">{'+' if g['views_growth'] >= 0 else ''}{g['views_growth']:.1f}%</td>
                        <td>{format_number(g['reach'])}</td>
                        <td class="{reach_class}">{'+' if g['reach_growth'] >= 0 else ''}{g['reach_growth']:.1f}%</td>
                        <td>{format_number(g['engagement'])}</td>
                        <td class="{eng_class}">{'+' if g['eng_growth'] >= 0 else ''}{g['eng_growth']:.1f}%</td>
                    </tr>
"""

    # Calculate max engagement for bar chart scaling
    max_eng = max(g['engagement'] for g in growth_data) if growth_data else 1

    html += f"""
                </tbody>
            </table>

            <h3>Engagement Trend</h3>
            <div class="bar-chart">
"""
    for g in growth_data:
        height = (g['engagement'] / max_eng * 100) if max_eng > 0 else 0
        month_val = g.get('month', '')
        month_display = month_names.get(month_val, month_val) if month_val else 'N/A'
        month_short = month_display[:3] if month_display else 'N/A'
        html += f"""
                <div class="bar" style="height: {height}%;">
                    <span class="bar-value">{format_number(g['engagement'])}</span>
                    <span class="bar-label">{month_short}</span>
                </div>
"""

    html += """
            </div>
        </div>

        <!-- Day & Hour Analysis -->
        <div class="section">
            <h2>Posting Time Analysis</h2>
            <div class="two-col">
                <div>
                    <h3>Best Days to Post</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Day</th>
                                <th>Posts</th>
                                <th>Avg Engagement</th>
                                <th>Total Views</th>
                            </tr>
                        </thead>
                        <tbody>
"""

    for i, day in enumerate(day_performance):
        html += f"""
                            <tr>
                                <td>{'🏆 ' if i == 0 else ''}{day['day_name']}</td>
                                <td>{day['posts']}</td>
                                <td>{format_number(int(day['avg_engagement']))}</td>
                                <td>{format_number(day['views'])}</td>
                            </tr>
"""

    html += """
                        </tbody>
                    </table>
                </div>
                <div>
                    <h3>Best Hours to Post - PHT (Top 10)</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Hour</th>
                                <th>Posts</th>
                                <th>Avg Engagement</th>
                            </tr>
                        </thead>
                        <tbody>
"""

    for i, hour in enumerate(hour_performance):
        hour_display = f"{hour['hour_pht']:02d}:00 - {hour['hour_pht']:02d}:59"
        html += f"""
                            <tr>
                                <td>{'🏆 ' if i == 0 else ''}{hour_display}</td>
                                <td>{hour['posts']}</td>
                                <td>{format_number(int(hour['avg_engagement']))}</td>
                            </tr>
"""

    html += """
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Page Performance -->
        <div class="section">
            <h2>Page Performance Ranking</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Page</th>
                        <th>Followers</th>
                        <th>Posts</th>
                        <th>Views</th>
                        <th>Engagement</th>
                        <th>Avg Eng/Post</th>
                        <th>Eng Rate</th>
                    </tr>
                </thead>
                <tbody>
"""

    for i, page in enumerate(page_ranking, 1):
        rank_class = "gold" if i == 1 else "silver" if i == 2 else "bronze" if i == 3 else ""
        page_eng_rate = (page['engagement'] / page['reach'] * 100) if page['reach'] > 0 else 0

        html += f"""
                    <tr>
                        <td><span class="rank {rank_class}">{i}</span></td>
                        <td><strong>{page['page_name']}</strong></td>
                        <td>{format_number(page['followers'])}</td>
                        <td>{page['posts']}</td>
                        <td>{format_number(page['views'])}</td>
                        <td>{format_number(page['engagement'])}</td>
                        <td>{format_number(int(page['avg_engagement']))}</td>
                        <td>{format_pct(page_eng_rate)}</td>
                    </tr>
"""

    html += """
                </tbody>
            </table>
        </div>

        <!-- Content Type Analysis -->
        <div class="section">
            <h2>Content Type Performance</h2>
            <table>
                <thead>
                    <tr>
                        <th>Content Type</th>
                        <th>Posts</th>
                        <th>Total Views</th>
                        <th>Avg Views</th>
                        <th>Total Engagement</th>
                        <th>Avg Engagement</th>
                    </tr>
                </thead>
                <tbody>
"""

    for i, ct in enumerate(content_types):
        html += f"""
                    <tr>
                        <td>{'🏆 ' if i == 0 else ''}<strong>{ct['content_type']}</strong></td>
                        <td>{ct['posts']}</td>
                        <td>{format_number(ct['views'])}</td>
                        <td>{format_number(int(ct['avg_views']))}</td>
                        <td>{format_number(ct['engagement'])}</td>
                        <td>{format_number(int(ct['avg_engagement']))}</td>
                    </tr>
"""

    html += """
                </tbody>
            </table>
        </div>

        <!-- Viral Posts -->
        <div class="section">
            <h2>Most Viral Posts (Highest Share Rate)</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Page</th>
                        <th>Title</th>
                        <th>Shares</th>
                        <th>Views</th>
                        <th>Share Rate</th>
                        <th>Link</th>
                    </tr>
                </thead>
                <tbody>
"""

    for i, post in enumerate(viral_posts, 1):
        title = post['title'][:40] + "..." if post['title'] and len(post['title']) > 40 else (post['title'] or "No caption")
        permalink = post['permalink'] or "#"

        html += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{post['page_name']}</td>
                        <td>{title}</td>
                        <td>{format_number(post['shares'])}</td>
                        <td>{format_number(post['views'])}</td>
                        <td class="growth-positive">{post['share_rate']:.2f}%</td>
                        <td><a href="{permalink}" class="post-link" target="_blank">View</a></td>
                    </tr>
"""

    html += """
                </tbody>
            </table>
        </div>

        <!-- Top 20 Posts -->
        <div class="section">
            <h2>Top 20 Posts of 2025</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Page</th>
                        <th>Title</th>
                        <th>Type</th>
                        <th>Views</th>
                        <th>Reactions</th>
                        <th>Comments</th>
                        <th>Shares</th>
                        <th>Link</th>
                    </tr>
                </thead>
                <tbody>
"""

    for i, post in enumerate(top_posts, 1):
        title = post['title'][:35] + "..." if post['title'] and len(post['title']) > 35 else (post['title'] or "No caption")
        permalink = post['permalink'] or "#"
        rank_class = "gold" if i == 1 else "silver" if i == 2 else "bronze" if i == 3 else ""

        html += f"""
                    <tr>
                        <td><span class="rank {rank_class}">{i}</span></td>
                        <td>{post['page_name']}</td>
                        <td>{title}</td>
                        <td>{post['post_type'] or 'Post'}</td>
                        <td>{format_number(post['views'])}</td>
                        <td>{format_number(post['reactions'])}</td>
                        <td>{format_number(post['comments'])}</td>
                        <td>{format_number(post['shares'])}</td>
                        <td><a href="{permalink}" class="post-link" target="_blank">View</a></td>
                    </tr>
"""

    html += f"""
                </tbody>
            </table>
        </div>

        <!-- Current Followers -->
        <div class="section">
            <h2>Current Page Followers</h2>
            <div class="stats-grid">
"""

    for f in followers:
        if f['followers'] > 0:
            html += f"""
                <div class="stat-card">
                    <div class="value">{format_number(f['followers'])}</div>
                    <div class="label">{f['page_name']}</div>
                </div>
"""

    html += f"""
            </div>
            <p style="margin-top: 15px; opacity: 0.7; font-size: 0.9em;">
                <strong>Total Followers:</strong> {format_number(total_followers)}
            </p>
        </div>

        <div class="footer">
            <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            <p>Juan365 Social Media Analytics - 2025 Annual Report</p>
        </div>
    </div>
</body>
</html>
"""

    # Save report
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Report generated: {OUTPUT_PATH}")
    return str(OUTPUT_PATH)

if __name__ == "__main__":
    generate_report()
