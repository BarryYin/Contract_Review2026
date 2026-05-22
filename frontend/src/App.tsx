import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import ReviewDetail from './pages/ReviewDetail'
import Dashboard from './pages/Dashboard'
import Compare from './pages/Compare'
import AuditLog from './pages/AuditLog'
import RulesManage from './pages/RulesManage'
import LatestReviewRedirect from './components/LatestReviewRedirect'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="review/latest" element={<LatestReviewRedirect />} />
          <Route path="review/:fileId" element={<ReviewDetail />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="compare" element={<Compare />} />
          <Route path="audit-log" element={<AuditLog />} />
          <Route path="rules" element={<RulesManage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
