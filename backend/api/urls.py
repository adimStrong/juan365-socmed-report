"""
URL configuration for JuanBabes Analytics API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PageViewSet, PostViewSet, CsvImportViewSet, AudienceOverlapViewSet,
    DashboardStatsView, DailyEngagementView, PostTypeStatsView, TopPostsView,
    PageComparisonView, CsvImportView, TimeSeriesView
)

router = DefaultRouter()
router.register(r'pages', PageViewSet)
router.register(r'posts', PostViewSet)
router.register(r'imports', CsvImportViewSet)
router.register(r'overlaps', AudienceOverlapViewSet)

urlpatterns = [
    # ViewSet routes
    path('', include(router.urls)),

    # Stats endpoints
    path('stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('stats/daily/', DailyEngagementView.as_view(), name='daily-engagement'),
    path('stats/post-types/', PostTypeStatsView.as_view(), name='post-type-stats'),
    path('stats/top-posts/', TopPostsView.as_view(), name='top-posts'),
    path('stats/pages/', PageComparisonView.as_view(), name='page-comparison'),
    path('stats/time-series/', TimeSeriesView.as_view(), name='time-series'),

    # Import endpoint
    path('import/csv/', CsvImportView.as_view(), name='csv-import'),
]
