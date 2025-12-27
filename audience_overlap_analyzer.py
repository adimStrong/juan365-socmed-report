#!/usr/bin/env python3
"""
JuanBabes Audience Overlap Analyzer
Analyze content similarity and audience overlap between Facebook pages
"""

import sys
import argparse
import re
from pathlib import Path
from datetime import datetime, date
from collections import Counter
from typing import Optional, List, Dict, Any, Tuple
import math
import json

from database import (
    ensure_initialized, db_connection, get_all_pages, get_posts,
    get_post_type_performance, get_database_stats
)
from models import OverlapResult
from config import REPORTS_DIR


def extract_keywords(text: str) -> List[str]:
    """
    Extract keywords from text for content similarity analysis.

    Args:
        text: Input text (title, description, etc.)

    Returns:
        List of lowercase keywords
    """
    if not text:
        return []

    # Remove URLs
    text = re.sub(r'http\S+|www\.\S+', '', text)

    # Remove special characters, keep letters and spaces
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)

    # Split and filter short words
    words = [w.lower().strip() for w in text.split()]
    words = [w for w in words if len(w) >= 3]

    # Remove common stopwords
    stopwords = {
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can',
        'had', 'her', 'was', 'one', 'our', 'out', 'has', 'have', 'been',
        'this', 'that', 'with', 'they', 'from', 'will', 'what', 'when',
        'where', 'which', 'their', 'there', 'about', 'would', 'could',
        'should', 'your', 'just', 'like', 'more', 'some', 'into', 'only',
        'other', 'than', 'then', 'very', 'also', 'back', 'after', 'most',
        'over', 'such', 'each', 'those', 'both', 'being', 'here', 'live',
        'stream', 'video', 'post', 'watch', 'now', 'new', 'today',
    }

    return [w for w in words if w not in stopwords]


def get_page_keywords(page_id: str, limit: int = 500) -> Counter:
    """
    Get keyword frequency for a page's content.

    Args:
        page_id: Page ID
        limit: Max posts to analyze

    Returns:
        Counter of keyword frequencies
    """
    posts = get_posts(page_id=page_id, limit=limit)
    all_keywords = []

    for post in posts:
        title = post.get('title', '') or ''
        description = post.get('description', '') or ''
        all_keywords.extend(extract_keywords(title))
        all_keywords.extend(extract_keywords(description))

    return Counter(all_keywords)


def calculate_cosine_similarity(counter1: Counter, counter2: Counter) -> float:
    """
    Calculate cosine similarity between two keyword counters.

    Args:
        counter1: First keyword counter
        counter2: Second keyword counter

    Returns:
        Similarity score from 0 to 1
    """
    if not counter1 or not counter2:
        return 0.0

    # Get all unique keywords
    all_keys = set(counter1.keys()) | set(counter2.keys())

    # Calculate dot product and magnitudes
    dot_product = sum(counter1.get(k, 0) * counter2.get(k, 0) for k in all_keys)
    mag1 = math.sqrt(sum(v ** 2 for v in counter1.values()))
    mag2 = math.sqrt(sum(v ** 2 for v in counter2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot_product / (mag1 * mag2)


def analyze_content_similarity(page_id_1: str, page_id_2: str) -> Dict[str, Any]:
    """
    Analyze content similarity between two pages.

    Args:
        page_id_1: First page ID
        page_id_2: Second page ID

    Returns:
        Dict with similarity metrics
    """
    keywords1 = get_page_keywords(page_id_1)
    keywords2 = get_page_keywords(page_id_2)

    # Cosine similarity
    cosine_sim = calculate_cosine_similarity(keywords1, keywords2)

    # Common keywords
    common = set(keywords1.keys()) & set(keywords2.keys())
    unique_1 = set(keywords1.keys()) - set(keywords2.keys())
    unique_2 = set(keywords2.keys()) - set(keywords1.keys())

    # Jaccard similarity (keyword overlap)
    all_keywords = set(keywords1.keys()) | set(keywords2.keys())
    jaccard = len(common) / len(all_keywords) if all_keywords else 0

    return {
        'cosine_similarity': round(cosine_sim * 100, 2),
        'jaccard_similarity': round(jaccard * 100, 2),
        'common_keywords': len(common),
        'unique_page_1': len(unique_1),
        'unique_page_2': len(unique_2),
        'top_common': [k for k, _ in Counter({k: keywords1[k] + keywords2[k]
                                               for k in common}).most_common(10)],
        'top_unique_1': [k for k, _ in Counter({k: keywords1[k]
                                                 for k in unique_1}).most_common(5)],
        'top_unique_2': [k for k, _ in Counter({k: keywords2[k]
                                                 for k in unique_2}).most_common(5)],
    }


def analyze_posting_patterns(page_id_1: str, page_id_2: str) -> Dict[str, Any]:
    """
    Analyze posting time patterns between two pages.

    Args:
        page_id_1: First page ID
        page_id_2: Second page ID

    Returns:
        Dict with timing pattern metrics
    """
    posts1 = get_posts(page_id=page_id_1, limit=500)
    posts2 = get_posts(page_id=page_id_2, limit=500)

    def extract_hour_distribution(posts: List[Dict]) -> Counter:
        hours = Counter()
        for post in posts:
            publish_time = post.get('publish_time')
            if publish_time:
                try:
                    if isinstance(publish_time, str):
                        # Parse the datetime string
                        dt = datetime.fromisoformat(publish_time.replace('Z', '+00:00'))
                    else:
                        dt = publish_time
                    hours[dt.hour] += 1
                except (ValueError, AttributeError):
                    pass
        return hours

    def extract_day_distribution(posts: List[Dict]) -> Counter:
        days = Counter()
        for post in posts:
            publish_time = post.get('publish_time')
            if publish_time:
                try:
                    if isinstance(publish_time, str):
                        dt = datetime.fromisoformat(publish_time.replace('Z', '+00:00'))
                    else:
                        dt = publish_time
                    days[dt.weekday()] += 1  # 0=Monday, 6=Sunday
                except (ValueError, AttributeError):
                    pass
        return days

    hours1 = extract_hour_distribution(posts1)
    hours2 = extract_hour_distribution(posts2)
    days1 = extract_day_distribution(posts1)
    days2 = extract_day_distribution(posts2)

    # Calculate correlation for hours
    hour_correlation = calculate_cosine_similarity(hours1, hours2)
    day_correlation = calculate_cosine_similarity(days1, days2)

    # Find peak hours
    peak_hours_1 = [h for h, _ in hours1.most_common(3)]
    peak_hours_2 = [h for h, _ in hours2.most_common(3)]
    common_peak_hours = set(peak_hours_1) & set(peak_hours_2)

    # Find peak days
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    peak_days_1 = [day_names[d] for d, _ in days1.most_common(3)]
    peak_days_2 = [day_names[d] for d, _ in days2.most_common(3)]

    return {
        'hour_correlation': round(hour_correlation, 3),
        'day_correlation': round(day_correlation, 3),
        'peak_hours_page_1': peak_hours_1,
        'peak_hours_page_2': peak_hours_2,
        'common_peak_hours': list(common_peak_hours),
        'peak_days_page_1': peak_days_1,
        'peak_days_page_2': peak_days_2,
        'posts_analyzed_1': len(posts1),
        'posts_analyzed_2': len(posts2),
    }


def analyze_engagement_patterns(page_id_1: str, page_id_2: str) -> Dict[str, Any]:
    """
    Analyze engagement patterns between two pages.

    Args:
        page_id_1: First page ID
        page_id_2: Second page ID

    Returns:
        Dict with engagement pattern metrics
    """
    posts1 = get_posts(page_id=page_id_1, limit=500)
    posts2 = get_posts(page_id=page_id_2, limit=500)

    def calculate_engagement_metrics(posts: List[Dict]) -> Dict[str, float]:
        if not posts:
            return {'avg_engagement': 0, 'avg_reactions': 0, 'avg_comments': 0,
                    'avg_shares': 0, 'avg_views': 0, 'engagement_rate': 0}

        total_reactions = sum(p.get('reactions', 0) or 0 for p in posts)
        total_comments = sum(p.get('comments', 0) or 0 for p in posts)
        total_shares = sum(p.get('shares', 0) or 0 for p in posts)
        total_views = sum(p.get('views', 0) or 0 for p in posts)
        total_reach = sum(p.get('reach', 0) or 0 for p in posts)
        total_engagement = total_reactions + total_comments + total_shares

        n = len(posts)
        engagement_rate = (total_engagement / total_reach * 100) if total_reach else 0

        return {
            'avg_engagement': round(total_engagement / n, 2),
            'avg_reactions': round(total_reactions / n, 2),
            'avg_comments': round(total_comments / n, 2),
            'avg_shares': round(total_shares / n, 2),
            'avg_views': round(total_views / n, 2),
            'engagement_rate': round(engagement_rate, 4),
            'total_posts': n,
        }

    def get_reaction_distribution(posts: List[Dict]) -> Counter:
        # Use engagement levels as proxy for reaction distribution
        levels = Counter()
        for post in posts:
            engagement = (post.get('reactions', 0) or 0) + \
                        (post.get('comments', 0) or 0) + \
                        (post.get('shares', 0) or 0)
            if engagement < 10:
                levels['low'] += 1
            elif engagement < 50:
                levels['medium'] += 1
            elif engagement < 200:
                levels['high'] += 1
            else:
                levels['viral'] += 1
        return levels

    metrics1 = calculate_engagement_metrics(posts1)
    metrics2 = calculate_engagement_metrics(posts2)
    dist1 = get_reaction_distribution(posts1)
    dist2 = get_reaction_distribution(posts2)

    # Calculate pattern similarity
    pattern_similarity = calculate_cosine_similarity(dist1, dist2)

    # Compare engagement rates
    rate_diff = abs(metrics1['engagement_rate'] - metrics2['engagement_rate'])
    rate_similarity = max(0, 100 - rate_diff * 100)  # Convert to similarity

    return {
        'page_1_metrics': metrics1,
        'page_2_metrics': metrics2,
        'pattern_similarity': round(pattern_similarity * 100, 2),
        'engagement_rate_similarity': round(rate_similarity, 2),
        'page_1_distribution': dict(dist1),
        'page_2_distribution': dict(dist2),
    }


def analyze_post_types(page_id_1: str, page_id_2: str) -> Dict[str, Any]:
    """
    Analyze post type distribution between two pages.

    Args:
        page_id_1: First page ID
        page_id_2: Second page ID

    Returns:
        Dict with post type comparison
    """
    perf1 = get_post_type_performance(page_id_1)
    perf2 = get_post_type_performance(page_id_2)

    def to_distribution(perf: List[Dict]) -> Dict[str, float]:
        total = sum(p['post_count'] for p in perf)
        if not total:
            return {}
        return {p['post_type']: round(p['post_count'] / total * 100, 1) for p in perf}

    dist1 = to_distribution(perf1)
    dist2 = to_distribution(perf2)

    # Calculate similarity
    all_types = set(dist1.keys()) | set(dist2.keys())
    counter1 = Counter({t: dist1.get(t, 0) for t in all_types})
    counter2 = Counter({t: dist2.get(t, 0) for t in all_types})
    similarity = calculate_cosine_similarity(counter1, counter2)

    return {
        'page_1_distribution': dist1,
        'page_2_distribution': dist2,
        'distribution_similarity': round(similarity * 100, 2),
        'common_types': list(set(dist1.keys()) & set(dist2.keys())),
    }


def analyze_overlap(
    page_id_1: str,
    page_id_2: str,
    save_to_db: bool = True
) -> OverlapResult:
    """
    Perform comprehensive overlap analysis between two pages.

    Args:
        page_id_1: First page ID
        page_id_2: Second page ID
        save_to_db: Whether to save results to database

    Returns:
        OverlapResult with all metrics
    """
    ensure_initialized()

    # Run all analyses
    content = analyze_content_similarity(page_id_1, page_id_2)
    timing = analyze_posting_patterns(page_id_1, page_id_2)
    engagement = analyze_engagement_patterns(page_id_1, page_id_2)
    post_types = analyze_post_types(page_id_1, page_id_2)

    # Calculate overall scores
    content_score = (content['cosine_similarity'] + content['jaccard_similarity']) / 2
    timing_score = (timing['hour_correlation'] + timing['day_correlation']) / 2 * 100
    engagement_score = engagement['pattern_similarity']

    # Estimate overall overlap (weighted average)
    estimated_overlap = (
        content_score * 0.4 +
        timing_score * 0.3 +
        engagement_score * 0.3
    )

    # Generate recommendations
    recommendations = []

    if content_score > 50:
        recommendations.append("High content similarity - consider differentiating topics")
    elif content_score < 20:
        recommendations.append("Low content similarity - pages target different topics")

    if timing['common_peak_hours']:
        recommendations.append(f"Both pages peak at hours: {timing['common_peak_hours']}")

    if engagement['page_1_metrics']['engagement_rate'] > engagement['page_2_metrics']['engagement_rate']:
        recommendations.append("Page 1 has higher engagement rate")
    else:
        recommendations.append("Page 2 has higher engagement rate")

    if post_types['distribution_similarity'] > 70:
        recommendations.append("Similar content type mix - audiences may overlap")

    result = OverlapResult(
        page_id_1=page_id_1,
        page_id_2=page_id_2,
        analysis_date=date.today(),
        content_similarity=content_score,
        timing_correlation=(timing['hour_correlation'] + timing['day_correlation']) / 2,
        engagement_pattern_score=engagement_score,
        estimated_overlap_percentage=estimated_overlap,
        analysis_method='combined',
        recommendations=recommendations,
        notes=json.dumps({
            'content': content,
            'timing': timing,
            'engagement': engagement,
            'post_types': post_types,
        })
    )

    # Save to database
    if save_to_db:
        with db_connection() as conn:
            conn.execute("""
                INSERT INTO audience_overlap (
                    page_id_1, page_id_2, analysis_date,
                    overlap_percentage, content_similarity_score,
                    posting_time_correlation, engagement_pattern_score,
                    analysis_method, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.page_id_1,
                result.page_id_2,
                result.analysis_date.isoformat(),
                result.estimated_overlap_percentage,
                result.content_similarity,
                result.timing_correlation,
                result.engagement_pattern_score,
                result.analysis_method,
                result.notes,
            ))

    return result


def generate_report(result: OverlapResult, output_path: Optional[Path] = None) -> str:
    """
    Generate HTML report for overlap analysis.

    Args:
        result: OverlapResult to report on
        output_path: Path to save HTML file

    Returns:
        HTML content
    """
    notes = json.loads(result.notes) if result.notes else {}

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Audience Overlap Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a73e8; }}
        .metric-card {{ background: #f8f9fa; border-radius: 8px; padding: 15px; margin: 10px 0; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #1a73e8; }}
        .metric-label {{ color: #5f6368; }}
        .section {{ margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f1f3f4; }}
        .recommendation {{ background: #e8f5e9; padding: 10px; margin: 5px 0; border-radius: 4px; }}
        .progress {{ background: #e0e0e0; border-radius: 10px; height: 20px; }}
        .progress-bar {{ background: #1a73e8; height: 100%; border-radius: 10px; }}
    </style>
</head>
<body>
    <h1>Audience Overlap Analysis Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

    <div class="section">
        <h2>Overview</h2>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
            <div class="metric-card">
                <div class="metric-value">{result.estimated_overlap_percentage:.1f}%</div>
                <div class="metric-label">Estimated Overlap</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{result.content_similarity:.1f}%</div>
                <div class="metric-label">Content Similarity</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{result.timing_correlation:.2f}</div>
                <div class="metric-label">Timing Correlation</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{result.engagement_pattern_score:.1f}%</div>
                <div class="metric-label">Engagement Similarity</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Pages Compared</h2>
        <table>
            <tr><th>Page 1</th><td>{result.page_id_1}</td></tr>
            <tr><th>Page 2</th><td>{result.page_id_2}</td></tr>
            <tr><th>Analysis Date</th><td>{result.analysis_date}</td></tr>
        </table>
    </div>
"""

    if notes.get('content'):
        content = notes['content']
        html += f"""
    <div class="section">
        <h2>Content Analysis</h2>
        <table>
            <tr><th>Cosine Similarity</th><td>{content.get('cosine_similarity', 0)}%</td></tr>
            <tr><th>Jaccard Similarity</th><td>{content.get('jaccard_similarity', 0)}%</td></tr>
            <tr><th>Common Keywords</th><td>{content.get('common_keywords', 0)}</td></tr>
            <tr><th>Top Common Keywords</th><td>{', '.join(content.get('top_common', []))}</td></tr>
        </table>
    </div>
"""

    if notes.get('timing'):
        timing = notes['timing']
        html += f"""
    <div class="section">
        <h2>Posting Patterns</h2>
        <table>
            <tr><th>Hour Correlation</th><td>{timing.get('hour_correlation', 0)}</td></tr>
            <tr><th>Day Correlation</th><td>{timing.get('day_correlation', 0)}</td></tr>
            <tr><th>Peak Hours (Page 1)</th><td>{timing.get('peak_hours_page_1', [])}</td></tr>
            <tr><th>Peak Hours (Page 2)</th><td>{timing.get('peak_hours_page_2', [])}</td></tr>
            <tr><th>Common Peak Hours</th><td>{timing.get('common_peak_hours', [])}</td></tr>
        </table>
    </div>
"""

    if notes.get('engagement'):
        eng = notes['engagement']
        html += f"""
    <div class="section">
        <h2>Engagement Comparison</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Page 1</th>
                <th>Page 2</th>
            </tr>
            <tr>
                <td>Avg Engagement</td>
                <td>{eng['page_1_metrics'].get('avg_engagement', 0)}</td>
                <td>{eng['page_2_metrics'].get('avg_engagement', 0)}</td>
            </tr>
            <tr>
                <td>Engagement Rate</td>
                <td>{eng['page_1_metrics'].get('engagement_rate', 0)}%</td>
                <td>{eng['page_2_metrics'].get('engagement_rate', 0)}%</td>
            </tr>
            <tr>
                <td>Avg Views</td>
                <td>{eng['page_1_metrics'].get('avg_views', 0)}</td>
                <td>{eng['page_2_metrics'].get('avg_views', 0)}</td>
            </tr>
        </table>
    </div>
"""

    html += """
    <div class="section">
        <h2>Recommendations</h2>
"""
    for rec in result.recommendations:
        html += f'        <div class="recommendation">{rec}</div>\n'

    html += """
    </div>
</body>
</html>
"""

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Report saved to: {output_path}")

    return html


def get_overlap_history(page_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Get overlap analysis history."""
    ensure_initialized()
    with db_connection() as conn:
        if page_id:
            cursor = conn.execute("""
                SELECT * FROM audience_overlap
                WHERE page_id_1 = ? OR page_id_2 = ?
                ORDER BY analysis_date DESC
                LIMIT ?
            """, (page_id, page_id, limit))
        else:
            cursor = conn.execute("""
                SELECT * FROM audience_overlap
                ORDER BY analysis_date DESC
                LIMIT ?
            """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='JuanBabes Audience Overlap Analyzer'
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze overlap between two pages')
    analyze_parser.add_argument('page1', help='First page ID')
    analyze_parser.add_argument('page2', help='Second page ID')
    analyze_parser.add_argument('--no-save', action='store_true', help='Don\'t save to database')
    analyze_parser.add_argument('--report', type=Path, help='Generate HTML report')

    # Content command
    content_parser = subparsers.add_parser('content', help='Analyze content similarity only')
    content_parser.add_argument('page1', help='First page ID')
    content_parser.add_argument('page2', help='Second page ID')

    # Timing command
    timing_parser = subparsers.add_parser('timing', help='Analyze posting patterns only')
    timing_parser.add_argument('page1', help='First page ID')
    timing_parser.add_argument('page2', help='Second page ID')

    # History command
    history_parser = subparsers.add_parser('history', help='Show analysis history')
    history_parser.add_argument('--page', help='Filter by page ID')

    # Pages command
    subparsers.add_parser('pages', help='List all pages in database')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    ensure_initialized()

    if args.command == 'analyze':
        print(f"Analyzing overlap between {args.page1} and {args.page2}...")
        result = analyze_overlap(args.page1, args.page2, save_to_db=not args.no_save)

        print(f"\n{'='*60}")
        print(f"OVERLAP ANALYSIS RESULTS")
        print(f"{'='*60}")
        print(f"Pages: {args.page1} vs {args.page2}")
        print(f"Date: {result.analysis_date}")
        print(f"\nScores:")
        print(f"  Estimated Overlap: {result.estimated_overlap_percentage:.1f}%")
        print(f"  Content Similarity: {result.content_similarity:.1f}%")
        print(f"  Timing Correlation: {result.timing_correlation:.3f}")
        print(f"  Engagement Pattern: {result.engagement_pattern_score:.1f}%")
        print(f"\nRecommendations:")
        for rec in result.recommendations:
            print(f"  - {rec}")

        if args.report:
            generate_report(result, args.report)

    elif args.command == 'content':
        result = analyze_content_similarity(args.page1, args.page2)
        print(f"\nContent Similarity Analysis:")
        print(f"  Cosine Similarity: {result['cosine_similarity']}%")
        print(f"  Jaccard Similarity: {result['jaccard_similarity']}%")
        print(f"  Common Keywords: {result['common_keywords']}")
        print(f"  Top Common: {', '.join(result['top_common'])}")

    elif args.command == 'timing':
        result = analyze_posting_patterns(args.page1, args.page2)
        print(f"\nPosting Pattern Analysis:")
        print(f"  Hour Correlation: {result['hour_correlation']}")
        print(f"  Day Correlation: {result['day_correlation']}")
        print(f"  Peak Hours (Page 1): {result['peak_hours_page_1']}")
        print(f"  Peak Hours (Page 2): {result['peak_hours_page_2']}")
        print(f"  Common Peak Hours: {result['common_peak_hours']}")

    elif args.command == 'history':
        history = get_overlap_history(page_id=args.page if hasattr(args, 'page') else None)
        if history:
            print("\nAnalysis History:")
            print("-" * 60)
            for h in history:
                print(f"  {h['analysis_date']}: {h['page_id_1']} vs {h['page_id_2']}")
                print(f"    Overlap: {h['overlap_percentage']:.1f}%")
        else:
            print("No analysis history found")

    elif args.command == 'pages':
        pages = get_all_pages()
        if pages:
            print("\nPages in Database:")
            print("-" * 40)
            for p in pages:
                comp = " (competitor)" if p['is_competitor'] else ""
                print(f"  {p['page_id']}: {p['page_name']}{comp}")
        else:
            print("No pages found. Import some CSV data first.")


if __name__ == '__main__':
    main()
