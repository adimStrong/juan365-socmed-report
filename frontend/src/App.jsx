import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Posts from './pages/Posts';
import Pages from './pages/Pages';
import Comments from './pages/Comments';
import Imports from './pages/Imports';
import Overlap from './pages/Overlap';
import AnalyticsReport from './pages/AnalyticsReport';
import ReportSelector from './pages/ReportSelector';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="posts" element={<Posts />} />
          <Route path="pages" element={<Pages />} />
          <Route path="comments" element={<Comments />} />
          <Route path="imports" element={<Imports />} />
          <Route path="overlap" element={<Overlap />} />
          <Route path="report" element={<ReportSelector />} />
          <Route path="report/juan365" element={<AnalyticsReport pageGroup="juan365" />} />
          <Route path="report/livestream" element={<AnalyticsReport pageGroup="liveStream" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
