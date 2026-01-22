import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getAnalytics } from '../services/api';

export default function AnalyticsReport({ pageGroup }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedMonth, setSelectedMonth] = useState('all'); // 'all', 'december', 'january'

  useEffect(() => {
    getAnalytics().then(d => {
      setData(d);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex justify-center items-center h-64">Loading...</div>;
  }

  const report = data?.analyticsReport || {};
  const pageGroupHealth = data?.pageGroupHealth || {};
  const pageGroupComparison = data?.pageGroupComparison || {};
  const watchTimeData = data?.watchTime || {};

  // Get data for the selected page group
  const groupData = pageGroup === 'juan365' ? pageGroupHealth.juan365 : pageGroupHealth.liveStream;
  const comparisonData = pageGroup === 'juan365' ? pageGroupComparison.juan365 : pageGroupComparison.liveStream;
  const watchData = pageGroup === 'juan365' ? watchTimeData.juan365 : watchTimeData.liveStream;
  const deepDiveData = pageGroup === 'juan365' ? data?.deepDive?.juan365 : data?.deepDive?.liveStream;

  const isJuan365 = pageGroup === 'juan365';
  const groupName = isJuan365 ? 'Juan365' : 'Juan365 Live Stream';
  const accentColor = isJuan365 ? 'blue' : 'red';
  const otherGroupName = isJuan365 ? 'Live Stream' : 'Juan365';
  const otherGroupPath = isJuan365 ? '/report/livestream' : '/report/juan365';

  // Get monthly data based on filter
  const getFilteredStats = () => {
    if (selectedMonth === 'december') {
      return comparisonData?.december || {};
    } else if (selectedMonth === 'january') {
      return comparisonData?.january || {};
    }
    return comparisonData?.total || groupData?.overall || {};
  };

  const filteredStats = getFilteredStats();
  const monthLabel = selectedMonth === 'december' ? 'December 2025' :
                     selectedMonth === 'january' ? 'January 2026' :
                     'Dec 2025 - Jan 2026';

  return (
    <div className="space-y-6">
      {/* Header with Navigation */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-start mb-4">
          <div className="flex items-center gap-4">
            <Link to="/report" className="text-gray-400 hover:text-gray-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <div className="flex items-center gap-3">
                <div className={`w-4 h-4 rounded-full bg-${accentColor}-500`}></div>
                <h1 className="text-2xl font-bold text-gray-900">{groupName} Report</h1>
              </div>
              <p className="text-gray-500 mt-1">Detailed analytics for {groupName} pages</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-500">Last Updated</div>
            <div className="text-lg font-semibold text-indigo-600">
              {report.generatedAt ? new Date(report.generatedAt).toLocaleDateString('en-US', {
                year: 'numeric', month: 'short', day: 'numeric'
              }) : new Date().toLocaleDateString()}
            </div>
          </div>
        </div>

        {/* Page Group Tabs */}
        <div className="flex gap-2 mb-4">
          <Link
            to="/report/juan365"
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              isJuan365
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Juan365
          </Link>
          <Link
            to="/report/livestream"
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              !isJuan365
                ? 'bg-red-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Live Stream
          </Link>
        </div>

        {/* Date Filter */}
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">Period:</span>
          <div className="flex gap-2">
            <button
              onClick={() => setSelectedMonth('all')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                selectedMonth === 'all'
                  ? `bg-${accentColor}-100 text-${accentColor}-700 border-2 border-${accentColor}-300`
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              All (Dec-Jan)
            </button>
            <button
              onClick={() => setSelectedMonth('december')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                selectedMonth === 'december'
                  ? `bg-${accentColor}-100 text-${accentColor}-700 border-2 border-${accentColor}-300`
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Dec 2025
            </button>
            <button
              onClick={() => setSelectedMonth('january')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                selectedMonth === 'january'
                  ? `bg-${accentColor}-100 text-${accentColor}-700 border-2 border-${accentColor}-300`
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Jan 2026
            </button>
          </div>
        </div>
      </div>

      {/* Executive Summary */}
      <div className={`bg-gradient-to-r ${
        groupData?.health?.status === 'healthy' ? 'from-green-500 to-emerald-500' :
        groupData?.health?.status === 'warning' ? 'from-yellow-500 to-amber-500' : 'from-red-500 to-orange-500'
      } rounded-lg shadow p-6 text-white`}>
        <h2 className="text-xl font-bold mb-4">{groupName} Summary - {monthLabel}</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white/20 rounded-lg p-4">
            <div className="text-sm opacity-80">Health Score</div>
            <div className="text-3xl font-bold">{groupData?.health?.score?.toFixed(0) || 0}/100</div>
            <div className="text-sm font-semibold capitalize">{groupData?.health?.status || 'N/A'}</div>
          </div>
          <div className="bg-white/20 rounded-lg p-4">
            <div className="text-sm opacity-80">WoW Change</div>
            <div className="text-3xl font-bold">
              {groupData?.health?.wowChange >= 0 ? '+' : ''}{groupData?.health?.wowChange?.toFixed(1) || 0}%
            </div>
            <div className="text-sm">Week over Week</div>
          </div>
          <div className="bg-white/20 rounded-lg p-4">
            <div className="text-sm opacity-80">vs Peak</div>
            <div className="text-3xl font-bold">
              {groupData?.health?.vsPeak >= 0 ? '+' : ''}{groupData?.health?.vsPeak?.toFixed(1) || 0}%
            </div>
            <div className="text-sm">Performance</div>
          </div>
          <div className="bg-white/20 rounded-lg p-4">
            <div className="text-sm opacity-80">Avg Engagement</div>
            <div className="text-3xl font-bold">{filteredStats.avg_engagement?.toFixed(0) || groupData?.overall?.avgEngagement?.toFixed(0) || 0}</div>
            <div className="text-sm">per post</div>
          </div>
        </div>
      </div>

      {/* Key Metrics for Selected Period */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Performance Metrics - {monthLabel}</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className={`bg-${accentColor}-50 rounded-lg p-4 text-center`}>
            <div className="text-sm text-gray-500">Total Posts</div>
            <div className={`text-3xl font-bold text-${accentColor}-600`}>
              {filteredStats.posts || filteredStats.totalPosts || groupData?.overall?.totalPosts || 0}
            </div>
          </div>
          <div className={`bg-${accentColor}-50 rounded-lg p-4 text-center`}>
            <div className="text-sm text-gray-500">Total Engagement</div>
            <div className={`text-3xl font-bold text-${accentColor}-600`}>
              {(filteredStats.total_engagement || filteredStats.totalEngagement || groupData?.overall?.totalEngagement || 0).toLocaleString()}
            </div>
          </div>
          <div className={`bg-${accentColor}-50 rounded-lg p-4 text-center`}>
            <div className="text-sm text-gray-500">Avg Engagement</div>
            <div className={`text-3xl font-bold text-${accentColor}-600`}>
              {(filteredStats.avg_engagement || filteredStats.avgEngagement || groupData?.overall?.avgEngagement || 0).toFixed(1)}
            </div>
          </div>
          <div className={`bg-${accentColor}-50 rounded-lg p-4 text-center`}>
            <div className="text-sm text-gray-500">Total Views</div>
            <div className={`text-3xl font-bold text-${accentColor}-600`}>
              {(filteredStats.total_views || filteredStats.totalViews || groupData?.overall?.totalViews || 0).toLocaleString()}
            </div>
          </div>
        </div>
      </div>

      {/* Monthly Comparison (only show when "all" is selected) */}
      {selectedMonth === 'all' && comparisonData && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">Monthly Comparison</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* December */}
            <div className={`border-2 border-${accentColor}-200 rounded-lg p-4`}>
              <h3 className={`font-semibold text-${accentColor}-700 mb-3`}>December 2025</h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-500">Posts</span>
                  <span className="font-bold">{comparisonData.december?.posts || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Total Engagement</span>
                  <span className="font-bold">{(comparisonData.december?.total_engagement || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Avg Engagement</span>
                  <span className="font-bold">{comparisonData.december?.avg_engagement?.toFixed(1) || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Total Views</span>
                  <span className="font-bold">{(comparisonData.december?.total_views || 0).toLocaleString()}</span>
                </div>
              </div>
            </div>

            {/* January */}
            <div className={`border-2 border-${accentColor}-200 rounded-lg p-4`}>
              <h3 className={`font-semibold text-${accentColor}-700 mb-3`}>January 2026</h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-500">Posts</span>
                  <span className="font-bold">{comparisonData.january?.posts || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Total Engagement</span>
                  <span className="font-bold">{(comparisonData.january?.total_engagement || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Avg Engagement</span>
                  <span className="font-bold">{comparisonData.january?.avg_engagement?.toFixed(1) || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Total Views</span>
                  <span className="font-bold">{(comparisonData.january?.total_views || 0).toLocaleString()}</span>
                </div>
              </div>
            </div>
          </div>

          {/* MoM Change */}
          <div className={`mt-4 p-4 rounded-lg ${comparisonData.momChange?.avg_engagement >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
            <div className="flex justify-between items-center">
              <span className="font-semibold">Month-over-Month Change (Dec → Jan)</span>
              <span className={`text-xl font-bold ${comparisonData.momChange?.avg_engagement >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {comparisonData.momChange?.avg_engagement >= 0 ? '+' : ''}
                {comparisonData.momChange?.avg_engagement?.toFixed(1) || 0}% avg engagement
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Weekly Performance */}
      {groupData?.weekly && groupData.weekly.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">Weekly Performance</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-gray-100">
                  <th className="px-3 py-2 text-left">Week</th>
                  <th className="px-3 py-2 text-right">Posts</th>
                  <th className="px-3 py-2 text-right">Total Engagement</th>
                  <th className="px-3 py-2 text-right">Avg Engagement</th>
                  <th className="px-3 py-2 text-right">Total Views</th>
                  <th className="px-3 py-2 text-right">Avg Views</th>
                </tr>
              </thead>
              <tbody>
                {groupData.weekly.map((week, i) => (
                  <tr key={i} className="border-b hover:bg-gray-50">
                    <td className="px-3 py-2">{week.week}</td>
                    <td className="px-3 py-2 text-right">{week.post_count}</td>
                    <td className="px-3 py-2 text-right">{week.total_engagement?.toLocaleString()}</td>
                    <td className="px-3 py-2 text-right font-medium">{week.avg_engagement?.toFixed(1)}</td>
                    <td className="px-3 py-2 text-right">{week.total_views?.toLocaleString()}</td>
                    <td className="px-3 py-2 text-right">{week.avg_views?.toFixed(0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Post Type Breakdown */}
      {groupData?.postTypes && groupData.postTypes.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">Post Type Breakdown</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {groupData.postTypes.map((pt, i) => (
              <div key={i} className={`bg-${accentColor}-50 rounded-lg p-4`}>
                <div className="flex justify-between items-start mb-2">
                  <span className="font-semibold capitalize">{pt.type}</span>
                  <span className={`text-${accentColor}-600 font-bold`}>{pt.count} posts</span>
                </div>
                <div className="text-sm text-gray-500">
                  Avg Engagement: <span className="font-medium text-gray-700">{pt.avg_engagement?.toFixed(0)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Watch Time Analytics */}
      {watchData && watchData.overall && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <span>⏱️</span> Watch Time Analytics
          </h2>

          {/* Overall Watch Time Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className={`bg-${accentColor}-50 rounded-lg p-4 text-center`}>
              <div className="text-sm text-gray-500">Avg Watch Time</div>
              <div className={`text-3xl font-bold text-${accentColor}-600`}>
                {watchData.overall.avgWatchTimeSec?.toFixed(1) || 0}s
              </div>
              <div className="text-xs text-gray-400">per video</div>
            </div>
            <div className={`bg-${accentColor}-50 rounded-lg p-4 text-center`}>
              <div className="text-sm text-gray-500">Videos Tracked</div>
              <div className={`text-3xl font-bold text-${accentColor}-600`}>
                {(watchData.overall.postsWithWatchTime || 0).toLocaleString()}
              </div>
              <div className="text-xs text-gray-400">with watch data</div>
            </div>
            <div className={`bg-${accentColor}-50 rounded-lg p-4 text-center`}>
              <div className="text-sm text-gray-500">Total Watch Time</div>
              <div className={`text-3xl font-bold text-${accentColor}-600`}>
                {((watchData.overall.totalWatchTimeHours || 0) / 24).toLocaleString(undefined, {maximumFractionDigits: 1})}
              </div>
              <div className="text-xs text-gray-400">days</div>
            </div>
            <div className={`bg-${accentColor}-50 rounded-lg p-4 text-center`}>
              <div className="text-sm text-gray-500">Total Views</div>
              <div className={`text-3xl font-bold text-${accentColor}-600`}>
                {(watchData.overall.totalViews || 0).toLocaleString()}
              </div>
              <div className="text-xs text-gray-400">video views</div>
            </div>
          </div>

          {/* MoM Change */}
          <div className={`mb-6 p-4 rounded-lg ${watchData.momChange >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
            <div className="flex justify-between items-center">
              <span className="font-semibold">Avg Watch Time Change (Dec → Jan)</span>
              <span className={`text-xl font-bold ${watchData.momChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {watchData.momChange !== null ? `${watchData.momChange >= 0 ? '+' : ''}${watchData.momChange?.toFixed(1)}%` : 'N/A'}
              </span>
            </div>
          </div>

          {/* Monthly Watch Time Comparison */}
          {selectedMonth === 'all' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* December Watch Time */}
              <div className={`border-2 border-${accentColor}-200 rounded-lg p-4`}>
                <h3 className={`font-semibold text-${accentColor}-700 mb-3`}>December 2025</h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Videos</span>
                    <span className="font-bold">{(watchData.december?.posts || 0).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Avg Watch Time</span>
                    <span className="font-bold">{watchData.december?.avgWatchTimeSec?.toFixed(1) || 0}s</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Total Watch Time</span>
                    <span className="font-bold">{((watchData.december?.totalWatchTimeHours || 0) / 24).toLocaleString(undefined, {maximumFractionDigits: 1})} days</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Total Views</span>
                    <span className="font-bold">{(watchData.december?.totalViews || 0).toLocaleString()}</span>
                  </div>
                </div>
              </div>

              {/* January Watch Time */}
              <div className={`border-2 border-${accentColor}-200 rounded-lg p-4`}>
                <h3 className={`font-semibold text-${accentColor}-700 mb-3`}>January 2026</h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Videos</span>
                    <span className="font-bold">{(watchData.january?.posts || 0).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Avg Watch Time</span>
                    <span className="font-bold">{watchData.january?.avgWatchTimeSec?.toFixed(1) || 0}s</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Total Watch Time</span>
                    <span className="font-bold">{((watchData.january?.totalWatchTimeHours || 0) / 24).toLocaleString(undefined, {maximumFractionDigits: 1})} days</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Total Views</span>
                    <span className="font-bold">{(watchData.january?.totalViews || 0).toLocaleString()}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Watch Time Insights */}
          {watchTimeData.insights && watchTimeData.insights.length > 0 && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
              <div className="text-sm font-semibold text-gray-700 mb-2">Insights</div>
              <ul className="space-y-1">
                {watchTimeData.insights.map((insight, i) => (
                  <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                    <span className="text-green-500">•</span>
                    <span>{insight}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Deep Dive Analysis */}
      {deepDiveData && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <span>🔍</span> Deep Dive Analysis
          </h2>

          {/* Weekly Engagement Trend */}
          {deepDiveData.weeklyTrend && deepDiveData.weeklyTrend.length > 0 && (
            <div className="mb-6">
              <h3 className="font-semibold text-gray-700 mb-3">Weekly Engagement Trend</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-3 py-2 text-left">Week</th>
                      <th className="px-3 py-2 text-right">Posts</th>
                      <th className="px-3 py-2 text-right">Avg Eng</th>
                      <th className="px-3 py-2 text-right">Total Eng</th>
                      <th className="px-3 py-2 text-right">Max</th>
                      <th className="px-3 py-2 text-right">WoW</th>
                    </tr>
                  </thead>
                  <tbody>
                    {deepDiveData.weeklyTrend.map((week, i) => (
                      <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        <td className="px-3 py-2 font-medium">{week.week}</td>
                        <td className="px-3 py-2 text-right">{week.posts}</td>
                        <td className="px-3 py-2 text-right">{(week.avgEngagement || 0).toLocaleString()}</td>
                        <td className="px-3 py-2 text-right">{(week.totalEngagement || 0).toLocaleString()}</td>
                        <td className="px-3 py-2 text-right">{(week.maxEngagement || 0).toLocaleString()}</td>
                        <td className={`px-3 py-2 text-right font-medium ${
                          week.wowChange > 0 ? 'text-green-600' :
                          week.wowChange < 0 ? 'text-red-600' : 'text-gray-500'
                        }`}>
                          {week.wowChange !== null ? `${week.wowChange >= 0 ? '+' : ''}${week.wowChange}%` : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Viral Posts */}
          {deepDiveData.viralPosts && deepDiveData.viralPosts.length > 0 && (
            <div className="mb-6">
              <h3 className="font-semibold text-gray-700 mb-3">Top Performing Posts</h3>
              <div className="space-y-2">
                {deepDiveData.viralPosts.slice(0, 5).map((post, i) => (
                  <a
                    key={i}
                    href={post.permalink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`block p-3 rounded-lg hover:shadow-md transition-shadow cursor-pointer ${i === 0 ? 'bg-yellow-50 border border-yellow-200 hover:bg-yellow-100' : 'bg-gray-50 hover:bg-gray-100'}`}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          {i === 0 && <span className="text-yellow-500">🏆</span>}
                          <span className="text-xs text-gray-500">{post.date}</span>
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            post.postType === 'Videos' ? 'bg-purple-100 text-purple-700' :
                            post.postType === 'Photos' ? 'bg-blue-100 text-blue-700' :
                            post.postType === 'Live' ? 'bg-red-100 text-red-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>{post.postType}</span>
                          <span className="text-xs text-blue-500 hover:underline">View Post</span>
                        </div>
                        <div className="text-sm font-medium text-gray-800 truncate">{post.title || 'No title'}</div>
                      </div>
                      <div className="text-right ml-4">
                        <div className="text-lg font-bold text-blue-600">{(post.engagement || 0).toLocaleString()}</div>
                        <div className="text-xs text-gray-500">{(post.views || 0).toLocaleString()} views</div>
                      </div>
                    </div>
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Post Type Comparison */}
          {deepDiveData.postTypeComparison && deepDiveData.postTypeComparison.length > 0 && (
            <div className="mb-6">
              <h3 className="font-semibold text-gray-700 mb-3">Post Type: Dec vs Jan</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-3 py-2 text-left">Type</th>
                      <th className="px-3 py-2 text-right">Dec Posts</th>
                      <th className="px-3 py-2 text-right">Dec Avg</th>
                      <th className="px-3 py-2 text-right">Jan Posts</th>
                      <th className="px-3 py-2 text-right">Jan Avg</th>
                      <th className="px-3 py-2 text-right">Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {deepDiveData.postTypeComparison.map((pt, i) => (
                      <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        <td className="px-3 py-2 font-medium">{pt.type}</td>
                        <td className="px-3 py-2 text-right">{pt.decPosts}</td>
                        <td className="px-3 py-2 text-right">{(pt.decAvg || 0).toLocaleString()}</td>
                        <td className="px-3 py-2 text-right">{pt.janPosts}</td>
                        <td className="px-3 py-2 text-right">{(pt.janAvg || 0).toLocaleString()}</td>
                        <td className={`px-3 py-2 text-right font-medium ${
                          pt.change > 0 ? 'text-green-600' : pt.change < 0 ? 'text-red-600' : 'text-gray-500'
                        }`}>
                          {pt.change >= 0 ? '+' : ''}{pt.change}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* CTA Analysis */}
          {deepDiveData.ctaAnalysis && (
            <div className="mb-6">
              <h3 className="font-semibold text-gray-700 mb-3">Call-to-Action Usage (Dec vs Jan)</h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {['comment', 'share', 'react', 'giveaway', 'question'].map(cta => {
                  const dec = deepDiveData.ctaAnalysis.december?.[cta] || {};
                  const jan = deepDiveData.ctaAnalysis.january?.[cta] || {};
                  const change = dec.percentage && jan.percentage
                    ? (jan.percentage - dec.percentage).toFixed(1)
                    : null;
                  return (
                    <div key={cta} className="bg-gray-50 rounded-lg p-3">
                      <div className="text-xs text-gray-500 capitalize mb-1">{cta}</div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Dec: {dec.percentage || 0}%</span>
                        <span className="text-gray-600">Jan: {jan.percentage || 0}%</span>
                      </div>
                      {change !== null && (
                        <div className={`text-xs mt-1 font-medium ${
                          parseFloat(change) > 0 ? 'text-green-600' : parseFloat(change) < 0 ? 'text-red-600' : 'text-gray-500'
                        }`}>
                          {parseFloat(change) >= 0 ? '+' : ''}{change}%
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Key Insights */}
          {deepDiveData.insights && deepDiveData.insights.length > 0 && (
            <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="text-sm font-semibold text-blue-800 mb-3">Key Insights & Recommendations</div>
              <div className="space-y-3">
                {deepDiveData.insights.map((insight, i) => {
                  const getEmoji = () => {
                    if (insight.type === 'viral') return '🔥';
                    if (insight.type === 'cta') return insight.title.includes('Increased') ? '📈' : '📉';
                    if (insight.type === 'content') return insight.title.includes('Improved') ? '📈' : '📉';
                    if (insight.type === 'recommendation') return '💡';
                    return '📊';
                  };
                  return (
                    <div key={i} className="flex items-start gap-3">
                      <span className="text-lg">{getEmoji()}</span>
                      <div>
                        <div className="font-medium text-gray-800">{insight.title}</div>
                        <div className="text-sm text-gray-600">{insight.detail}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Health Score Explanation */}
      <div className="bg-gray-50 rounded-lg shadow p-4">
        <div className="flex items-start gap-3">
          <span className="text-xl">ℹ️</span>
          <div>
            <div className="font-semibold text-gray-800 mb-1">How Health Score is Calculated</div>
            <div className="text-sm text-gray-600 space-y-1">
              <p>Health Score starts at 100 and is reduced based on:</p>
              <ul className="list-disc list-inside ml-2 text-xs">
                <li><strong>-30 points</strong> if Week-over-Week change is below -20%</li>
                <li><strong>-30 points</strong> if current performance is 50%+ below peak</li>
                <li><strong>-20 points</strong> if posting less than 5 posts per week</li>
              </ul>
              <p className="mt-2">
                <span className="text-green-600 font-medium">Healthy (75-100)</span> |
                <span className="text-yellow-600 font-medium ml-2">Warning (50-74)</span> |
                <span className="text-red-600 font-medium ml-2">Critical (0-49)</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Link to Other Report */}
      <div className="bg-white rounded-lg shadow p-4">
        <Link
          to={otherGroupPath}
          className={`flex items-center justify-between p-4 rounded-lg border-2 border-gray-200 hover:border-${isJuan365 ? 'red' : 'blue'}-300 transition-colors`}
        >
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-full bg-${isJuan365 ? 'red' : 'blue'}-100 flex items-center justify-center`}>
              <span className="text-xl">{isJuan365 ? '🔴' : '📊'}</span>
            </div>
            <div>
              <div className="font-semibold">View {otherGroupName} Report</div>
              <div className="text-sm text-gray-500">Switch to {otherGroupName} analytics</div>
            </div>
          </div>
          <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </Link>
      </div>
    </div>
  );
}
