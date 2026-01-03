import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';

const navItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/posts', label: 'Posts', icon: '📝' },
  { path: '/pages', label: 'Pages', icon: '📄' },
  // { path: '/comments', label: 'Comments', icon: '💬' }, // Disabled temporarily
  { path: '/overlap', label: 'Comparison', icon: '📈' },
];

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex min-h-screen">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 z-40 w-64 bg-indigo-900 text-white
        transform transition-transform duration-200 ease-in-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        md:relative md:translate-x-0
      `}>
        <div className="p-4 flex items-center gap-3">
          <img src="/logo.jpg" alt="Juan365 Logo" className="w-10 h-10 rounded-full object-cover" />
          <div>
            <h1 className="text-lg font-bold">Socmed Report</h1>
            <p className="text-indigo-300 text-xs">Juan365 Analytics</p>
          </div>
          {/* Close button on mobile */}
          <button
            className="ml-auto md:hidden p-1 hover:bg-indigo-800 rounded"
            onClick={() => setSidebarOpen(false)}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <nav className="mt-2">
          {navItems.map(({ path, label, icon }) => (
            <NavLink
              key={path}
              to={path}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center px-4 py-3 text-sm transition-colors ${
                  isActive
                    ? 'bg-indigo-800 border-r-4 border-indigo-400'
                    : 'hover:bg-indigo-800'
                }`
              }
            >
              <span className="mr-3">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-h-screen md:ml-0">
        {/* Mobile header */}
        <header className="md:hidden bg-indigo-900 text-white p-3 flex items-center gap-3 sticky top-0 z-20">
          <button
            className="p-1.5 hover:bg-indigo-800 rounded"
            onClick={() => setSidebarOpen(true)}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <img src="/logo.jpg" alt="Logo" className="w-8 h-8 rounded-full object-cover" />
          <span className="font-semibold">Socmed Report</span>
        </header>

        <main className="flex-1 p-4 md:p-8 bg-gray-50 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
