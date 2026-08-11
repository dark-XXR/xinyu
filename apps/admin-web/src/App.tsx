/**
 * 应用根组件。
 * 提供 BrowserRouter 路由和全站核心运营页面配置。
 */
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Providers } from './pages/Providers'
import { Products } from './pages/commerce/Products'
import { Orders } from './pages/commerce/Orders'
import { AiOperations } from './pages/ai/AiOperations'
import { AuditOperations } from './pages/audit/AuditOperations'
import { UsersPage } from './pages/users/UsersPage'
import { NoticesPage } from './pages/operations/NoticesPage'
import { SettingsPage } from './pages/system/SettingsPage'
import { PaymentsPage } from './pages/commerce/PaymentsPage'
import { SupportPage } from './pages/support/SupportPage'

function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="operations/notices" element={<NoticesPage />} />
          <Route path="support" element={<SupportPage />} />
          <Route path="commerce/products" element={<Products />} />
          <Route path="commerce/orders" element={<Orders />} />
          <Route path="commerce/payments" element={<PaymentsPage />} />
          <Route path="providers" element={<Providers />} />
          <Route path="ai" element={<AiOperations />} />
          <Route path="audit" element={<AuditOperations />} />
          <Route path="system/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
