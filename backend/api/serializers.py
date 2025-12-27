"""
Django REST Framework serializers for JuanBabes Analytics API
"""

from rest_framework import serializers
from .models import Page, Post, PostMetrics, CsvImport, AudienceOverlap


class PageSerializer(serializers.ModelSerializer):
    """Serializer for Facebook pages."""
    post_count = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = [
            'page_id', 'page_name', 'page_url', 'fan_count',
            'followers_count', 'talking_about_count',
            'overall_star_rating', 'rating_count',
            'is_competitor', 'post_count'
        ]

    def get_post_count(self, obj):
        return obj.posts.count()


class PostMetricsSerializer(serializers.ModelSerializer):
    """Serializer for post metrics."""
    engagement = serializers.ReadOnlyField()

    class Meta:
        model = PostMetrics
        fields = [
            'id', 'metric_date', 'reactions', 'comments', 'shares',
            'views', 'reach', 'engagement', 'total_clicks',
            'link_clicks', 'other_clicks', 'like_count', 'love_count',
            'haha_count', 'wow_count', 'sad_count', 'angry_count', 'source'
        ]


class PostListSerializer(serializers.ModelSerializer):
    """Serializer for post list view (minimal data)."""
    page_name = serializers.CharField(source='page.page_name', read_only=True)
    reactions = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    shares = serializers.SerializerMethodField()
    views = serializers.SerializerMethodField()
    reach = serializers.SerializerMethodField()
    engagement = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'post_id', 'page_id', 'page_name', 'title', 'post_type',
            'publish_time', 'permalink', 'reactions', 'comments',
            'shares', 'views', 'reach', 'engagement'
        ]

    def get_latest_metrics(self, obj):
        if not hasattr(obj, '_latest_metrics'):
            obj._latest_metrics = obj.metrics.order_by('-metric_date').first()
        return obj._latest_metrics

    def get_reactions(self, obj):
        m = self.get_latest_metrics(obj)
        return m.reactions if m else 0

    def get_comments(self, obj):
        m = self.get_latest_metrics(obj)
        return m.comments if m else 0

    def get_shares(self, obj):
        m = self.get_latest_metrics(obj)
        return m.shares if m else 0

    def get_views(self, obj):
        m = self.get_latest_metrics(obj)
        return m.views if m else 0

    def get_reach(self, obj):
        m = self.get_latest_metrics(obj)
        return m.reach if m else 0

    def get_engagement(self, obj):
        m = self.get_latest_metrics(obj)
        return m.engagement if m else 0


class PostDetailSerializer(serializers.ModelSerializer):
    """Serializer for post detail view (full data)."""
    page_name = serializers.CharField(source='page.page_name', read_only=True)
    metrics_history = PostMetricsSerializer(source='metrics', many=True, read_only=True)
    latest_metrics = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'post_id', 'page_id', 'page_name', 'title', 'description',
            'post_type', 'publish_time', 'permalink', 'is_crosspost',
            'is_share', 'duration_sec', 'latest_metrics', 'metrics_history'
        ]

    def get_latest_metrics(self, obj):
        m = obj.metrics.order_by('-metric_date').first()
        return PostMetricsSerializer(m).data if m else None


class CsvImportSerializer(serializers.ModelSerializer):
    """Serializer for CSV import history."""
    total_processed = serializers.ReadOnlyField()

    class Meta:
        model = CsvImport
        fields = [
            'id', 'filename', 'file_path', 'import_date',
            'rows_imported', 'rows_updated', 'rows_skipped',
            'total_processed', 'date_range_start', 'date_range_end',
            'page_filter', 'status'
        ]


class AudienceOverlapSerializer(serializers.ModelSerializer):
    """Serializer for audience overlap analysis."""
    page_1_name = serializers.CharField(source='page_1.page_name', read_only=True)
    page_2_name = serializers.CharField(source='page_2.page_name', read_only=True)

    class Meta:
        model = AudienceOverlap
        fields = [
            'id', 'page_1', 'page_1_name', 'page_2', 'page_2_name',
            'analysis_date', 'shared_engagers', 'overlap_percentage',
            'content_similarity_score', 'posting_time_correlation',
            'engagement_pattern_score', 'analysis_method', 'notes'
        ]


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard summary statistics."""
    total_posts = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    total_engagement = serializers.IntegerField()
    total_views = serializers.IntegerField()
    total_reach = serializers.IntegerField()
    avg_engagement = serializers.FloatField()
    date_range_start = serializers.DateField(allow_null=True)
    date_range_end = serializers.DateField(allow_null=True)


class DailyEngagementSerializer(serializers.Serializer):
    """Serializer for daily engagement data."""
    date = serializers.DateField()
    posts = serializers.IntegerField()
    reactions = serializers.IntegerField()
    comments = serializers.IntegerField()
    shares = serializers.IntegerField()
    views = serializers.IntegerField()
    reach = serializers.IntegerField()
    engagement = serializers.IntegerField()


class PostTypeStatsSerializer(serializers.Serializer):
    """Serializer for post type distribution."""
    post_type = serializers.CharField()
    count = serializers.IntegerField()
    total_engagement = serializers.IntegerField()
    avg_engagement = serializers.FloatField()
    total_views = serializers.IntegerField()
