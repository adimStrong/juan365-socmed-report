import axios from 'axios';

// Always use static data (no backend API)
const IS_PRODUCTION = true;
const API_URL = 'http://localhost:8001/api';

let staticData = null;

async function loadStaticData() {
  if (!staticData) {
    const response = await fetch('/data/analytics.json');
    staticData = await response.json();
  }
  return staticData;
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
    if (pageId && data.postTypes.byPage && data.postTypes.byPage[pageId]) {
      return data.postTypes.byPage[pageId];
    }
    return data.postTypes.all || data.postTypes;
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
    return posts.slice(0, limit);
  }
  const params = new URLSearchParams({ limit, metric });
  if (pageId) params.append('page', pageId);
  return api.get(`/stats/top-posts/?${params}`).then(res => res.data);
};

export const getPosts = async (params = {}) => {
  if (IS_PRODUCTION) {
    const data = await loadStaticData();
    let posts = data.posts || [];

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
  return api.get(`/posts/?${searchParams}`).then(res => res.data);
};

export const getPost = (id) => api.get(`/posts/${id}/`).then(res => res.data);

export const getPages = async () => {
  if (IS_PRODUCTION) {
    const data = await loadStaticData();
    return data.pages;
  }
  return api.get('/pages/').then(res => res.data);
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
        // Use short page name (e.g., "Ashley" instead of "Juana Babe Ashley")
        const shortName = page.page_name.replace('Juana Babe ', '');
        dateMap[entry.date][shortName] = entry.posts;
      }
    });
  });

  // Convert to array and sort by date
  const result = Object.values(dateMap).sort((a, b) => a.date.localeCompare(b.date));

  // Get page names for the chart
  const pageNames = pages.map(p => p.page_name.replace('Juana Babe ', ''));

  return { data: result, pageNames };
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

export const getPageComparison = async () => {
  if (IS_PRODUCTION) {
    const data = await loadStaticData();
    return data.pageComparison || {
      pages: [],
      postTypesByPage: {},
      dominantTypes: {}
    };
  }
  return api.get('/stats/page-comparison/').then(res => res.data);
};

export default api;
