-- Migration: Add video watch time metrics and missing columns
-- Version: 003
-- Created: 2026-01-22

-- Add missing engagement columns to posts table (if not exists)
ALTER TABLE posts ADD COLUMN reactions_total INTEGER DEFAULT 0;
ALTER TABLE posts ADD COLUMN comments_count INTEGER DEFAULT 0;
ALTER TABLE posts ADD COLUMN shares_count INTEGER DEFAULT 0;
ALTER TABLE posts ADD COLUMN views_count INTEGER DEFAULT 0;
ALTER TABLE posts ADD COLUMN reach_count INTEGER DEFAULT 0;
ALTER TABLE posts ADD COLUMN total_engagement INTEGER DEFAULT 0;
ALTER TABLE posts ADD COLUMN pes REAL DEFAULT 0;
ALTER TABLE posts ADD COLUMN fetched_at TIMESTAMP;

-- Add video-specific columns to post_metrics
ALTER TABLE post_metrics ADD COLUMN avg_watch_time_ms INTEGER DEFAULT 0;
ALTER TABLE post_metrics ADD COLUMN video_views_3sec INTEGER DEFAULT 0;
ALTER TABLE post_metrics ADD COLUMN video_views_complete INTEGER DEFAULT 0;
ALTER TABLE post_metrics ADD COLUMN video_views_10sec INTEGER DEFAULT 0;
ALTER TABLE post_metrics ADD COLUMN video_views_30sec INTEGER DEFAULT 0;

-- Add video columns to posts table for easier access to latest values
ALTER TABLE posts ADD COLUMN avg_watch_time_ms INTEGER DEFAULT 0;
ALTER TABLE posts ADD COLUMN video_views_3sec INTEGER DEFAULT 0;
ALTER TABLE posts ADD COLUMN video_views_complete INTEGER DEFAULT 0;
ALTER TABLE posts ADD COLUMN watch_completion_rate REAL DEFAULT 0;

-- Create index for video posts (skip if syntax not supported)
-- CREATE INDEX IF NOT EXISTS idx_posts_video_type ON posts(post_type);
