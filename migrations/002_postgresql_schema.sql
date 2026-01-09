-- Juan365 Analytics PostgreSQL Schema
-- Version: 002
-- For Railway PostgreSQL deployment

-- Facebook pages being tracked
CREATE TABLE IF NOT EXISTS pages (
    page_id VARCHAR(50) PRIMARY KEY,
    page_name VARCHAR(255) NOT NULL,
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
    post_id VARCHAR(100) PRIMARY KEY,
    page_id VARCHAR(50) NOT NULL REFERENCES pages(page_id),
    title TEXT,
    description TEXT,
    post_type VARCHAR(50),
    publish_time TIMESTAMP,
    permalink TEXT,
    is_crosspost BOOLEAN DEFAULT FALSE,
    is_share BOOLEAN DEFAULT FALSE,
    duration_sec INTEGER,
    reactions_total INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    views_count INTEGER DEFAULT 0,
    reach_count INTEGER DEFAULT 0,
    total_engagement INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Engagement metrics per post (historical tracking)
CREATE TABLE IF NOT EXISTS post_metrics (
    id SERIAL PRIMARY KEY,
    post_id VARCHAR(100) NOT NULL REFERENCES posts(post_id),
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
    source VARCHAR(20) DEFAULT 'csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(post_id, metric_date, source)
);

-- Track CSV import history
CREATE TABLE IF NOT EXISTS csv_imports (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT,
    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rows_imported INTEGER DEFAULT 0,
    rows_updated INTEGER DEFAULT 0,
    rows_skipped INTEGER DEFAULT 0,
    date_range_start DATE,
    date_range_end DATE,
    page_filter VARCHAR(255),
    status VARCHAR(50) DEFAULT 'completed'
);

-- Audience overlap analysis results
CREATE TABLE IF NOT EXISTS audience_overlap (
    id SERIAL PRIMARY KEY,
    page_id_1 VARCHAR(50) NOT NULL REFERENCES pages(page_id),
    page_id_2 VARCHAR(50) NOT NULL REFERENCES pages(page_id),
    analysis_date DATE NOT NULL,
    shared_engagers INTEGER,
    overlap_percentage REAL,
    content_similarity_score REAL,
    posting_time_correlation REAL,
    engagement_pattern_score REAL,
    analysis_method VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_posts_page_id ON posts(page_id);
CREATE INDEX IF NOT EXISTS idx_posts_publish_time ON posts(publish_time);
CREATE INDEX IF NOT EXISTS idx_posts_post_type ON posts(post_type);
CREATE INDEX IF NOT EXISTS idx_post_metrics_post_id ON post_metrics(post_id);
CREATE INDEX IF NOT EXISTS idx_post_metrics_date ON post_metrics(metric_date);
CREATE INDEX IF NOT EXISTS idx_audience_overlap_pages ON audience_overlap(page_id_1, page_id_2);

-- View: Combined post data with latest metrics
CREATE OR REPLACE VIEW enhanced_metrics AS
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
    COALESCE(pm.reactions, 0) as reactions,
    COALESCE(pm.comments, 0) as comments,
    COALESCE(pm.shares, 0) as shares,
    COALESCE(pm.views, 0) as views,
    COALESCE(pm.reach, 0) as reach,
    COALESCE(pm.reactions + pm.comments + pm.shares, 0) as engagement,
    COALESCE(pm.total_clicks, 0) as total_clicks,
    COALESCE(pm.link_clicks, 0) as link_clicks,
    COALESCE(pm.other_clicks, 0) as other_clicks,
    COALESCE(pm.like_count, 0) as like_count,
    COALESCE(pm.love_count, 0) as love_count,
    COALESCE(pm.haha_count, 0) as haha_count,
    COALESCE(pm.wow_count, 0) as wow_count,
    COALESCE(pm.sad_count, 0) as sad_count,
    COALESCE(pm.angry_count, 0) as angry_count,
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
CREATE OR REPLACE VIEW daily_engagement AS
SELECT
    p.page_id,
    DATE(p.publish_time) as post_date,
    COUNT(*) as post_count,
    COALESCE(SUM(pm.reactions), 0) as total_reactions,
    COALESCE(SUM(pm.comments), 0) as total_comments,
    COALESCE(SUM(pm.shares), 0) as total_shares,
    COALESCE(SUM(pm.views), 0) as total_views,
    COALESCE(SUM(pm.reach), 0) as total_reach,
    COALESCE(SUM(pm.reactions + pm.comments + pm.shares), 0) as total_engagement,
    COALESCE(AVG(pm.reactions + pm.comments + pm.shares), 0) as avg_engagement
FROM posts p
LEFT JOIN post_metrics pm ON p.post_id = pm.post_id
    AND pm.metric_date = (
        SELECT MAX(metric_date)
        FROM post_metrics pm2
        WHERE pm2.post_id = p.post_id
    )
GROUP BY p.page_id, DATE(p.publish_time);

-- View: Post type performance summary
CREATE OR REPLACE VIEW post_type_performance AS
SELECT
    p.page_id,
    p.post_type,
    COUNT(*) as post_count,
    COALESCE(SUM(pm.reactions), 0) as total_reactions,
    COALESCE(SUM(pm.comments), 0) as total_comments,
    COALESCE(SUM(pm.shares), 0) as total_shares,
    COALESCE(SUM(pm.views), 0) as total_views,
    COALESCE(AVG(pm.reactions + pm.comments + pm.shares), 0) as avg_engagement,
    COALESCE(AVG(pm.views), 0) as avg_views
FROM posts p
LEFT JOIN post_metrics pm ON p.post_id = pm.post_id
    AND pm.metric_date = (
        SELECT MAX(metric_date)
        FROM post_metrics pm2
        WHERE pm2.post_id = p.post_id
    )
GROUP BY p.page_id, p.post_type;
