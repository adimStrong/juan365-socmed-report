import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Cell
} from 'recharts';
import { getPageComparison } from '../services/api';

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function Overlap() {
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedMetric, setSelectedMetric] = useState('engagement');

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await getPageComparison();
        setComparison(data);
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

  if (!comparison || !comparison.pages || comparison.pages.length === 0) {
    return (
      <div className="bg-yellow-50 rounded-lg p-6">
        <h3 className="font-medium text-yellow-900">No Data Available</h3>
        <p className="text-sm text-yellow-700 mt-1">
          Page comparison data is not available. Please run the export script.
        </p>
      </div>
    );
  }

  const { pages, postTypesByPage, dominantTypes } = comparison;

  // Prepare chart data
  const chartData = pages.map(p => ({
    name: p.page_name?.replace('Juana Babe ', ''),
    posts: p.posts,
    engagement: p.engagement,
    avgEngagement: p.avg_engagement,
    views: p.views,
    reach: p.reach,
    reactions: p.reactions,
    comments: p.comments,
    shares: p.shares,
    fans: p.fan_count || 0
  }));

  // Radar chart data (normalized for comparison)
  const maxValues = {
    posts: Math.max(...pages.map(p => p.posts)),
    engagement: Math.max(...pages.map(p => p.avg_engagement)),
    views: Math.max(...pages.map(p => p.views)),
    reach: Math.max(...pages.map(p => p.reach)),
    comments: Math.max(...pages.map(p => p.comments))
  };

  const radarData = [
    { metric: 'Posts', fullMark: 100 },
    { metric: 'Avg Eng', fullMark: 100 },
    { metric: 'Views', fullMark: 100 },
    { metric: 'Reach', fullMark: 100 },
    { metric: 'Comments', fullMark: 100 }
  ];

  pages.forEach(p => {
    const name = p.page_name?.replace('Juana Babe ', '');
    radarData[0][name] = Math.round((p.posts / maxValues.posts) * 100);
    radarData[1][name] = Math.round((p.avg_engagement / maxValues.engagement) * 100);
    radarData[2][name] = Math.round((p.views / maxValues.views) * 100);
    radarData[3][name] = Math.round((p.reach / maxValues.reach) * 100);
    radarData[4][name] = Math.round((p.comments / maxValues.comments) * 100);
  });

  const metricOptions = [
    { value: 'engagement', label: 'Total Engagement' },
    { value: 'avgEngagement', label: 'Avg Engagement' },
    { value: 'views', label: 'Views' },
    { value: 'reach', label: 'Reach' },
    { value: 'posts', label: 'Post Count' }
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Page Comparison</h1>
          <p className="text-sm text-gray-500">Compare performance across all 5 JuanBabes pages</p>
        </div>
      </div>

      {/* Rankings Table */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Performance Rankings</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-3 font-medium w-12">Rank</th>
                <th className="pb-3 font-medium">Page</th>
                <th className="pb-3 font-medium text-right">Posts</th>
                <th className="pb-3 font-medium text-right">Engagement</th>
                <th className="pb-3 font-medium text-right">Avg/Post</th>
                <th className="pb-3 font-medium text-right">Views</th>
                <th className="pb-3 font-medium text-right">Reach</th>
                <th className="pb-3 font-medium text-right">Fans</th>
                <th className="pb-3 font-medium">Share</th>
              </tr>
            </thead>
            <tbody>
              {pages.map((page, index) => (
                <tr key={page.page_id} className={`border-b ${index === 0 ? 'bg-indigo-50' : ''}`}>
                  <td className="py-3">
                    <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                      index === 0 ? 'bg-yellow-400 text-yellow-900' :
                      index === 1 ? 'bg-gray-300 text-gray-700' :
                      index === 2 ? 'bg-amber-600 text-white' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                      {page.rank}
                    </span>
                  </td>
                  <td className="py-3 font-medium">
                    {page.page_name?.replace('Juana Babe ', '')}
                    {index === 0 && (
                      <span className="ml-2 text-xs bg-indigo-600 text-white px-2 py-0.5 rounded">TOP</span>
                    )}
                  </td>
                  <td className="py-3 text-right">{page.posts?.toLocaleString()}</td>
                  <td className="py-3 text-right font-semibold text-indigo-600">
                    {page.engagement?.toLocaleString()}
                  </td>
                  <td className="py-3 text-right text-green-600">{page.avg_engagement?.toLocaleString()}</td>
                  <td className="py-3 text-right text-purple-600">
                    {page.views?.toLocaleString()}
                  </td>
                  <td className="py-3 text-right text-cyan-600">
                    {page.reach?.toLocaleString()}
                  </td>
                  <td className="py-3 text-right">
                    {page.fan_count?.toLocaleString() || 'N/A'}
                  </td>
                  <td className="py-3 w-32">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div
                          className="h-2 rounded-full"
                          style={{
                            width: `${page.engagement_share}%`,
                            backgroundColor: COLORS[index % COLORS.length]
                          }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 w-10">
                        {page.engagement_share}%
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Bar Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Comparison by Metric</h2>
            <select
              value={selectedMetric}
              onChange={(e) => setSelectedMetric(e.target.value)}
              className="text-sm border rounded-lg px-3 py-1"
            >
              {metricOptions.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" fontSize={12} />
              <YAxis fontSize={12} tickFormatter={(val) => val?.toLocaleString()} />
              <Tooltip formatter={(value) => value?.toLocaleString()} />
              <Bar dataKey={selectedMetric}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Radar Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Performance Profile</h2>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="metric" fontSize={12} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} fontSize={10} />
              {pages.slice(0, 3).map((p, index) => (
                <Radar
                  key={p.page_id}
                  name={p.page_name?.replace('Juana Babe ', '')}
                  dataKey={p.page_name?.replace('Juana Babe ', '')}
                  stroke={COLORS[index]}
                  fill={COLORS[index]}
                  fillOpacity={0.2}
                />
              ))}
              <Legend />
            </RadarChart>
          </ResponsiveContainer>
          <p className="text-xs text-gray-500 text-center mt-2">
            Showing top 3 pages. Values normalized to 100%.
          </p>
        </div>
      </div>

      {/* Content Strategy */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Content Strategy Comparison</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {pages.map((page, index) => {
            const pageTypes = postTypesByPage[page.page_id] || [];
            const totalPosts = pageTypes.reduce((sum, t) => sum + t.count, 0);

            return (
              <div key={page.page_id} className="border rounded-lg p-4">
                <h3 className="font-medium text-sm mb-2" style={{ color: COLORS[index] }}>
                  {page.page_name?.replace('Juana Babe ', '')}
                </h3>
                <div className="space-y-2">
                  {pageTypes.slice(0, 4).map(type => {
                    const pct = totalPosts > 0 ? Math.round((type.count / totalPosts) * 100) : 0;
                    return (
                      <div key={type.type} className="flex items-center gap-2">
                        <span className="text-xs text-gray-500 w-16 truncate">{type.type}</span>
                        <div className="flex-1 bg-gray-100 rounded-full h-2">
                          <div
                            className="h-2 rounded-full"
                            style={{
                              width: `${pct}%`,
                              backgroundColor: COLORS[index]
                            }}
                          />
                        </div>
                        <span className="text-xs text-gray-500 w-8">{pct}%</span>
                      </div>
                    );
                  })}
                </div>
                <div className="mt-3 pt-2 border-t">
                  <p className="text-xs text-gray-500">
                    Focus: <span className="font-medium">{dominantTypes[page.page_id]?.type || 'N/A'}</span>
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Efficiency Stats */}
      <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4 text-indigo-900">Efficiency Comparison</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {pages.map((page, index) => {
            const engPerView = page.views > 0 ? ((page.engagement / page.views) * 100).toFixed(2) : 0;
            const engPerReach = page.reach > 0 ? ((page.engagement / page.reach) * 100).toFixed(2) : 0;

            return (
              <div key={page.page_id} className="bg-white rounded-lg p-4 shadow-sm">
                <h3 className="font-medium text-sm mb-2" style={{ color: COLORS[index] }}>
                  {page.page_name?.replace('Juana Babe ', '')}
                </h3>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500">Eng/View</span>
                    <span className="font-medium">{engPerView}%</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500">Eng/Reach</span>
                    <span className="font-medium">{engPerReach}%</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500">Avg Eng</span>
                    <span className="font-medium">{page.avg_engagement?.toLocaleString()}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
