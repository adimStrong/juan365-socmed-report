import { NavLink, Outlet } from 'react-router-dom';

const navItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/posts', label: 'Posts', icon: '📝' },
  { path: '/pages', label: 'Pages', icon: '📄' },
  { path: '/comments', label: 'Comments', icon: '💬' },
  { path: '/overlap', label: 'Comparison', icon: '📈' },
];

export default function Layout() {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 bg-indigo-900 text-white">
        <div className="p-6">
          <h1 className="text-xl font-bold">Socmed Report</h1>
          <p className="text-indigo-300 text-sm">Juan365 Analytics</p>
        </div>
        <nav className="mt-4">
          {navItems.map(({ path, label, icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) =>
                `flex items-center px-6 py-3 text-sm transition-colors ${
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
      <main className="flex-1 p-8 bg-gray-50 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
