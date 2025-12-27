import { useState, useEffect } from 'react';
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { getPages, getPostTypeStats, getTopPosts, getCommentAnalysis } from '../services/api';

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function Comments() {
  const [pages, setPages] = useState([]);
  const [postTypes, setPostTypes] = useState([]);
  const [topCommented, setTopCommented] = useState([]);
  const [commentAnalysis, setCommentAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [pageData, postTypeData, topPostsData, analysisData] = await Promise.all([
          getPages(),
          getPostTypeStats(),
          getTopPosts(20, 'engagement'),
          getCommentAnalysis(),
        ]);
        setPages(pageData);
        setPostTypes(postTypeData);
        // Sort by comments
        const sorted = [...topPostsData].sort((a, b) => (b.comments || 0) - (a.comments || 0));
        setTopCommented(sorted.slice(0, 10));
        setCommentAnalysis(analysisData);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  // Calculate totals
  const totalComments = pages.reduce((sum, p) => sum + (p.total_comments || 0), 0);
  const totalPosts = pages.reduce((sum, p) => sum + (p.post_count || 0), 0);
  const avgCommentsPerPost = totalPosts > 0 ? (totalComments / totalPosts).toFixed(1) : 0;

  // Find page with most comments
  const topPage = pages.reduce((max, p) =>
    (p.total_comments || 0) > (max?.total_comments || 0) ? p : max, pages[0]);

  // Prepare chart data
  const commentsByPage = pages.map(p => ({
    name: p.page_name?.replace('Juana Babe ', ''),
    comments: p.total_comments || 0,
    posts: p.post_count || 0,
    avgPerPost: p.post_count > 0 ? Math.round((p.total_comments || 0) / p.post_count) : 0
  }));

  const commentsByType = postTypes.map(pt => ({
    type: pt.post_type,
    comments: pt.comments || 0,
    count: pt.count || 0,
    avgPerPost: pt.count > 0 ? Math.round((pt.comments || 0) / pt.count) : 0
  }));

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Comment Analysis</h1>
          <p className="text-sm text-gray-500">Analyze comment distribution across pages and post types</p>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Total Comments</p>
          <p className="text-3xl font-bold text-blue-600">{totalComments.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Total Posts</p>
          <p className="text-3xl font-bold text-indigo-600">{totalPosts.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Avg Comments/Post</p>
          <p className="text-3xl font-bold text-green-600">{avgCommentsPerPost}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Top Page</p>
          <p className="text-xl font-bold text-purple-600">
            {topPage?.page_name?.replace('Juana Babe ', '')}
          </p>
          <p className="text-sm text-gray-500">{topPage?.total_comments?.toLocaleString()} comments</p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Comments by Page Pie */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Comments Distribution by Page</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={commentsByPage}
                dataKey="comments"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={({ name, comments }) => `${name}: ${comments.toLocaleString()}`}
              >
                {commentsByPage.map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => value?.toLocaleString()} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Comments by Post Type */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Comments by Post Type</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={commentsByType}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="type" fontSize={12} />
              <YAxis fontSize={12} tickFormatter={(val) => val?.toLocaleString()} />
              <Tooltip formatter={(value) => value?.toLocaleString()} />
              <Legend />
              <Bar dataKey="comments" name="Total Comments" fill="#3b82f6" />
              <Bar dataKey="avgPerPost" name="Avg/Post" fill="#22c55e" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Page Breakdown Table */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Comments by Page</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-3 font-medium">Page</th>
                <th className="pb-3 font-medium text-right">Posts</th>
                <th className="pb-3 font-medium text-right">Comments</th>
                <th className="pb-3 font-medium text-right">Avg/Post</th>
                <th className="pb-3 font-medium text-right">% of Total</th>
                <th className="pb-3 font-medium">Distribution</th>
              </tr>
            </thead>
            <tbody>
              {commentsByPage.map((page, index) => (
                <tr key={page.name} className={`border-b ${index === 0 ? 'bg-blue-50' : ''}`}>
                  <td className="py-3 font-medium">
                    {page.name}
                    {index === 0 && (
                      <span className="ml-2 px-2 py-0.5 bg-blue-600 text-white text-xs rounded">
                        TOP
                      </span>
                    )}
                  </td>
                  <td className="py-3 text-right">{page.posts.toLocaleString()}</td>
                  <td className="py-3 text-right text-blue-600 font-semibold">
                    {page.comments.toLocaleString()}
                  </td>
                  <td className="py-3 text-right text-green-600">{page.avgPerPost}</td>
                  <td className="py-3 text-right">
                    {((page.comments / totalComments) * 100).toFixed(1)}%
                  </td>
                  <td className="py-3">
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="h-2 rounded-full"
                        style={{
                          width: `${(page.comments / totalComments) * 100}%`,
                          backgroundColor: COLORS[index % COLORS.length]
                        }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Top Commented Posts */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Top 10 Most Commented Posts</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-3 font-medium w-16">#</th>
                <th className="pb-3 font-medium w-24">Page</th>
                <th className="pb-3 font-medium">Title</th>
                <th className="pb-3 font-medium w-20">Type</th>
                <th className="pb-3 font-medium text-right w-24">Comments</th>
                <th className="pb-3 font-medium text-right w-24">Reactions</th>
                <th className="pb-3 font-medium text-right w-24">Engagement</th>
              </tr>
            </thead>
            <tbody>
              {topCommented.map((post, index) => (
                <tr key={post.post_id} className="border-b hover:bg-gray-50">
                  <td className="py-3 text-gray-500">{index + 1}</td>
                  <td className="py-3 text-xs">
                    {post.page_name?.replace('Juana Babe ', '')}
                  </td>
                  <td className="py-3">
                    <a
                      href={post.permalink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-600 hover:underline"
                      title={post.title}
                    >
                      {post.title?.slice(0, 50) || 'Untitled'}...
                    </a>
                  </td>
                  <td className="py-3">
                    <span className="px-2 py-1 bg-gray-100 rounded text-xs">
                      {post.post_type}
                    </span>
                  </td>
                  <td className="py-3 text-right font-semibold text-blue-600">
                    {post.comments?.toLocaleString()}
                  </td>
                  <td className="py-3 text-right text-pink-600">
                    {post.reactions?.toLocaleString()}
                  </td>
                  <td className="py-3 text-right text-green-600">
                    {post.engagement?.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Self-Comment Analysis Section */}
      {commentAnalysis && commentAnalysis.summary && commentAnalysis.summary.posts_analyzed > 0 ? (
        <div className="space-y-6">
          {/* Self-Comment Summary Stats */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4 text-blue-900">Self-Comment Analysis</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg p-4 shadow-sm">
                <p className="text-sm text-gray-500">Posts Analyzed</p>
                <p className="text-2xl font-bold text-indigo-600">
                  {commentAnalysis.summary.posts_analyzed?.toLocaleString()}
                </p>
              </div>
              <div className="bg-white rounded-lg p-4 shadow-sm">
                <p className="text-sm text-gray-500">Self-Comments</p>
                <p className="text-2xl font-bold text-orange-600">
                  {commentAnalysis.summary.total_self_comments?.toLocaleString()}
                </p>
                <p className="text-xs text-gray-400">
                  {commentAnalysis.summary.self_comment_rate}% of total
                </p>
              </div>
              <div className="bg-white rounded-lg p-4 shadow-sm">
                <p className="text-sm text-gray-500">Organic Comments</p>
                <p className="text-2xl font-bold text-green-600">
                  {commentAnalysis.summary.total_organic_comments?.toLocaleString()}
                </p>
              </div>
              <div className="bg-white rounded-lg p-4 shadow-sm">
                <p className="text-sm text-gray-500">Posts with Self-Comment</p>
                <p className="text-2xl font-bold text-purple-600">
                  {commentAnalysis.summary.posts_with_self_comment}
                </p>
                <p className="text-xs text-gray-400">
                  {commentAnalysis.summary.posts_with_self_pct}% of posts
                </p>
              </div>
            </div>
          </div>

          {/* Engagement Effectivity */}
          {commentAnalysis.effectivity && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Comment Effectivity</h2>
              <p className="text-sm text-gray-500 mb-4">
                Does self-commenting boost engagement?
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center p-4 bg-orange-50 rounded-lg">
                  <p className="text-sm text-gray-600">Avg Engagement</p>
                  <p className="text-sm text-gray-500">WITH Self-Comment</p>
                  <p className="text-3xl font-bold text-orange-600 mt-2">
                    {Math.round(commentAnalysis.effectivity.avg_engagement_with_self)?.toLocaleString()}
                  </p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600">Avg Engagement</p>
                  <p className="text-sm text-gray-500">WITHOUT Self-Comment</p>
                  <p className="text-3xl font-bold text-gray-600 mt-2">
                    {Math.round(commentAnalysis.effectivity.avg_engagement_without_self)?.toLocaleString()}
                  </p>
                </div>
                <div className={`text-center p-4 rounded-lg ${
                  commentAnalysis.effectivity.engagement_boost_pct > 0
                    ? 'bg-green-50'
                    : 'bg-red-50'
                }`}>
                  <p className="text-sm text-gray-600">Engagement</p>
                  <p className="text-sm text-gray-500">Boost/Drop</p>
                  <p className={`text-3xl font-bold mt-2 ${
                    commentAnalysis.effectivity.engagement_boost_pct > 0
                      ? 'text-green-600'
                      : 'text-red-600'
                  }`}>
                    {commentAnalysis.effectivity.engagement_boost_pct > 0 ? '+' : ''}
                    {commentAnalysis.effectivity.engagement_boost_pct}%
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Self-Comment by Page */}
          {commentAnalysis.byPage && commentAnalysis.byPage.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Self-Comments by Page</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="pb-3 font-medium">Page</th>
                      <th className="pb-3 font-medium text-right">Posts</th>
                      <th className="pb-3 font-medium text-right">Self</th>
                      <th className="pb-3 font-medium text-right">Organic</th>
                      <th className="pb-3 font-medium text-right">Self Rate</th>
                      <th className="pb-3 font-medium">Distribution</th>
                    </tr>
                  </thead>
                  <tbody>
                    {commentAnalysis.byPage.map((page, index) => (
                      <tr key={page.page_id} className="border-b">
                        <td className="py-3 font-medium">
                          {page.page_name?.replace('Juana Babe ', '')}
                        </td>
                        <td className="py-3 text-right">{page.posts_with_comments}</td>
                        <td className="py-3 text-right text-orange-600 font-semibold">
                          {page.self_comments}
                        </td>
                        <td className="py-3 text-right text-green-600">
                          {page.organic_comments?.toLocaleString()}
                        </td>
                        <td className="py-3 text-right">{page.self_rate}%</td>
                        <td className="py-3">
                          <div className="w-full bg-gray-200 rounded-full h-2 flex">
                            <div
                              className="h-2 rounded-l-full bg-orange-500"
                              style={{ width: `${page.self_rate}%` }}
                            />
                            <div
                              className="h-2 rounded-r-full bg-green-500"
                              style={{ width: `${100 - page.self_rate}%` }}
                            />
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-3 flex gap-4 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 bg-orange-500 rounded" /> Self-Comments
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 bg-green-500 rounded" /> Organic Comments
                </span>
              </div>
            </div>
          )}

          {/* Top Self-Commented Posts */}
          {commentAnalysis.topSelfCommented && commentAnalysis.topSelfCommented.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Posts with Most Self-Comments</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="pb-3 font-medium w-16">#</th>
                      <th className="pb-3 font-medium w-24">Page</th>
                      <th className="pb-3 font-medium">Title</th>
                      <th className="pb-3 font-medium text-right w-20">Self</th>
                      <th className="pb-3 font-medium text-right w-20">Total</th>
                      <th className="pb-3 font-medium text-right w-24">Engagement</th>
                    </tr>
                  </thead>
                  <tbody>
                    {commentAnalysis.topSelfCommented.map((post, index) => (
                      <tr key={post.post_id} className="border-b hover:bg-gray-50">
                        <td className="py-3 text-gray-500">{index + 1}</td>
                        <td className="py-3 text-xs">
                          {post.page_name?.replace('Juana Babe ', '')}
                        </td>
                        <td className="py-3">
                          <a
                            href={post.permalink}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-indigo-600 hover:underline"
                          >
                            {post.title || 'Untitled'}
                          </a>
                        </td>
                        <td className="py-3 text-right font-semibold text-orange-600">
                          {post.self_comments}
                        </td>
                        <td className="py-3 text-right text-gray-600">
                          {post.total_comments}
                        </td>
                        <td className="py-3 text-right text-green-600">
                          {post.engagement?.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 text-blue-900">Comment Effectivity Analysis</h2>
          <div className="bg-white/50 rounded-lg p-4 text-center">
            <p className="text-gray-600 mb-2">Self-Comment vs Organic Comment analysis requires Facebook API data.</p>
            <p className="text-sm text-gray-500">
              Run <code className="bg-gray-100 px-2 py-1 rounded">python fetch_comments.py</code> to fetch comment details.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
