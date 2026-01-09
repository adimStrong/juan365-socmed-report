import axios from 'axios';

// Use static data in production, API in development
const IS_PRODUCTION = false; // Set to true for Vercel deployment
const API_URL = 'http://localhost:8002/api/v1';

let staticData = null;

async function loadStaticData() {
  if (!staticData) {
    // Use cache-busting for fresh data
    const response = await fetch('/data/analytics.json?t=' + Date.now());
    staticData = await response.json();
  }
  return staticData;
}

// Normalize date to YYYY-MM-DD format
function normalizeDate(dateStr) {
  if (!dateStr) return null;
  // If already YYYY-MM-DD format
  if (dateStr.length >= 10 && dateStr[4] === '-') {
    return dateStr.slice(0, 10);
  }
  // If MM/DD/YYYY format
  if (dateStr.includes('/')) {
    const parts = dateStr.split('/');
    if (parts.length >= 3) {
      const [month, day, year] = parts;
      return `${year.slice(0, 4)}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
    }
  }
  return dateStr.slice(0, 10);
}

// Date filter helper
function filterByDateRange(data, startDate, endDate, dateField = 'date') {
  if (!startDate && !endDate) return data;
  return data.filter(item => {
    const itemDate = item[dateField];
    if (!itemDate) return true;
    if (startDate && itemDate < startDate) return false;
    if (endDate && itemDate > endDate) return false;
    return true;
  });
}

// Merge Videos and Reels into a single category
function mergeVideoReels(postTypes) {
  if (!Array.isArray(postTypes)) return postTypes;

  const videoIdx = postTypes.findIndex(p => p.post_type === 'Videos');
  const reelIdx = postTypes.findIndex(p => p.post_type === 'Reels');

  // If both don't exist, return as-is
  if (videoIdx === -1 && reelIdx === -1) return postTypes;

  const video = videoIdx !== -1 ? postTypes[videoIdx] : { count: 0, reactions: 0, comments: 0, shares: 0, total_engagement: 0 };
  const reel = reelIdx !== -1 ? postTypes[reelIdx] : { count: 0, reactions: 0, comments: 0, shares: 0, total_engagement: 0 };

  const combined = {
    post_type: 'Videos/Reels',
    count: (video.count || 0) + (reel.count || 0),
    reactions: (video.reactions || 0) + (reel.reactions || 0),
    comments: (video.comments || 0) + (reel.comments || 0),
    shares: (video.shares || 0) + (reel.shares || 0),
    total_engagement: (video.total_engagement || 0) + (reel.total_engagement || 0),
  };
  combined.avg_engagement = combined.count > 0 ? Math.round(combined.total_engagement / combined.count) : 0;

  return postTypes
    .filter(p => p.post_type !== 'Videos' && p.post_type !== 'Reels')
    .concat(combined);
}

// Normalize post_type for individual posts
function normalizePostType(post) {
  if (post.post_type === 'Videos' || post.post_type === 'Reels') {
    return { ...post, post_type: 'Videos/Reels' };
  }
  return post;
}

// Normalize post field names for display
function normalizePostFields(p) {
  return {
    ...p,
    comments: p.comments ?? p.comments_count ?? 0,
    reactions: p.reactions ?? p.reactions_total ?? 0,
    shares: p.shares ?? p.shares_count ?? 0,
    engagement: p.engagement ?? p.total_engagement ?? 0,
    views: p.views ?? p.views_count ?? 0,
    reach: p.reach ?? p.reach_count ?? 0,
  };
}

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getStats = async (pageId = null, dateRange = {}) => {
  if (IS_PRODUCTION) {
    const data = await loadStaticData();
    const { startDate, endDate } = dateRange;

    // If date range specified, calculate stats from filtered daily data
    if (startDate || endDate) {
      let dailyData;
      if (pageId && data.daily.byPage && data.daily.byPage[pageId]) {
        dailyData = data.daily.byPage[pageId];
      } else {
        dailyData = data.daily.all || data.daily;
      }
      const filtered = filterByDateRange(dailyData, startDate, endDate);

      // Calculate totals from filtered daily data
      const totals = filtered.reduce((acc, day) => ({
        total_posts: acc.total_posts + (day.posts || 0),
        total_views: acc.total_views + (day.views || 0),
        total_reach: acc.total_reach + (day.reach || 0),
        total_engagement: acc.total_engagement + (day.engagement || 0),
        total_reactions: acc.total_reactions + (day.reactions || 0),
        total_comments: acc.total_comments + (day.comments || 0),
        total_shares: acc.total_shares + (day.shares || 0),
      }), { total_posts: 0, total_views: 0, total_reach: 0, total_engagement: 0, total_reactions: 0, total_comments: 0, total_shares: 0 });

      const postCount = totals.total_posts || 1;
      return {
        ...totals,
        avg_views: Math.round(totals.total_views / postCount),
        avg_reach: Math.round(totals.total_reach / postCount),
        avg_engagement: Math.round(totals.total_engagement / postCount),
        total_pages: data.pages?.length || 0,
        all_pages: data.pages?.length || 0,
        date_range_start: startDate || filtered[0]?.date,
        date_range_end: endDate || filtered[filtered.length - 1]?.date,
      };
    }

    // Support per-page stats filtering
    if (pageId && data.stats.byPage && data.stats.byPage[pageId]) {
      return data.stats.byPage[pageId];
    }
    return data.stats.all || data.stats;
  }
  const params = pageId ? `?page=${pageId}` : '';
  return api.get(`/stats/${params}`).then(res => res.data);
};

export const getDailyEngagement = async (days = 30, pageId = null, dateRange = {}) => {
  if (IS_PRODUCTION) {
    const data = await loadStaticData();
    const { startDate, endDate } = dateRange;

    // Support per-page daily filtering
    let dailyData;
    if (pageId && data.daily.byPage && data.daily.byPage[pageId]) {
      dailyData = data.daily.byPage[pageId];
    } else {
      dailyData = data.daily.all || data.daily;
    }

    // If date range specified, use it
    if (startDate || endDate) {
      return filterByDateRange(dailyData, startDate, endDate);
    }

    // Return all data (no T+2 filter)
    return dailyData.slice(-days);
  }
  const params = new URLSearchParams({ days });
  if (pageId) params.append('page', pageId);
  return api.get(`/stats/daily/?${params}`).then(res => res.data);
};

export const getPostTypeStats = async (pageId = null) => {
  if (IS_PRODUCTION) {
    const data = await loadStaticData();
    // Support per-page post type filtering
    let postTypes;
    if (pageId && data.postTypes.byPage && data.postTypes.byPage[pageId]) {
      postTypes = data.postTypes.byPage[pageId];
    } else {
      postTypes = data.postTypes.all || data.postTypes;
    }
    // Merge Videos and Reels into single category
    return mergeVideoReels(postTypes);
  }
  const params = pageId ? `?page=${pageId}` : '';
  return api.get(`/stats/post-types/${params}`).then(res => res.data);
};

export const getTopPosts = async (limit = 10, metric = 'engagement', pageId = null) => {
  if (IS_PRODUCTION) {
    const data = await loadStaticData();
    // Support per-page top posts filtering
    let posts;
    if (pageId && data.topPosts.byPage && data.topPosts.byPage[pageId]) {
      posts = data.topPosts.byPage[pageId];
    } else {
      posts = data.topPosts.all || data.topPosts;
    }
    // Normalize post_type and field names
    return posts.slice(0, limit).map(p => normalizePostFields(normalizePostType(p)));
  }
  const params = new URLSearchParams({ limit, metric });
  if (pageId) params.append('page', pageId);
  // API response - normalize field names
  return api.get(`/stats/top-posts/?${params}`).then(res =>
    res.data.map(p => normalizePostFields(normalizePostType(p)))
  );
};

export const getPosts = async (params = {}, dateRange = {}) => {
  if (IS_PRODUCTION) {
    const data = await loadStaticData();
    // Normalize post_type and field names
    let posts = (data.posts || []).map(p => normalizePostFields(normalizePostType(p)));

    // Apply date range filter
    const { startDate, endDate } = dateRange;
    if (startDate || endDate) {
      posts = posts.filter(p => {
        const postDate = normalizeDate(p.publish_time);
        if (!postDate) return true;
        if (startDate && postDate < startDate) return false;
        if (endDate && postDate > endDate) return false;
        return true;
      });
    }

    // Apply filters
    if (params.post_type) {
      posts = posts.filter(p => p.post_type === params.post_type);
    }
    if (params.page_id) {
      posts = posts.filter(p => p.page_id === params.page_id);
    }
    if (params.search) {
      const search = params.search.toLowerCase();
      posts = posts.filter(p =>
        (p.title || '').toLowerCase().includes(search) ||
        (p.page_name || '').toLowerCase().includes(search)
      );
    }

    // Pagination
    const page = parseInt(params.page || 1);
    const pageSize = 20;
    const start = (page - 1) * pageSize;
    const end = start + pageSize;
    const paginatedPosts = posts.slice(start, end);

    return {
      results: paginatedPosts,
      count: posts.length,
      next: end < posts.length ? page + 1 : null,
      previous: page > 1 ? page - 1 : null,
    };
  }
  const searchParams = new URLSearchParams(params);
  // API response - normalize field names
  return api.get(`/posts/?${searchParams}`).then(res => ({
    ...res.data,
    results: (res.data.posts || res.data.results || []).map(p => normalizePostFields(normalizePostType(p))),
  }));
};

export const getPost = (id) => api.get(`/posts/${id}/`).then(res => res.data);

// Normalize page fields for display
function normalizePageFields(page) {
  return {
    ...page,
    total_reactions: page.total_reactions ?? page.reactions ?? 0,
    total_comments: page.total_comments ?? page.comments ?? 0,
    total_shares: page.total_shares ?? page.shares ?? 0,
    total_views: page.total_views ?? page.views ?? 0,
    total_reach: page.total_reach ?? page.reach ?? 0,
  };
}

export const getPages = async (dateRange = {}) => {
  if (IS_PRODUCTION) {
    const data = await loadStaticData();
    const { startDate, endDate } = dateRange;

    // If no date filter, return pages as-is
    if (!startDate && !endDate) {
      return data.pages;
    }

    // Filter posts by date and recalculate page stats
    let posts = data.posts || [];
    posts = posts.filter(p => {
      const postDate = normalizeDate(p.publish_time);
      if (!postDate) return true;
      if (startDate && postDate < startDate) return false;
      if (endDate && postDate > endDate) return false;
      return true;
    });

    // Aggregate by page
    const pageMap = {};
    posts.forEach(post => {
      const pageId = post.page_id;
      if (!pageMap[pageId]) {
        // Get base page info from data.pages
        const basePage = (data.pages || []).find(pg => pg.page_id === pageId) || {};
        pageMap[pageId] = {
          page_id: pageId,
          page_name: post.page_name || basePage.page_name,
          fan_count: basePage.fan_count || 0,
          followers_count: basePage.followers_count || 0,
          post_count: 0,
          total_views: 0,
          total_reach: 0,
          total_reactions: 0,
          total_comments: 0,
          total_shares: 0,
          total_engagement: 0,
        };
      }
      pageMap[pageId].post_count++;
      pageMap[pageId].total_views += post.views || post.views_count || 0;
      pageMap[pageId].total_reach += post.reach || post.reach_count || 0;
      pageMap[pageId].total_reactions += post.reactions || post.reactions_total || 0;
      pageMap[pageId].total_comments += post.comments || post.comments_count || 0;
      pageMap[pageId].total_shares += post.shares || post.shares_count || 0;
      pageMap[pageId].total_engagement += (post.reactions || post.reactions_total || 0) +
                                           (post.comments || post.comments_count || 0) +
                                           (post.shares || post.shares_count || 0);
    });

    return Object.values(pageMap).sort((a, b) => b.total_engagement - a.total_engagement);
  }
  // API response - normalize field names
  return api.get('/pages/').then(res => res.data.map(normalizePageFields));
};

export const getImports = () => api.get('/imports/').then(res => res.data);

export const getOverlaps = async () => {
  if (IS_PRODUCTION) {
    const data = await loadStaticData();
    return data.overlaps || [];
  }
  return api.get('/overlaps/').then(res => res.data);
};

export const getDailyByPage = async (days = 60) => {
  if (IS_PRODUCTION) {
    const data = await loadStaticData();
    const pages = data.pages || [];
    const byPage = data.daily.byPage || {};
    const allDaily = data.daily.all || [];

    // Create a map of all dates from the last N days (no T+2 filter)
    const dateMap = {};
    allDaily.slice(-days).forEach(entry => {
      dateMap[entry.date] = { date: entry.date };
    });

    // Add each page's posts to the date map
    pages.forEach(page => {
      const pageDaily = byPage[page.page_id] || [];
      pageDaily.forEach(entry => {
        if (dateMap[entry.date]) {
          // Use page name as-is or shorten if needed
          const shortName = page.page_name;
          dateMap[entry.date][shortName] = entry.posts;
        }
      });
    });

    // Convert to array and sort by date
    const result = Object.values(dateMap).sort((a, b) => a.date.localeCompare(b.date));

    // Get page names for the chart
    const pageNames = pages.map(p => p.page_name);

    return { data: result, pageNames };
  }

  // Non-production: use dedicated API endpoint
  try {
    const response = await api.get(`/stats/daily-by-page?days=${days}`);
    return response.data || { data: [], pageNames: [] };
  } catch (err) {
    console.error('getDailyByPage API error:', err);
    return { data: [], pageNames: [] };
  }
};

export const getTimeSeries = async () => {
  if (IS_PRODUCTION) {
    const data = await loadStaticData();
    return data.timeSeries || {
      monthly: [],
      weekly: [],
      dayOfWeek: [],
      pageRankings: [],
      postTypePerf: [],
      insights: []
    };
  }
  // For dev, calculate from daily data (simplified)
  return api.get('/stats/time-series/').then(res => res.data);
};

export const getCommentAnalysis = async () => {
  if (IS_PRODUCTION) {
    const data = await loadStaticData();
    return data.commentAnalysis || {
      summary: {},
      byPage: [],
      effectivity: {},
      topSelfCommented: []
    };
  }
  return api.get('/stats/comment-analysis/').then(res => res.data);
};

export const getPageComparison = async (dateRange = {}) => {
  if (IS_PRODUCTION) {
    const data = await loadStaticData();
    const { startDate, endDate } = dateRange;

    // If no date filter, return as-is
    if (!startDate && !endDate) {
      return data.pageComparison || {
        pages: [],
        postTypesByPage: {},
        dominantTypes: {}
      };
    }

    // Filter posts by date and recalculate comparison
    let posts = data.posts || [];
    posts = posts.filter(p => {
      const postDate = normalizeDate(p.publish_time);
      if (!postDate) return true;
      if (startDate && postDate < startDate) return false;
      if (endDate && postDate > endDate) return false;
      return true;
    });

    // Aggregate by page
    const pageMap = {};
    const postTypesByPage = {};

    posts.forEach(post => {
      const pageId = post.page_id;
      const postType = post.post_type || 'Unknown';

      if (!pageMap[pageId]) {
        // Get base page info for fan_count
        const basePage = (data.pages || []).find(pg => pg.page_id === pageId) || {};
        pageMap[pageId] = {
          page_id: pageId,
          page_name: post.page_name,
          post_count: 0,
          total_engagement: 0,
          fan_count: basePage.fan_count || 0,
        };
        postTypesByPage[pageId] = {};
      }

      pageMap[pageId].post_count++;
      pageMap[pageId].total_engagement += (post.reactions || post.reactions_total || 0) +
                                           (post.comments || post.comments_count || 0) +
                                           (post.shares || post.shares_count || 0);

      if (!postTypesByPage[pageId][postType]) {
        postTypesByPage[pageId][postType] = 0;
      }
      postTypesByPage[pageId][postType]++;
    });

    // Calculate dominant types
    const dominantTypes = {};
    Object.keys(postTypesByPage).forEach(pageId => {
      const types = postTypesByPage[pageId];
      const dominant = Object.entries(types).sort((a, b) => b[1] - a[1])[0];
      dominantTypes[pageId] = dominant ? dominant[0] : 'Unknown';
    });

    return {
      pages: Object.values(pageMap).sort((a, b) => b.total_engagement - a.total_engagement),
      postTypesByPage,
      dominantTypes
    };
  }
  return api.get('/stats/page-comparison/').then(res => res.data);
};

export const getDateBoundaries = async () => {
  if (IS_PRODUCTION) {
    const data = await loadStaticData();
    const posts = data.posts || [];
    if (posts.length === 0) return { minDate: null, maxDate: null };

    const dates = posts
      .map(p => normalizeDate(p.publish_time))
      .filter(d => d)
      .sort();

    return {
      minDate: dates[0],
      maxDate: dates[dates.length - 1]
    };
  }
  // For localhost API, return null (no boundaries)
  return { minDate: null, maxDate: null };
};

export default api;
