import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import ReviewDetail from './pages/ReviewDetail'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="review/:id" element={<ReviewDetail />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
