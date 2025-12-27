"""
JuanBabes Project Data Models
Dataclasses for posts, pages, metrics, and analysis results
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any


@dataclass
class Page:
    """Facebook page model."""
    page_id: str
    page_name: str
    page_url: Optional[str] = None
    fan_count: Optional[int] = None
    followers_count: Optional[int] = None
    talking_about_count: Optional[int] = None
    overall_star_rating: Optional[float] = None
    rating_count: Optional[int] = None
    is_competitor: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Page':
        """Create Page from dictionary."""
        return cls(
            page_id=str(data.get('page_id', '')),
            page_name=data.get('page_name', ''),
            page_url=data.get('page_url'),
            fan_count=data.get('fan_count'),
            followers_count=data.get('followers_count'),
            talking_about_count=data.get('talking_about_count'),
            overall_star_rating=data.get('overall_star_rating'),
            rating_count=data.get('rating_count'),
            is_competitor=bool(data.get('is_competitor', False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'page_id': self.page_id,
            'page_name': self.page_name,
            'page_url': self.page_url,
            'fan_count': self.fan_count,
            'followers_count': self.followers_count,
            'talking_about_count': self.talking_about_count,
            'overall_star_rating': self.overall_star_rating,
            'rating_count': self.rating_count,
            'is_competitor': self.is_competitor,
        }


@dataclass
class Post:
    """Facebook post model."""
    post_id: str
    page_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    post_type: Optional[str] = None  # Photo, Video, Reel, Live, Link, Other
    publish_time: Optional[datetime] = None
    permalink: Optional[str] = None
    is_crosspost: bool = False
    is_share: bool = False
    duration_sec: Optional[int] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Post':
        """Create Post from dictionary."""
        publish_time = data.get('publish_time')
        if isinstance(publish_time, str):
            try:
                publish_time = datetime.fromisoformat(publish_time.replace('Z', '+00:00'))
            except ValueError:
                publish_time = None

        return cls(
            post_id=str(data.get('post_id', '')),
            page_id=str(data.get('page_id', '')),
            title=data.get('title'),
            description=data.get('description'),
            post_type=data.get('post_type'),
            publish_time=publish_time,
            permalink=data.get('permalink'),
            is_crosspost=bool(data.get('is_crosspost', False)),
            is_share=bool(data.get('is_share', False)),
            duration_sec=data.get('duration_sec'),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'post_id': self.post_id,
            'page_id': self.page_id,
            'title': self.title,
            'description': self.description,
            'post_type': self.post_type,
            'publish_time': self.publish_time.isoformat() if self.publish_time else None,
            'permalink': self.permalink,
            'is_crosspost': self.is_crosspost,
            'is_share': self.is_share,
            'duration_sec': self.duration_sec,
        }


@dataclass
class PostMetrics:
    """Engagement metrics for a post."""
    post_id: str
    metric_date: date
    reactions: int = 0
    comments: int = 0
    shares: int = 0
    views: int = 0
    reach: int = 0
    total_clicks: int = 0
    link_clicks: int = 0
    other_clicks: int = 0
    like_count: int = 0
    love_count: int = 0
    haha_count: int = 0
    wow_count: int = 0
    sad_count: int = 0
    angry_count: int = 0
    source: str = 'csv'  # csv, api, scraped

    @property
    def engagement(self) -> int:
        """Total engagement (reactions + comments + shares)."""
        return self.reactions + self.comments + self.shares

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PostMetrics':
        """Create PostMetrics from dictionary."""
        metric_date = data.get('metric_date')
        if isinstance(metric_date, str):
            metric_date = date.fromisoformat(metric_date)
        elif metric_date is None:
            metric_date = date.today()

        return cls(
            post_id=str(data.get('post_id', '')),
            metric_date=metric_date,
            reactions=int(data.get('reactions', 0) or 0),
            comments=int(data.get('comments', 0) or 0),
            shares=int(data.get('shares', 0) or 0),
            views=int(data.get('views', 0) or 0),
            reach=int(data.get('reach', 0) or 0),
            total_clicks=int(data.get('total_clicks', 0) or 0),
            link_clicks=int(data.get('link_clicks', 0) or 0),
            other_clicks=int(data.get('other_clicks', 0) or 0),
            like_count=int(data.get('like_count', 0) or 0),
            love_count=int(data.get('love_count', 0) or 0),
            haha_count=int(data.get('haha_count', 0) or 0),
            wow_count=int(data.get('wow_count', 0) or 0),
            sad_count=int(data.get('sad_count', 0) or 0),
            angry_count=int(data.get('angry_count', 0) or 0),
            source=data.get('source', 'csv'),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'post_id': self.post_id,
            'metric_date': self.metric_date.isoformat(),
            'reactions': self.reactions,
            'comments': self.comments,
            'shares': self.shares,
            'views': self.views,
            'reach': self.reach,
            'engagement': self.engagement,
            'total_clicks': self.total_clicks,
            'link_clicks': self.link_clicks,
            'other_clicks': self.other_clicks,
            'like_count': self.like_count,
            'love_count': self.love_count,
            'haha_count': self.haha_count,
            'wow_count': self.wow_count,
            'sad_count': self.sad_count,
            'angry_count': self.angry_count,
            'source': self.source,
        }


@dataclass
class EnhancedPost:
    """Post with page info and latest metrics combined."""
    post_id: str
    page_id: str
    page_name: str
    title: Optional[str] = None
    description: Optional[str] = None
    post_type: Optional[str] = None
    publish_time: Optional[datetime] = None
    permalink: Optional[str] = None
    reactions: int = 0
    comments: int = 0
    shares: int = 0
    views: int = 0
    reach: int = 0
    engagement: int = 0
    metric_date: Optional[date] = None
    source: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnhancedPost':
        """Create EnhancedPost from dictionary."""
        publish_time = data.get('publish_time')
        if isinstance(publish_time, str):
            try:
                publish_time = datetime.fromisoformat(publish_time.replace('Z', '+00:00'))
            except ValueError:
                publish_time = None

        metric_date = data.get('metric_date')
        if isinstance(metric_date, str):
            metric_date = date.fromisoformat(metric_date)

        return cls(
            post_id=str(data.get('post_id', '')),
            page_id=str(data.get('page_id', '')),
            page_name=data.get('page_name', ''),
            title=data.get('title'),
            description=data.get('description'),
            post_type=data.get('post_type'),
            publish_time=publish_time,
            permalink=data.get('permalink'),
            reactions=int(data.get('reactions', 0) or 0),
            comments=int(data.get('comments', 0) or 0),
            shares=int(data.get('shares', 0) or 0),
            views=int(data.get('views', 0) or 0),
            reach=int(data.get('reach', 0) or 0),
            engagement=int(data.get('engagement', 0) or 0),
            metric_date=metric_date,
            source=data.get('source'),
        )


@dataclass
class OverlapResult:
    """Result of audience overlap analysis between two pages."""
    page_id_1: str
    page_id_2: str
    analysis_date: date
    content_similarity: float = 0.0  # 0-100%
    timing_correlation: float = 0.0  # -1 to 1
    engagement_pattern_score: float = 0.0  # 0-100
    estimated_overlap_percentage: float = 0.0  # 0-100%
    analysis_method: str = 'combined'
    recommendations: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'page_id_1': self.page_id_1,
            'page_id_2': self.page_id_2,
            'analysis_date': self.analysis_date.isoformat(),
            'content_similarity': self.content_similarity,
            'timing_correlation': self.timing_correlation,
            'engagement_pattern_score': self.engagement_pattern_score,
            'estimated_overlap_percentage': self.estimated_overlap_percentage,
            'analysis_method': self.analysis_method,
            'recommendations': self.recommendations,
            'notes': self.notes,
        }


@dataclass
class ImportResult:
    """Result of a CSV import operation."""
    filename: str
    file_path: Optional[str] = None
    rows_imported: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    page_filter: Optional[str] = None
    status: str = 'completed'  # completed, failed, partial
    error_message: Optional[str] = None
    import_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'filename': self.filename,
            'file_path': self.file_path,
            'rows_imported': self.rows_imported,
            'rows_updated': self.rows_updated,
            'rows_skipped': self.rows_skipped,
            'date_range_start': self.date_range_start.isoformat() if self.date_range_start else None,
            'date_range_end': self.date_range_end.isoformat() if self.date_range_end else None,
            'page_filter': self.page_filter,
            'status': self.status,
            'error_message': self.error_message,
        }

    @property
    def total_processed(self) -> int:
        """Total rows processed."""
        return self.rows_imported + self.rows_updated + self.rows_skipped

    def __str__(self) -> str:
        return (
            f"Import '{self.filename}': "
            f"{self.rows_imported} imported, "
            f"{self.rows_updated} updated, "
            f"{self.rows_skipped} skipped "
            f"[{self.status}]"
        )
