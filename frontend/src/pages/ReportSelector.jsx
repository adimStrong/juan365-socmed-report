import { Link } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { getAnalytics } from '../services/api';

export default function ReportSelector() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAnalytics().then(d => {
      setData(d);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex justify-center items-center h-64">Loading...</div>;
  }

  const pageGroupHealth = data?.pageGroupHealth || {};
  const juan365 = pageGroupHealth.juan365 || {};
  const liveStream = pageGroupHealth.liveStream || {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold text-gray-900">Analytics Reports</h1>
        <p className="text-gray-500 mt-1">Select a page group to view detailed analytics (Dec 2025 - Jan 2026)</p>
      </div>

      {/* Report Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Juan365 Report Card */}
        <Link to="/report/juan365" className="block">
          <div className={`rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-shadow border-2 ${
            juan365.health?.status === 'healthy' ? 'border-green-300' :
            juan365.health?.status === 'warning' ? 'border-yellow-300' : 'border-red-300'
          }`}>
            <div className={`p-6 text-white ${
              juan365.health?.status === 'healthy' ? 'bg-gradient-to-r from-green-500 to-emerald-500' :
              juan365.health?.status === 'warning' ? 'bg-gradient-to-r from-yellow-500 to-amber-500' : 'bg-gradient-to-r from-red-500 to-orange-500'
            }`}>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center">
                  <span className="text-2xl">📊</span>
                </div>
                <div>
                  <h2 className="text-2xl font-bold">Juan365</h2>
                  <p className="text-sm opacity-80">Main Page Report</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white/20 rounded-lg p-3">
                  <div className="text-xs opacity-80">Health Score</div>
                  <div className="text-2xl font-bold">{juan365.health?.score?.toFixed(0) || 0}/100</div>
                  <div className="text-sm capitalize">{juan365.health?.status || 'N/A'}</div>
                </div>
                <div className="bg-white/20 rounded-lg p-3">
                  <div className="text-xs opacity-80">WoW Change</div>
                  <div className="text-2xl font-bold">
                    {juan365.health?.wowChange >= 0 ? '+' : ''}{juan365.health?.wowChange?.toFixed(1) || 0}%
                  </div>
                  <div className="text-sm">Week over Week</div>
                </div>
              </div>
            </div>
            <div className="bg-white p-4">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="text-2xl font-bold text-blue-600">{juan365.overall?.totalPosts || 0}</div>
                  <div className="text-xs text-gray-500">Total Posts</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-blue-600">{juan365.overall?.avgEngagement?.toFixed(0) || 0}</div>
                  <div className="text-xs text-gray-500">Avg Engagement</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-blue-600">{(juan365.overall?.totalEngagement || 0).toLocaleString()}</div>
                  <div className="text-xs text-gray-500">Total Engagement</div>
                </div>
              </div>
              <div className="mt-4 text-center">
                <span className="inline-flex items-center gap-2 text-blue-600 font-medium">
                  View Full Report
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </span>
              </div>
            </div>
          </div>
        </Link>

        {/* Live Stream Report Card */}
        <Link to="/report/livestream" className="block">
          <div className={`rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-shadow border-2 ${
            liveStream.health?.status === 'healthy' ? 'border-green-300' :
            liveStream.health?.status === 'warning' ? 'border-yellow-300' : 'border-red-300'
          }`}>
            <div className={`p-6 text-white ${
              liveStream.health?.status === 'healthy' ? 'bg-gradient-to-r from-green-500 to-emerald-500' :
              liveStream.health?.status === 'warning' ? 'bg-gradient-to-r from-yellow-500 to-amber-500' : 'bg-gradient-to-r from-red-500 to-orange-500'
            }`}>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center">
                  <span className="text-2xl">🔴</span>
                </div>
                <div>
                  <h2 className="text-2xl font-bold">Live Stream</h2>
                  <p className="text-sm opacity-80">Live Content Report</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white/20 rounded-lg p-3">
                  <div className="text-xs opacity-80">Health Score</div>
                  <div className="text-2xl font-bold">{liveStream.health?.score?.toFixed(0) || 0}/100</div>
                  <div className="text-sm capitalize">{liveStream.health?.status || 'N/A'}</div>
                </div>
                <div className="bg-white/20 rounded-lg p-3">
                  <div className="text-xs opacity-80">WoW Change</div>
                  <div className="text-2xl font-bold">
                    {liveStream.health?.wowChange >= 0 ? '+' : ''}{liveStream.health?.wowChange?.toFixed(1) || 0}%
                  </div>
                  <div className="text-sm">Week over Week</div>
                </div>
              </div>
            </div>
            <div className="bg-white p-4">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="text-2xl font-bold text-red-600">{liveStream.overall?.totalPosts || 0}</div>
                  <div className="text-xs text-gray-500">Total Posts</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-red-600">{liveStream.overall?.avgEngagement?.toFixed(0) || 0}</div>
                  <div className="text-xs text-gray-500">Avg Engagement</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-red-600">{(liveStream.overall?.totalEngagement || 0).toLocaleString()}</div>
                  <div className="text-xs text-gray-500">Total Engagement</div>
                </div>
              </div>
              <div className="mt-4 text-center">
                <span className="inline-flex items-center gap-2 text-red-600 font-medium">
                  View Full Report
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </span>
              </div>
            </div>
          </div>
        </Link>
      </div>

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
    </div>
  );
}
