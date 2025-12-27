-- Juan365 Analytics Database Schema
-- Version: 001
-- Created: 2025-12-26

-- Facebook pages being tracked
CREATE TABLE IF NOT EXISTS pages (
    page_id TEXT PRIMARY KEY,
    page_name TEXT NOT NULL,
    page_url TEXT,
    fan_count INTEGER,
    followers_count INTEGER,
    talking_about_count INTEGER,
    overall_star_rating REAL,
    rating_count INTEGER,
    is_competitor BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- All posts from tracked pages
CREATE TABLE IF NOT EXISTS posts (
    post_id TEXT PRIMARY KEY,
    page_id TEXT NOT NULL,
    title TEXT,
    description TEXT,
    post_type TEXT,  -- Photo, Video, Reel, Live, Link, Other
    publish_time TIMESTAMP,
    permalink TEXT,
    is_crosspost BOOLEAN DEFAULT FALSE,
    is_share BOOLEAN DEFAULT FALSE,
    duration_sec INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (page_id) REFERENCES pages(page_id)
);

-- Engagement metrics per post (historical tracking)
CREATE TABLE IF NOT EXISTS post_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL,
    metric_date DATE NOT NULL,
    reactions INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    views INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    total_clicks INTEGER DEFAULT 0,
    link_clicks INTEGER DEFAULT 0,
    other_clicks INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    love_count INTEGER DEFAULT 0,
    haha_count INTEGER DEFAULT 0,
    wow_count INTEGER DEFAULT 0,
    sad_count INTEGER DEFAULT 0,
    angry_count INTEGER DEFAULT 0,
    source TEXT DEFAULT 'csv',  -- 'csv', 'api', 'scraped'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(post_id),
    UNIQUE(post_id, metric_date, source)
);

-- Track CSV import history
CREATE TABLE IF NOT EXISTS csv_imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_path TEXT,
    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rows_imported INTEGER DEFAULT 0,
    rows_updated INTEGER DEFAULT 0,
    rows_skipped INTEGER DEFAULT 0,
    date_range_start DATE,
    date_range_end DATE,
    page_filter TEXT,
    status TEXT DEFAULT 'completed'  -- completed, failed, partial
);

-- Audience overlap analysis results
CREATE TABLE IF NOT EXISTS audience_overlap (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id_1 TEXT NOT NULL,
    page_id_2 TEXT NOT NULL,
    analysis_date DATE NOT NULL,
    shared_engagers INTEGER,
    overlap_percentage REAL,
    content_similarity_score REAL,
    posting_time_correlation REAL,
    engagement_pattern_score REAL,
    analysis_method TEXT,  -- 'content', 'timing', 'engagement', 'combined'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (page_id_1) REFERENCES pages(page_id),
    FOREIGN KEY (page_id_2) REFERENCES pages(page_id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_posts_page_id ON posts(page_id);
CREATE INDEX IF NOT EXISTS idx_posts_publish_time ON posts(publish_time);
CREATE INDEX IF NOT EXISTS idx_posts_post_type ON posts(post_type);
CREATE INDEX IF NOT EXISTS idx_post_metrics_post_id ON post_metrics(post_id);
CREATE INDEX IF NOT EXISTS idx_post_metrics_date ON post_metrics(metric_date);
CREATE INDEX IF NOT EXISTS idx_audience_overlap_pages ON audience_overlap(page_id_1, page_id_2);

-- View: Combined post data with latest metrics
CREATE VIEW IF NOT EXISTS enhanced_metrics AS
SELECT
    p.post_id,
    p.page_id,
    pg.page_name,
    p.title,
    p.description,
    p.post_type,
    p.publish_time,
    p.permalink,
    p.is_crosspost,
    p.is_share,
    p.duration_sec,
    pm.reactions,
    pm.comments,
    pm.shares,
    pm.views,
    pm.reach,
    (pm.reactions + pm.comments + pm.shares) as engagement,
    pm.total_clicks,
    pm.link_clicks,
    pm.other_clicks,
    pm.like_count,
    pm.love_count,
    pm.haha_count,
    pm.wow_count,
    pm.sad_count,
    pm.angry_count,
    pm.metric_date,
    pm.source
FROM posts p
LEFT JOIN pages pg ON p.page_id = pg.page_id
LEFT JOIN post_metrics pm ON p.post_id = pm.post_id
    AND pm.metric_date = (
        SELECT MAX(metric_date)
        FROM post_metrics pm2
        WHERE pm2.post_id = p.post_id
    );

-- View: Daily engagement summary
CREATE VIEW IF NOT EXISTS daily_engagement AS
SELECT
    p.page_id,
    DATE(p.publish_time) as post_date,
    COUNT(*) as post_count,
    SUM(pm.reactions) as total_reactions,
    SUM(pm.comments) as total_comments,
    SUM(pm.shares) as total_shares,
    SUM(pm.views) as total_views,
    SUM(pm.reach) as total_reach,
    SUM(pm.reactions + pm.comments + pm.shares) as total_engagement,
    AVG(pm.reactions + pm.comments + pm.shares) as avg_engagement
FROM posts p
LEFT JOIN post_metrics pm ON p.post_id = pm.post_id
    AND pm.metric_date = (
        SELECT MAX(metric_date)
        FROM post_metrics pm2
        WHERE pm2.post_id = p.post_id
    )
GROUP BY p.page_id, DATE(p.publish_time);

-- View: Post type performance summary
CREATE VIEW IF NOT EXISTS post_type_performance AS
SELECT
    p.page_id,
    p.post_type,
    COUNT(*) as post_count,
    SUM(pm.reactions) as total_reactions,
    SUM(pm.comments) as total_comments,
    SUM(pm.shares) as total_shares,
    SUM(pm.views) as total_views,
    AVG(pm.reactions + pm.comments + pm.shares) as avg_engagement,
    AVG(pm.views) as avg_views
FROM posts p
LEFT JOIN post_metrics pm ON p.post_id = pm.post_id
    AND pm.metric_date = (
        SELECT MAX(metric_date)
        FROM post_metrics pm2
        WHERE pm2.post_id = p.post_id
    )
GROUP BY p.page_id, p.post_type;
