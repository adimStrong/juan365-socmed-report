import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { getPages } from '../services/api';

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function Pages() {
  const [pages, setPages] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchPages() {
      try {
        const data = await getPages();
        setPages(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchPages();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  // Calculate totals
  const totals = pages.reduce((acc, page) => ({
    posts: acc.posts + (page.post_count || 0),
    views: acc.views + (page.total_views || 0),
    reach: acc.reach + (page.total_reach || 0),
    reactions: acc.reactions + (page.total_reactions || 0),
    comments: acc.comments + (page.total_comments || 0),
    shares: acc.shares + (page.total_shares || 0),
    engagement: acc.engagement + (page.total_engagement || 0),
  }), { posts: 0, views: 0, reach: 0, reactions: 0, comments: 0, shares: 0, engagement: 0 });

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">JuanBabes - 5 Facebook Pages</h1>
        <span className="text-sm text-gray-500">{pages.length} pages tracked</span>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Total Posts</p>
          <p className="text-2xl font-bold text-indigo-600">{totals.posts.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Total Views</p>
          <p className="text-2xl font-bold text-purple-600">{totals.views.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Total Reach</p>
          <p className="text-2xl font-bold text-cyan-600">{totals.reach.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Total Reactions</p>
          <p className="text-2xl font-bold text-pink-600">{totals.reactions.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Total Comments</p>
          <p className="text-2xl font-bold text-blue-600">{totals.comments.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Total Shares</p>
          <p className="text-2xl font-bold text-orange-600">{totals.shares.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Total Engagement</p>
          <p className="text-2xl font-bold text-green-600">{totals.engagement.toLocaleString()}</p>
        </div>
      </div>

      {/* Comparison Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Engagement Comparison by Page</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={pages}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="page_name"
              fontSize={12}
              tickFormatter={(val) => val?.replace('Juana Babe ', '')}
            />
            <YAxis fontSize={12} tickFormatter={(val) => val?.toLocaleString()} />
            <Tooltip
              labelFormatter={(val) => val}
              formatter={(value) => [value?.toLocaleString(), '']}
            />
            <Legend />
            <Bar dataKey="total_reactions" name="Reactions" fill="#ec4899" />
            <Bar dataKey="total_comments" name="Comments" fill="#3b82f6" />
            <Bar dataKey="total_shares" name="Shares" fill="#f97316" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Page Cards */}
      <div className="grid gap-6">
        {pages.map((page, index) => (
          <div
            key={page.page_id}
            className={`bg-white rounded-lg shadow p-6 ${index === 0 ? 'ring-2 ring-indigo-500' : ''}`}
          >
            <div className="flex justify-between items-start">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-semibold text-gray-900">
                    {page.page_name}
                  </h2>
                  {index === 0 && (
                    <span className="px-2 py-0.5 bg-indigo-600 text-white text-xs rounded">
                      TOP PERFORMER
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-500">ID: {page.page_id}</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-500">Rank</p>
                <p className="text-2xl font-bold text-indigo-600">#{index + 1}</p>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="mt-6 grid grid-cols-2 md:grid-cols-5 lg:grid-cols-10 gap-4">
              <div className="bg-gray-50 rounded p-3">
                <p className="text-xs text-gray-500 uppercase">Posts</p>
                <p className="text-lg font-semibold">{page.post_count?.toLocaleString()}</p>
              </div>
              <div className="bg-purple-50 rounded p-3">
                <p className="text-xs text-gray-500 uppercase">Views</p>
                <p className="text-lg font-semibold text-purple-600">
                  {page.total_views?.toLocaleString() || 0}
                </p>
              </div>
              <div className="bg-cyan-50 rounded p-3">
                <p className="text-xs text-gray-500 uppercase">Reach</p>
                <p className="text-lg font-semibold text-cyan-600">
                  {page.total_reach?.toLocaleString() || 0}
                </p>
              </div>
              <div className="bg-pink-50 rounded p-3">
                <p className="text-xs text-gray-500 uppercase">Reactions</p>
                <p className="text-lg font-semibold text-pink-600">
                  {page.total_reactions?.toLocaleString()}
                </p>
              </div>
              <div className="bg-blue-50 rounded p-3">
                <p className="text-xs text-gray-500 uppercase">Comments</p>
                <p className="text-lg font-semibold text-blue-600">
                  {page.total_comments?.toLocaleString()}
                </p>
              </div>
              <div className="bg-orange-50 rounded p-3">
                <p className="text-xs text-gray-500 uppercase">Shares</p>
                <p className="text-lg font-semibold text-orange-600">
                  {page.total_shares?.toLocaleString()}
                </p>
              </div>
              <div className="bg-green-50 rounded p-3">
                <p className="text-xs text-gray-500 uppercase">Engagement</p>
                <p className="text-lg font-semibold text-green-600">
                  {page.total_engagement?.toLocaleString()}
                </p>
              </div>
              <div className="bg-indigo-50 rounded p-3">
                <p className="text-xs text-gray-500 uppercase">Avg/Post</p>
                <p className="text-lg font-semibold text-indigo-600">
                  {page.avg_engagement?.toLocaleString()}
                </p>
              </div>
              <div className="bg-amber-50 rounded p-3">
                <p className="text-xs text-gray-500 uppercase">Avg Reach</p>
                <p className="text-lg font-semibold text-amber-600">
                  {page.avg_reach?.toLocaleString() || 0}
                </p>
              </div>
              <div className="bg-gray-50 rounded p-3">
                <p className="text-xs text-gray-500 uppercase">Fans</p>
                <p className="text-lg font-semibold">
                  {page.fan_count?.toLocaleString() || 'N/A'}
                </p>
              </div>
            </div>

            {/* Engagement Bar */}
            <div className="mt-4">
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>Engagement Share</span>
                <span>{((page.total_engagement / totals.engagement) * 100).toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="h-2 rounded-full"
                  style={{
                    width: `${(page.total_engagement / totals.engagement) * 100}%`,
                    backgroundColor: COLORS[index % COLORS.length]
                  }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
