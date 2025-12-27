"""
Django models for JuanBabes Analytics
These models map to the existing SQLite database schema
"""

from django.db import models


class Page(models.Model):
    """Facebook page being tracked."""
    page_id = models.CharField(max_length=100, primary_key=True)
    page_name = models.CharField(max_length=255)
    page_url = models.URLField(blank=True, null=True)
    fan_count = models.IntegerField(null=True, blank=True)
    followers_count = models.IntegerField(null=True, blank=True)
    talking_about_count = models.IntegerField(null=True, blank=True)
    overall_star_rating = models.FloatField(null=True, blank=True)
    rating_count = models.IntegerField(null=True, blank=True)
    is_competitor = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pages'
        managed = False

    def __str__(self):
        return self.page_name


class Post(models.Model):
    """Facebook post from a tracked page."""
    post_id = models.CharField(max_length=100, primary_key=True)
    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        db_column='page_id',
        related_name='posts'
    )
    title = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    post_type = models.CharField(max_length=50, blank=True, null=True)
    publish_time = models.DateTimeField(null=True, blank=True)
    permalink = models.URLField(blank=True, null=True)
    is_crosspost = models.BooleanField(default=False)
    is_share = models.BooleanField(default=False)
    duration_sec = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'posts'
        managed = False
        ordering = ['-publish_time']

    def __str__(self):
        return f"{self.post_type}: {self.title or self.post_id[:20]}"

    @property
    def latest_metrics(self):
        """Get the most recent metrics for this post."""
        return self.metrics.order_by('-metric_date').first()


class PostMetrics(models.Model):
    """Engagement metrics for a post (historical tracking)."""
    id = models.AutoField(primary_key=True)
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        db_column='post_id',
        related_name='metrics'
    )
    metric_date = models.DateField()
    reactions = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    views = models.IntegerField(default=0)
    reach = models.IntegerField(default=0)
    total_clicks = models.IntegerField(default=0)
    link_clicks = models.IntegerField(default=0)
    other_clicks = models.IntegerField(default=0)
    like_count = models.IntegerField(default=0)
    love_count = models.IntegerField(default=0)
    haha_count = models.IntegerField(default=0)
    wow_count = models.IntegerField(default=0)
    sad_count = models.IntegerField(default=0)
    angry_count = models.IntegerField(default=0)
    source = models.CharField(max_length=20, default='csv')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'post_metrics'
        managed = False
        unique_together = ['post', 'metric_date', 'source']

    @property
    def engagement(self):
        """Total engagement (reactions + comments + shares)."""
        return self.reactions + self.comments + self.shares


class CsvImport(models.Model):
    """Track CSV import history."""
    id = models.AutoField(primary_key=True)
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500, blank=True, null=True)
    import_date = models.DateTimeField(auto_now_add=True)
    rows_imported = models.IntegerField(default=0)
    rows_updated = models.IntegerField(default=0)
    rows_skipped = models.IntegerField(default=0)
    date_range_start = models.DateField(null=True, blank=True)
    date_range_end = models.DateField(null=True, blank=True)
    page_filter = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, default='completed')

    class Meta:
        db_table = 'csv_imports'
        managed = False
        ordering = ['-import_date']

    def __str__(self):
        return f"{self.filename} ({self.import_date})"

    @property
    def total_processed(self):
        return self.rows_imported + self.rows_updated + self.rows_skipped


class AudienceOverlap(models.Model):
    """Audience overlap analysis results."""
    id = models.AutoField(primary_key=True)
    page_1 = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        db_column='page_id_1',
        related_name='overlaps_as_page1'
    )
    page_2 = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        db_column='page_id_2',
        related_name='overlaps_as_page2'
    )
    analysis_date = models.DateField()
    shared_engagers = models.IntegerField(null=True, blank=True)
    overlap_percentage = models.FloatField(null=True, blank=True)
    content_similarity_score = models.FloatField(null=True, blank=True)
    posting_time_correlation = models.FloatField(null=True, blank=True)
    engagement_pattern_score = models.FloatField(null=True, blank=True)
    analysis_method = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audience_overlap'
        managed = False
        ordering = ['-analysis_date']

    def __str__(self):
        return f"Overlap: {self.page_1} vs {self.page_2}"
