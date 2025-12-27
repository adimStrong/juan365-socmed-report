import { useState, useEffect } from 'react';
import { getPosts, getPages } from '../services/api';

export default function Posts() {
  const [posts, setPosts] = useState([]);
  const [pages, setPages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [filter, setFilter] = useState({ post_type: '', page_id: '', search: '' });
  const [searchInput, setSearchInput] = useState('');

  // Load pages for filter dropdown
  useEffect(() => {
    async function fetchPages() {
      const pageData = await getPages();
      setPages(pageData);
    }
    fetchPages();
  }, []);

  useEffect(() => {
    async function fetchPosts() {
      setLoading(true);
      try {
        const params = { page };
        if (filter.post_type) params.post_type = filter.post_type;
        if (filter.page_id) params.page_id = filter.page_id;
        if (filter.search) params.search = filter.search;
        const data = await getPosts(params);
        setPosts(data.results || data);
        setTotalCount(data.count || 0);
        setHasNext(!!data.next);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchPosts();
  }, [page, filter]);

  const formatDate = (date) => {
    if (!date) return 'N/A';
    return new Date(date).toLocaleDateString();
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    setFilter(f => ({ ...f, search: searchInput }));
  };

  const handleFilterChange = (key, value) => {
    setPage(1);
    setFilter(f => ({ ...f, [key]: value }));
  };

  const pageSize = 20;
  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">All Posts</h1>
          <p className="text-sm text-gray-500">
            Showing {posts.length} of {totalCount.toLocaleString()} posts
          </p>
        </div>

        {/* Filters Row */}
        <div className="flex flex-wrap gap-3">
          {/* Search */}
          <form onSubmit={handleSearch} className="flex">
            <input
              type="text"
              placeholder="Search posts..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="border rounded-l-lg px-4 py-2 w-48 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
            <button
              type="submit"
              className="bg-indigo-600 text-white px-4 py-2 rounded-r-lg hover:bg-indigo-700"
            >
              Search
            </button>
          </form>

          {/* Page Filter */}
          <select
            className="border rounded-lg px-4 py-2 bg-white"
            value={filter.page_id}
            onChange={(e) => handleFilterChange('page_id', e.target.value)}
          >
            <option value="">All Pages</option>
            {pages.map((p) => (
              <option key={p.page_id} value={p.page_id}>
                {p.page_name?.replace('Juana Babe ', '')}
              </option>
            ))}
          </select>

          {/* Type Filter */}
          <select
            className="border rounded-lg px-4 py-2 bg-white"
            value={filter.post_type}
            onChange={(e) => handleFilterChange('post_type', e.target.value)}
          >
            <option value="">All Types</option>
            <option value="Photos">Photos</option>
            <option value="Videos">Videos</option>
            <option value="Reels">Reels</option>
            <option value="Live">Live</option>
            <option value="Text">Text</option>
          </select>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          </div>
        ) : posts.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No posts found matching your criteria
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[900px]">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Page</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Title</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Type</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Date</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-500">Reactions</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-500">Comments</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-500">Shares</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-500">Views</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-500">Engagement</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {posts.map((post) => (
                  <tr key={post.post_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-xs text-gray-600 whitespace-nowrap">
                      {post.page_name?.replace('Juana Babe ', '')}
                    </td>
                    <td className="px-4 py-3 max-w-xs">
                      <a
                        href={post.permalink}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-indigo-600 hover:underline truncate block"
                        title={post.title}
                      >
                        {post.title?.slice(0, 50) || 'Untitled'}
                        {post.title?.length > 50 ? '...' : ''}
                      </a>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs ${
                        post.post_type === 'Reels' ? 'bg-purple-100 text-purple-800' :
                        post.post_type === 'Videos' ? 'bg-blue-100 text-blue-800' :
                        post.post_type === 'Live' ? 'bg-red-100 text-red-800' :
                        post.post_type === 'Photos' ? 'bg-green-100 text-green-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {post.post_type || 'Unknown'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                      {formatDate(post.publish_time)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {post.reactions?.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {post.comments?.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {post.shares?.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right text-purple-600">
                      {post.views?.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right font-semibold text-indigo-600">
                      {post.engagement?.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex justify-between items-center">
        <div className="text-sm text-gray-500">
          Page {page} of {totalPages || 1}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 border rounded-lg disabled:opacity-50 hover:bg-gray-50"
          >
            Previous
          </button>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={!hasNext}
            className="px-4 py-2 border rounded-lg disabled:opacity-50 hover:bg-gray-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
