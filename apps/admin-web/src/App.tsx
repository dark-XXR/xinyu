/**
 * 应用根组件。
 * 提供 BrowserRouter 路由和页面布局。
 */
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Providers } from './pages/Providers'
import { Products } from './pages/commerce/Products'
import { Orders } from './pages/commerce/Orders'

function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="providers" element={<Providers />} />
          <Route path="commerce/products" element={<Products />} />
          <Route path="commerce/orders" element={<Orders />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
