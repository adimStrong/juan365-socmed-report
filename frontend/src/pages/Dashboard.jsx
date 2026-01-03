import { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar, Legend
} from 'recharts';
import StatCard from '../components/StatCard';
import DateFilter from '../components/DateFilter';
import { getStats, getDailyEngagement, getPostTypeStats, getTopPosts, getPages, getTimeSeries, getDailyByPage } from '../services/api';

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [dailyData, setDailyData] = useState([]);
  const [dailyByPage, setDailyByPage] = useState({ data: [], pageNames: [] });
  const [postTypes, setPostTypes] = useState([]);
  const [topPosts, setTopPosts] = useState([]);
  const [pageComparison, setPageComparison] = useState([]);
  const [timeSeries, setTimeSeries] = useState(null);
  const [selectedPage, setSelectedPage] = useState(null);
  const [distributionView, setDistributionView] = useState('type'); // 'type' or 'page'
  const [pageMetric, setPageMetric] = useState('posts'); // posts, views, reach, engagement
  const [dateRange, setDateRange] = useState({ startDate: null, endDate: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const handleDateChange = (newDateRange) => {
    setDateRange(newDateRange);
  };

  useEffect(() => {
    async function fetchData() {
      try {
        const [statsData, dailyData, postTypeData, topPostsData, pageData, timeSeriesData, dailyByPageData] = await Promise.all([
          getStats(selectedPage, dateRange),
          getDailyEngagement(60, selectedPage, dateRange),
          getPostTypeStats(selectedPage),
          getTopPosts(5, 'engagement', selectedPage),
          getPages(),
          getTimeSeries(),
          getDailyByPage(60),
        ]);
        setStats(statsData);
        setDailyData(dailyData);
        setPostTypes(postTypeData);
        setTopPosts(topPostsData);
        setPageComparison(pageData);
        setTimeSeries(timeSeriesData);
        setDailyByPage(dailyByPageData);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [selectedPage, dateRange]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 text-red-600 p-4 rounded-lg">
        Error loading data: {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="flex justify-between items-center flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Socmed Report</h1>
            <p className="text-sm text-gray-500">
              {stats?.date_range_start} - {stats?.date_range_end}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <select
              value={selectedPage || ''}
              onChange={(e) => setSelectedPage(e.target.value || null)}
              className="px-4 py-2 border border-gray-300 rounded-lg bg-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="">All Pages</option>
              {pageComparison.map((page) => (
                <option key={page.page_id} value={page.page_id}>
                  {page.page_name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <DateFilter onDateChange={handleDateChange} />
      </div>

      {/* Stats Cards - Row 1 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Posts"
          value={stats?.total_posts?.toLocaleString()}
          icon="📝"
          color="indigo"
        />
        <StatCard
          title="Total Views"
          value={stats?.total_views?.toLocaleString()}
          subtitle={`Avg: ${stats?.avg_views?.toLocaleString() || 0}/post`}
          icon="👁️"
          color="purple"
        />
        <StatCard
          title="Total Reach"
          value={stats?.total_reach?.toLocaleString()}
          subtitle={`Avg: ${stats?.avg_reach?.toLocaleString() || 0}/post`}
          icon="📡"
          color="cyan"
        />
        <StatCard
          title="Total Engagement"
          value={stats?.total_engagement?.toLocaleString()}
          subtitle={`Avg: ${stats?.avg_engagement?.toLocaleString()}`}
          icon="⚡"
          color="green"
        />
      </div>

      {/* Stats Cards - Row 2 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          title="Total Reactions"
          value={stats?.total_reactions?.toLocaleString()}
          icon="❤️"
          color="pink"
        />
        <StatCard
          title="Total Comments"
          value={stats?.total_comments?.toLocaleString()}
          icon="💬"
          color="blue"
        />
        <StatCard
          title="Total Shares"
          value={stats?.total_shares?.toLocaleString()}
          icon="🔄"
          color="amber"
        />
        <StatCard
          title="Active Pages"
          value={`${stats?.total_pages || 0} / ${stats?.all_pages || stats?.total_pages || 0}`}
          subtitle="Pages with engagement data"
          icon="📄"
          color="teal"
        />
        <StatCard
          title="Total Followers"
          value={(() => {
            const total = pageComparison.reduce((sum, p) => sum + (p.followers_count || 0), 0);
            if (total >= 1000000) return (total / 1000000).toFixed(1) + 'M';
            if (total >= 1000) return (total / 1000).toFixed(1) + 'K';
            return total.toLocaleString();
          })()}
          subtitle={`across ${pageComparison.length} pages`}
          icon="👥"
          color="rose"
        />
      </div>

      {/* Page Comparison Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Page Comparison - Total Engagement</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={pageComparison} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" fontSize={12} tickFormatter={(val) => val?.toLocaleString()} />
            <YAxis
              type="category"
              dataKey="page_name"
              fontSize={12}
              width={120}
              tickFormatter={(val) => val?.replace('Juana Babe ', '')}
            />
            <Tooltip
              formatter={(value, name) => [value?.toLocaleString(), name]}
            />
            <Legend />
            <Bar dataKey="total_engagement" name="Total Engagement" fill="#6366f1" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Page Stats Table */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">{pageComparison.length} Pages Performance Summary</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[1000px]">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-3 font-medium whitespace-nowrap">Page</th>
                <th className="pb-3 font-medium text-right whitespace-nowrap">Followers</th>
                <th className="pb-3 font-medium text-right whitespace-nowrap">Posts</th>
                <th className="pb-3 font-medium text-right whitespace-nowrap">Views</th>
                <th className="pb-3 font-medium text-right whitespace-nowrap">Reach</th>
                <th className="pb-3 font-medium text-right whitespace-nowrap">Reactions</th>
                <th className="pb-3 font-medium text-right whitespace-nowrap">Comments</th>
                <th className="pb-3 font-medium text-right whitespace-nowrap">Shares</th>
                <th className="pb-3 font-medium text-right whitespace-nowrap">Engagement</th>
              </tr>
            </thead>
            <tbody>
              {pageComparison.map((page, index) => (
                <tr
                  key={page.page_id}
                  className={`border-b hover:bg-gray-50 ${index === 0 ? 'bg-indigo-50' : ''}`}
                >
                  <td className="py-3 font-medium whitespace-nowrap">
                    {page.page_name?.replace('Juana Babe ', '')}
                    {index === 0 && (
                      <span className="ml-2 px-2 py-0.5 bg-indigo-600 text-white text-xs rounded">
                        TOP
                      </span>
                    )}
                  </td>
                  <td className="py-3 text-right whitespace-nowrap font-semibold text-rose-600">
                    {(() => {
                      const num = page.followers_count;
                      if (!num) return '0';
                      if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
                      if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
                      return num.toLocaleString();
                    })()}
                  </td>
                  <td className="py-3 text-right whitespace-nowrap">{page.post_count?.toLocaleString()}</td>
                  <td className="py-3 text-right whitespace-nowrap text-purple-600">{page.total_views?.toLocaleString()}</td>
                  <td className="py-3 text-right whitespace-nowrap text-cyan-600">{page.total_reach?.toLocaleString()}</td>
                  <td className="py-3 text-right whitespace-nowrap">{page.total_reactions?.toLocaleString()}</td>
                  <td className="py-3 text-right whitespace-nowrap">{page.total_comments?.toLocaleString()}</td>
                  <td className="py-3 text-right whitespace-nowrap">{page.total_shares?.toLocaleString()}</td>
                  <td className="py-3 text-right font-semibold text-indigo-600 whitespace-nowrap">
                    {page.total_engagement?.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Engagement Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Daily Engagement (60 days)</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={dailyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tickFormatter={(val) => val?.slice(5) || ''}
                fontSize={12}
              />
              <YAxis fontSize={12} tickFormatter={(val) => val?.toLocaleString()} />
              <Tooltip formatter={(value) => value?.toLocaleString()} />
              <Legend />
              <Line
                type="monotone"
                dataKey="engagement"
                name="Engagement"
                stroke="#6366f1"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Post Type / Page Distribution */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
            <h2 className="text-lg font-semibold">
              {distributionView === 'type' ? 'Post Type Distribution' : `Distribution by Page (${pageMetric.charAt(0).toUpperCase() + pageMetric.slice(1)})`}
            </h2>
            <div className="flex items-center gap-2">
              {distributionView === 'page' && (
                <select
                  value={pageMetric}
                  onChange={(e) => setPageMetric(e.target.value)}
                  className="px-2 py-1 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="posts">Posts</option>
                  <option value="views">Views</option>
                  <option value="reach">Reach</option>
                  <option value="engagement">Engagement</option>
                </select>
              )}
              <div className="flex bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => setDistributionView('type')}
                  className={`px-3 py-1 text-sm rounded-md transition ${
                    distributionView === 'type'
                      ? 'bg-white shadow text-indigo-600 font-medium'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  By Type
                </button>
                <button
                  onClick={() => setDistributionView('page')}
                  className={`px-3 py-1 text-sm rounded-md transition ${
                    distributionView === 'page'
                      ? 'bg-white shadow text-indigo-600 font-medium'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  By Page
                </button>
              </div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              {distributionView === 'type' ? (
                <Pie
                  data={postTypes}
                  dataKey="count"
                  nameKey="post_type"
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={80}
                  paddingAngle={2}
                  label={({ post_type, percent }) => `${post_type} ${(percent * 100).toFixed(0)}%`}
                  labelLine={{ stroke: '#666', strokeWidth: 1 }}
                >
                  {postTypes.map((_, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
              ) : (
                <Pie
                  data={pageComparison.map(p => ({
                    ...p,
                    short_name: p.page_name?.replace('Juana Babe ', ''),
                    value: pageMetric === 'posts' ? p.post_count :
                           pageMetric === 'views' ? p.total_views :
                           pageMetric === 'reach' ? p.total_reach : p.total_engagement
                  }))}
                  dataKey="value"
                  nameKey="short_name"
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={80}
                  paddingAngle={2}
                  label={({ short_name, percent }) => `${short_name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={{ stroke: '#666', strokeWidth: 1 }}
                >
                  {pageComparison.map((_, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
              )}
              <Tooltip formatter={(value, name) => [value?.toLocaleString(), name]} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Reach & Views Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Reach Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Daily Reach (60 days)</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={dailyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tickFormatter={(val) => val?.slice(5) || ''}
                fontSize={12}
              />
              <YAxis fontSize={12} tickFormatter={(val) => val >= 1000 ? `${(val/1000).toFixed(0)}k` : val} />
              <Tooltip formatter={(value) => value?.toLocaleString()} />
              <Legend />
              <Line
                type="monotone"
                dataKey="reach"
                name="Reach"
                stroke="#06b6d4"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Daily Views Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Daily Views (60 days)</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={dailyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tickFormatter={(val) => val?.slice(5) || ''}
                fontSize={12}
              />
              <YAxis fontSize={12} tickFormatter={(val) => val >= 1000 ? `${(val/1000).toFixed(0)}k` : val} />
              <Tooltip formatter={(value) => value?.toLocaleString()} />
              <Legend />
              <Line
                type="monotone"
                dataKey="views"
                name="Views"
                stroke="#8b5cf6"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Daily Content Count - Stacked by Page */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Daily Content Published by Page (60 days)</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={dailyByPage.data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tickFormatter={(val) => val?.slice(5) || ''}
              fontSize={12}
            />
            <YAxis fontSize={12} allowDecimals={false} />
            <Tooltip
              formatter={(value, name) => [value || 0, name]}
              labelFormatter={(label) => `Date: ${label}`}
            />
            <Legend />
            {dailyByPage.pageNames.map((pageName, index) => (
              <Bar
                key={pageName}
                dataKey={pageName}
                name={pageName}
                stackId="a"
                fill={COLORS[index % COLORS.length]}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top Posts */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Top Performing Posts</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm table-fixed">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-3 font-medium w-16">Page</th>
                <th className="pb-3 font-medium w-64">Title</th>
                <th className="pb-3 font-medium w-20">Type</th>
                <th className="pb-3 font-medium text-right w-20">Reactions</th>
                <th className="pb-3 font-medium text-right w-20">Comments</th>
                <th className="pb-3 font-medium text-right w-16">Shares</th>
                <th className="pb-3 font-medium text-right w-24">Engagement</th>
              </tr>
            </thead>
            <tbody>
              {topPosts.map((post) => (
                <tr key={post.post_id} className="border-b hover:bg-gray-50">
                  <td className="py-3 text-xs text-gray-600 truncate">
                    {post.page_name?.replace('Juana Babe ', '')}
                  </td>
                  <td className="py-3 truncate">
                    <a
                      href={post.permalink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-600 hover:underline"
                      title={post.title}
                    >
                      {post.title?.slice(0, 60) || 'Untitled'}...
                    </a>
                  </td>
                  <td className="py-3">
                    <span className="px-2 py-1 bg-gray-100 rounded text-xs">
                      {post.post_type}
                    </span>
                  </td>
                  <td className="py-3 text-right">{post.reactions?.toLocaleString()}</td>
                  <td className="py-3 text-right">{post.comments?.toLocaleString()}</td>
                  <td className="py-3 text-right">{post.shares?.toLocaleString()}</td>
                  <td className="py-3 text-right font-semibold text-indigo-600">
                    {post.engagement?.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Post Type Performance */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Engagement by Post Type</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={postTypes}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="post_type" fontSize={12} />
            <YAxis fontSize={12} tickFormatter={(val) => val?.toLocaleString()} />
            <Tooltip formatter={(value) => value?.toLocaleString()} />
            <Legend />
            <Bar dataKey="avg_engagement" name="Avg Engagement" fill="#6366f1" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* AI Insights Section */}
      {timeSeries?.insights?.length > 0 && (
        <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 text-indigo-900">Performance Insights</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {timeSeries.insights.map((insight, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-lg ${
                  insight.type === 'trend_up' ? 'bg-green-100 border-l-4 border-green-500' :
                  insight.type === 'trend_down' ? 'bg-red-100 border-l-4 border-red-500' :
                  insight.type === 'best_day' ? 'bg-yellow-100 border-l-4 border-yellow-500' :
                  insight.type === 'content_type' ? 'bg-purple-100 border-l-4 border-purple-500' :
                  insight.type === 'top_page' ? 'bg-blue-100 border-l-4 border-blue-500' :
                  'bg-indigo-100 border-l-4 border-indigo-500'
                }`}
              >
                <h3 className="font-semibold text-sm mb-1">{insight.title}</h3>
                <p className="text-xs text-gray-700">{insight.text}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Monthly Performance Cards */}
      {timeSeries?.monthly?.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Monthly Performance</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {timeSeries.monthly.slice(0, 3).map((month) => (
              <div
                key={month.month}
                className="bg-gray-50 rounded-lg p-4 border"
              >
                <div className="flex justify-between items-center mb-3">
                  <span className="font-bold text-lg">{month.month}</span>
                  {month.mom_change !== null && (
                    <span className={`text-sm px-2 py-1 rounded ${
                      month.mom_change > 0 ? 'bg-green-100 text-green-700' :
                      month.mom_change < 0 ? 'bg-red-100 text-red-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {month.mom_change > 0 ? '+' : ''}{month.mom_change}%
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-500">Posts</span>
                    <p className="font-semibold">{month.posts}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Engagement</span>
                    <p className="font-semibold text-indigo-600">{month.engagement?.toLocaleString()}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Views</span>
                    <p className="font-semibold text-purple-600">{month.views?.toLocaleString()}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Reach</span>
                    <p className="font-semibold text-cyan-600">{month.reach?.toLocaleString()}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Weekly Performance Table */}
      {timeSeries?.weekly?.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Weekly Performance (Last 4 Weeks)</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="pb-3 font-medium">Week</th>
                  <th className="pb-3 font-medium text-right">Posts</th>
                  <th className="pb-3 font-medium text-right">Views</th>
                  <th className="pb-3 font-medium text-right">Reach</th>
                  <th className="pb-3 font-medium text-right">Engagement</th>
                  <th className="pb-3 font-medium text-right">WoW Change</th>
                </tr>
              </thead>
              <tbody>
                {timeSeries.weekly.map((week, idx) => (
                  <tr key={week.week} className={`border-b ${idx === 0 ? 'bg-indigo-50' : ''}`}>
                    <td className="py-3">
                      <span className="font-medium">{week.week_start}</span>
                      <span className="text-gray-400 mx-1">-</span>
                      <span className="font-medium">{week.week_end}</span>
                    </td>
                    <td className="py-3 text-right">{week.posts}</td>
                    <td className="py-3 text-right text-purple-600">{week.views?.toLocaleString()}</td>
                    <td className="py-3 text-right text-cyan-600">{week.reach?.toLocaleString()}</td>
                    <td className="py-3 text-right font-semibold text-indigo-600">{week.engagement?.toLocaleString()}</td>
                    <td className="py-3 text-right">
                      {week.wow_change !== null ? (
                        <span className={`px-2 py-1 rounded text-xs ${
                          week.wow_change > 0 ? 'bg-green-100 text-green-700' :
                          week.wow_change < 0 ? 'bg-red-100 text-red-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {week.wow_change > 0 ? '+' : ''}{week.wow_change}%
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Day of Week Analysis */}
      {timeSeries?.dayOfWeek?.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Best Days to Post</h2>
          <div className="grid grid-cols-4 sm:grid-cols-7 gap-2">
            {timeSeries.dayOfWeek.map((day) => (
              <div
                key={day.day}
                className={`text-center p-4 rounded-lg ${
                  day.is_best ? 'bg-yellow-100 border-2 border-yellow-400' : 'bg-gray-50'
                }`}
              >
                <div className={`text-sm font-bold ${day.is_best ? 'text-yellow-700' : 'text-gray-600'}`}>
                  {day.day}
                  {day.is_best && <span className="ml-1">⭐</span>}
                </div>
                <div className="text-xl font-bold mt-2 text-indigo-600">
                  {day.avg_engagement?.toLocaleString()}
                </div>
                <div className="text-xs text-gray-500">avg eng</div>
                <div className="text-xs text-gray-400 mt-1">{day.posts} posts</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
