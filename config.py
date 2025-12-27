"""
Juan365 Socmed Report Configuration
CSV Import & Analytics for Facebook Pages
"""

from pathlib import Path

# Project directories
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
EXPORTS_DIR = PROJECT_ROOT / "exports"
REPORTS_DIR = PROJECT_ROOT / "reports"
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"

# Database
DB_PATH = DATA_DIR / "juan365_socmed.db"

# CSV Import settings
CSV_DOWNLOADS_DIR = Path.home() / "Downloads"
DEFAULT_PAGE_FILTER = None  # Set to page name to filter imports

# Column mapping for Meta Business Suite CSV exports
COLUMN_MAPPING = {
    'Post ID': 'post_id',
    'Page ID': 'page_id',
    'Page name': 'page_name',
    'Title': 'title',
    'Description': 'description',
    'Post type': 'post_type',
    'Publish time': 'publish_time',
    'Permalink': 'permalink',
    'Reactions': 'reactions',
    'Comments': 'comments',
    'Shares': 'shares',
    'Views': 'views',
    'Reach': 'reach',
    'Total clicks': 'total_clicks',
    'Link clicks': 'link_clicks',
    'Other clicks': 'other_clicks',
    'Duration (sec)': 'duration_sec',
    'Is crosspost': 'is_crosspost',
    'Is share': 'is_share',
}

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
