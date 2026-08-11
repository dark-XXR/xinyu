/**
 * 应用根组件。
 * 提供 BrowserRouter 路由、Suspense 与全站核心运营页面动态按需加载。
 */
import { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';

const Dashboard = lazy(() => import('./pages/Dashboard').then((m) => ({ default: m.Dashboard })));
const Providers = lazy(() => import('./pages/Providers').then((m) => ({ default: m.Providers })));
const Products = lazy(() =>
  import('./pages/commerce/Products').then((m) => ({ default: m.Products }))
);
const Orders = lazy(() => import('./pages/commerce/Orders').then((m) => ({ default: m.Orders })));
const AiOperations = lazy(() =>
  import('./pages/ai/AiOperations').then((m) => ({ default: m.AiOperations }))
);
const AuditOperations = lazy(() =>
  import('./pages/audit/AuditOperations').then((m) => ({ default: m.AuditOperations }))
);
const UsersPage = lazy(() =>
  import('./pages/users/UsersPage').then((m) => ({ default: m.UsersPage }))
);
const NoticesPage = lazy(() =>
  import('./pages/operations/NoticesPage').then((m) => ({ default: m.NoticesPage }))
);
const SettingsPage = lazy(() =>
  import('./pages/system/SettingsPage').then((m) => ({ default: m.SettingsPage }))
);
const PaymentsPage = lazy(() =>
  import('./pages/commerce/PaymentsPage').then((m) => ({ default: m.PaymentsPage }))
);
const SupportPage = lazy(() =>
  import('./pages/support/SupportPage').then((m) => ({ default: m.SupportPage }))
);
const ReferralsPage = lazy(() =>
  import('./pages/referrals/ReferralsPage').then((m) => ({ default: m.ReferralsPage }))
);

function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Suspense
        fallback={
          <div
            style={{
              padding: '40px',
              textAlign: 'center',
              color: 'var(--color-text-secondary)',
              fontSize: '14px',
            }}
          >
            页面加载中...
          </div>
        }
      >
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="operations/notices" element={<NoticesPage />} />
            <Route path="support" element={<SupportPage />} />
            <Route path="commerce/products" element={<Products />} />
            <Route path="commerce/orders" element={<Orders />} />
            <Route path="commerce/payments" element={<PaymentsPage />} />
            <Route path="referrals" element={<ReferralsPage />} />
            <Route path="providers" element={<Providers />} />
            <Route path="ai" element={<AiOperations />} />
            <Route path="audit" element={<AuditOperations />} />
            <Route path="system/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;
