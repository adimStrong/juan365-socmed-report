"""
Django REST Framework views for JuanBabes Analytics API
Updated for 5 pages with direct post metrics
"""

import csv
import io
from datetime import datetime, timedelta
from django.db.models import Sum, Avg, Count, Min, Max, F
from django.db.models.functions import TruncDate
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters import rest_framework as filters

from .models import Page, Post, PostMetrics, CsvImport, AudienceOverlap
from .serializers import (
    PageSerializer, PostListSerializer, PostDetailSerializer,
    PostMetricsSerializer, CsvImportSerializer, AudienceOverlapSerializer,
    DashboardStatsSerializer, DailyEngagementSerializer, PostTypeStatsSerializer
)


class PageViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Facebook pages."""
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    filterset_fields = ['is_competitor']
    search_fields = ['page_name']
    ordering_fields = ['page_name', 'fan_count', 'followers_count']


class PostFilter(filters.FilterSet):
    """Filter for posts."""
    start_date = filters.DateFilter(field_name='publish_time', lookup_expr='gte')
    end_date = filters.DateFilter(field_name='publish_time', lookup_expr='lte')
    page = filters.CharFilter(field_name='page_id')

    class Meta:
        model = Post
        fields = ['page', 'post_type', 'is_crosspost', 'is_share']


class PostViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for posts."""
    queryset = Post.objects.select_related('page').prefetch_related('metrics')
    filterset_class = PostFilter
    search_fields = ['title', 'description']
    ordering_fields = ['publish_time', 'post_type']
    ordering = ['-publish_time']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PostDetailSerializer
        return PostListSerializer


class CsvImportViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for CSV import history."""
    queryset = CsvImport.objects.all()
    serializer_class = CsvImportSerializer
    filterset_fields = ['status']
    ordering = ['-import_date']


class AudienceOverlapViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for audience overlap analysis."""
    queryset = AudienceOverlap.objects.select_related('page_1', 'page_2')
    serializer_class = AudienceOverlapSerializer
    ordering = ['-analysis_date']


class DashboardStatsView(APIView):
    """Dashboard summary statistics - now using direct post columns."""

    def get(self, request):
        from django.db import connection

        with connection.cursor() as cursor:
            # Get totals directly from posts table
            cursor.execute("""
                SELECT
                    COALESCE(SUM(reactions_total), 0) as total_reactions,
                    COALESCE(SUM(comments_count), 0) as total_comments,
                    COALESCE(SUM(shares_count), 0) as total_shares,
                    COALESCE(SUM(total_engagement), 0) as total_engagement,
                    COALESCE(SUM(pes), 0) as total_pes,
                    COALESCE(SUM(views_count), 0) as total_views,
                    COALESCE(SUM(reach_count), 0) as total_reach
                FROM posts
                WHERE reactions_total > 0 OR comments_count > 0 OR shares_count > 0
            """)
            row = cursor.fetchone()
            total_reactions = row[0] or 0
            total_comments = row[1] or 0
            total_shares = row[2] or 0
            total_engagement = row[3] or 0
            total_pes = row[4] or 0
            total_views = row[5] or 0
            total_reach = row[6] or 0

            # Get date range
            cursor.execute("""
                SELECT MIN(publish_time), MAX(publish_time)
                FROM posts
                WHERE publish_time IS NOT NULL
            """)
            date_row = cursor.fetchone()
            start_date = str(date_row[0])[:10] if date_row[0] else None
            end_date = str(date_row[1])[:10] if date_row[1] else None

            # Get counts
            cursor.execute("SELECT COUNT(*) FROM posts WHERE reactions_total > 0 OR comments_count > 0")
            post_count = cursor.fetchone()[0]

            # Count unique pages with posts
            cursor.execute("""
                SELECT COUNT(DISTINCT page_id) FROM posts
                WHERE reactions_total > 0 OR comments_count > 0
            """)
            active_page_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM pages")
            total_page_count = cursor.fetchone()[0]

        avg_engagement = total_engagement / post_count if post_count > 0 else 0
        avg_pes = total_pes / post_count if post_count > 0 else 0
        avg_views = total_views / post_count if post_count > 0 else 0
        avg_reach = total_reach / post_count if post_count > 0 else 0

        stats = {
            'total_posts': post_count,
            'total_pages': active_page_count,
            'all_pages': total_page_count,
            'total_reactions': total_reactions,
            'total_comments': total_comments,
            'total_shares': total_shares,
            'total_engagement': total_engagement,
            'total_pes': round(total_pes, 1),
            'total_views': total_views,
            'total_reach': total_reach,
            'avg_engagement': round(avg_engagement, 1),
            'avg_pes': round(avg_pes, 1),
            'avg_views': round(avg_views, 1),
            'avg_reach': round(avg_reach, 1),
            'date_range_start': start_date,
            'date_range_end': end_date,
        }

        return Response(stats)


class DailyEngagementView(APIView):
    """Daily engagement statistics for charts."""

    def get(self, request):
        from django.db import connection

        days = int(request.query_params.get('days', 30))
        page_id = request.query_params.get('page')

        page_filter = f"AND page_id = '{page_id}'" if page_id else ""

        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT
                    DATE(publish_time) as post_date,
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
                    AND DATE(publish_time) >= DATE('now', '-{days} days')
                    AND (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
                    {page_filter}
                GROUP BY DATE(publish_time)
                ORDER BY post_date
            """)

            result = []
            for row in cursor.fetchall():
                result.append({
                    'date': row[0],
                    'posts': row[1],
                    'reactions': row[2],
                    'comments': row[3],
                    'shares': row[4],
                    'engagement': row[5],
                    'pes': round(row[6], 1),
                    'views': row[7],
                    'reach': row[8]
                })

        return Response(result)


class PostTypeStatsView(APIView):
    """Post type distribution statistics."""

    def get(self, request):
        from django.db import connection

        page_id = request.query_params.get('page')
        page_filter = f"AND page_id = '{page_id}'" if page_id else ""

        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT
                    COALESCE(post_type, 'Unknown') as post_type,
                    COUNT(*) as count,
                    COALESCE(SUM(reactions_total), 0) as reactions,
                    COALESCE(SUM(comments_count), 0) as comments,
                    COALESCE(SUM(shares_count), 0) as shares,
                    COALESCE(SUM(total_engagement), 0) as total_engagement,
                    COALESCE(AVG(pes), 0) as avg_pes
                FROM posts
                WHERE (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
                    {page_filter}
                GROUP BY post_type
                ORDER BY count DESC
            """)

            result = []
            for row in cursor.fetchall():
                count = row[1]
                total_engagement = row[5]
                result.append({
                    'post_type': row[0],
                    'count': count,
                    'reactions': row[2],
                    'comments': row[3],
                    'shares': row[4],
                    'total_engagement': total_engagement,
                    'avg_engagement': round(total_engagement / count, 1) if count > 0 else 0,
                    'avg_pes': round(row[6], 1)
                })

        return Response(result)


class TopPostsView(APIView):
    """Top performing posts."""

    def get(self, request):
        from django.db import connection

        limit = int(request.query_params.get('limit', 10))
        metric = request.query_params.get('metric', 'engagement')
        page_id = request.query_params.get('page')

        page_filter = f"AND p.page_id = '{page_id}'" if page_id else ""

        # Map metric to SQL column
        order_by = {
            'engagement': 'total_engagement',
            'reactions': 'reactions_total',
            'comments': 'comments_count',
            'shares': 'shares_count',
            'pes': 'pes',
        }.get(metric, 'total_engagement')

        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT
                    p.post_id,
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
                WHERE (p.reactions_total > 0 OR p.comments_count > 0 OR p.shares_count > 0)
                    {page_filter}
                ORDER BY p.{order_by} DESC
                LIMIT {limit}
            """)

            result = []
            for row in cursor.fetchall():
                result.append({
                    'post_id': row[0],
                    'page_name': row[1],
                    'title': row[2],
                    'post_type': row[3],
                    'publish_time': row[4],
                    'permalink': row[5],
                    'reactions': row[6],
                    'comments': row[7],
                    'shares': row[8],
                    'engagement': row[9],
                    'pes': round(row[10], 1),
                })

        return Response(result)


class PageComparisonView(APIView):
    """Compare engagement across pages."""

    def get(self, request):
        from django.db import connection

        with connection.cursor() as cursor:
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
                GROUP BY pg.page_id, pg.page_name, pg.fan_count, pg.followers_count
                HAVING COUNT(p.post_id) > 0
                ORDER BY total_engagement DESC
            """)

            result = []
            for row in cursor.fetchall():
                post_count = row[4]
                total_engagement = row[8]
                result.append({
                    'page_id': row[0],
                    'page_name': row[1],
                    'fan_count': row[2],
                    'followers_count': row[3],
                    'post_count': post_count,
                    'total_reactions': row[5],
                    'total_comments': row[6],
                    'total_shares': row[7],
                    'total_engagement': total_engagement,
                    'avg_engagement': round(total_engagement / post_count, 1) if post_count > 0 else 0,
                    'avg_pes': round(row[9], 1),
                    'total_views': row[10],
                    'total_reach': row[11]
                })

        return Response(result)


class TimeSeriesView(APIView):
    """Time series analytics: monthly, weekly, day-of-week."""

    def get(self, request):
        from django.db import connection

        with connection.cursor() as cursor:
            # Monthly data
            cursor.execute("""
                SELECT
                    strftime('%Y-%m', publish_time) as month,
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
                GROUP BY strftime('%Y-%m', publish_time)
                ORDER BY month DESC
                LIMIT 6
            """)

            monthly = []
            prev_engagement = None
            rows = list(cursor.fetchall())
            for row in reversed(rows):
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

            # Weekly data
            cursor.execute("""
                SELECT
                    strftime('%Y-%W', publish_time) as week,
                    MIN(DATE(publish_time)) as week_start,
                    MAX(DATE(publish_time)) as week_end,
                    COUNT(*) as post_count,
                    COALESCE(SUM(views_count), 0) as views,
                    COALESCE(SUM(reach_count), 0) as reach,
                    COALESCE(SUM(total_engagement), 0) as engagement,
                    COALESCE(AVG(total_engagement), 0) as avg_engagement
                FROM posts
                WHERE publish_time IS NOT NULL
                    AND DATE(publish_time) >= DATE('now', '-28 days')
                    AND (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
                GROUP BY strftime('%Y-%W', publish_time)
                ORDER BY week DESC
                LIMIT 4
            """)

            weekly = []
            prev_weekly = None
            rows = list(cursor.fetchall())
            for row in reversed(rows):
                engagement = row[6]
                wow_change = None
                if prev_weekly and prev_weekly > 0:
                    wow_change = round(((engagement - prev_weekly) / prev_weekly) * 100, 1)
                weekly.append({
                    "week": row[0],
                    "week_start": row[1],
                    "week_end": row[2],
                    "posts": row[3],
                    "views": row[4],
                    "reach": row[5],
                    "engagement": engagement,
                    "avg_engagement": round(row[7], 1),
                    "wow_change": wow_change
                })
                prev_weekly = engagement

            # Day of week
            cursor.execute("""
                SELECT
                    CASE CAST(strftime('%w', publish_time) AS INTEGER)
                        WHEN 0 THEN 'Sun'
                        WHEN 1 THEN 'Mon'
                        WHEN 2 THEN 'Tue'
                        WHEN 3 THEN 'Wed'
                        WHEN 4 THEN 'Thu'
                        WHEN 5 THEN 'Fri'
                        WHEN 6 THEN 'Sat'
                    END as day_name,
                    CAST(strftime('%w', publish_time) AS INTEGER) as day_num,
                    COUNT(*) as post_count,
                    COALESCE(SUM(total_engagement), 0) as total_engagement,
                    COALESCE(AVG(total_engagement), 0) as avg_engagement
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
                if row[4] > max_avg:
                    max_avg = row[4]

            for row in rows:
                day_of_week.append({
                    "day": row[0],
                    "day_num": row[1],
                    "posts": row[2],
                    "total_engagement": row[3],
                    "avg_engagement": round(row[4], 1),
                    "is_best": row[4] == max_avg
                })

        # Generate insights
        insights = []
        if len(monthly) >= 2:
            recent = monthly[-1]
            if recent.get('mom_change') and recent['mom_change'] > 0:
                insights.append({
                    "type": "trend_up",
                    "title": "Engagement Growing",
                    "text": f"Engagement up {recent['mom_change']}% this month"
                })

        best_day = next((d for d in day_of_week if d['is_best']), None)
        if best_day:
            insights.append({
                "type": "best_day",
                "title": f"{best_day['day']} is Best",
                "text": f"{best_day['day']} generates {best_day['avg_engagement']:.0f} avg engagement"
            })

        return Response({
            "monthly": list(reversed(monthly)),
            "weekly": list(reversed(weekly)),
            "dayOfWeek": day_of_week,
            "insights": insights
        })


class CsvImportView(APIView):
    """Import CSV data from Meta Business Suite export."""
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        from django.db import connection

        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded'}, status=400)

        if not file.name.endswith('.csv'):
            return Response({'error': 'File must be a CSV'}, status=400)

        try:
            # Read CSV content
            content = file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(content))

            imported = 0
            pages_seen = set()

            with connection.cursor() as cursor:
                for row in reader:
                    page_id = row.get('Page ID', '')
                    page_name = row.get('Page name', '')
                    post_id = row.get('Post ID', '')

                    if not post_id or not page_id:
                        continue

                    # Track pages
                    if page_id not in pages_seen:
                        pages_seen.add(page_id)
                        cursor.execute("""
                            INSERT OR IGNORE INTO pages (page_id, page_name, created_at, updated_at)
                            VALUES (?, ?, ?, ?)
                        """, (page_id, page_name, datetime.now().isoformat(), datetime.now().isoformat()))

                    # Parse post data
                    title = (row.get('Title', '') or '')[:200]
                    permalink = row.get('Permalink', '') or ''
                    post_type = row.get('Post type', 'TEXT') or 'TEXT'

                    # Parse datetime
                    publish_time_str = row.get('Publish time', '')
                    try:
                        publish_time = datetime.strptime(publish_time_str, "%m/%d/%Y %H:%M").isoformat() if publish_time_str else None
                    except:
                        publish_time = publish_time_str

                    # Parse metrics
                    def safe_int(val):
                        try:
                            return int(float(val)) if val else 0
                        except:
                            return 0

                    reactions = safe_int(row.get('Reactions', 0))
                    comments = safe_int(row.get('Comments', 0))
                    shares = safe_int(row.get('Shares', 0))
                    views = safe_int(row.get('Views', 0))
                    reach = safe_int(row.get('Reach', 0))

                    total_engagement = reactions + comments + shares
                    pes = (reactions * 1.0) + (comments * 2.0) + (shares * 3.0)

                    # Insert or update post
                    cursor.execute("""
                        INSERT OR REPLACE INTO posts
                        (post_id, page_id, title, permalink, post_type, publish_time,
                         reactions_total, comments_count, shares_count,
                         views_count, reach_count,
                         pes, total_engagement, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        post_id, page_id, title, permalink, post_type, publish_time,
                        reactions, comments, shares, views, reach,
                        pes, total_engagement,
                        datetime.now().isoformat()
                    ))
                    imported += 1

            # Log import
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO csv_imports (filename, import_date, rows_imported, rows_updated, status)
                    VALUES (?, ?, ?, ?, ?)
                """, (file.name, datetime.now().isoformat(), imported, 0, 'completed'))

            return Response({
                'success': True,
                'posts_imported': imported,
                'pages_count': len(pages_seen),
                'pages': list(pages_seen)
            })

        except Exception as e:
            return Response({'error': str(e)}, status=500)
