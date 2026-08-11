/**
 * 主布局组件。
 * 负责动态品牌名读取、侧边栏三大分组导航、移动端响应式与右侧主内容区域渲染。
 */
import React, { useState, useEffect } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  Megaphone,
  LifeBuoy,
  ShoppingCart,
  ListOrdered,
  CreditCard,
  UserPlus,
  Server,
  Cpu,
  ShieldCheck,
  Settings,
  Menu,
} from 'lucide-react';
import { repository } from '../api/repository';

export const Layout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [brandName, setBrandName] = useState<string>('运营管理台');

  const toggleSidebar = () => setSidebarOpen(!sidebarOpen);
  const closeSidebar = () => setSidebarOpen(false);

  useEffect(() => {
    let active = true;
    repository
      .getAdminSystemConfig()
      .then((cfg) => {
        if (!active) return;
        const name =
          cfg.publishedConfig?.appName ||
          cfg.publishedConfig?.websiteName ||
          cfg.draftConfig?.appName ||
          cfg.draftConfig?.websiteName;
        if (name) {
          setBrandName(name);
        }
      })
      .catch(() => {
        // 读取异常时降级使用运营管理台占位
        if (active) setBrandName('运营管理台');
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && sidebarOpen) {
        closeSidebar();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [sidebarOpen]);

  return (
    <div className="app-container" style={{ overflowX: 'hidden' }}>
      {sidebarOpen && (
        <div className="overlay" style={{ zIndex: 80 }} onClick={closeSidebar} />
      )}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="brand-mark" />
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {brandName}
          </span>
        </div>
        <nav className="sidebar-nav">
          <div className="nav-group">
            <div className="nav-group-title">平台运营</div>
            <NavLink to="/" end onClick={closeSidebar} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <LayoutDashboard size={18} /> 工作台
            </NavLink>
            <NavLink to="/users" onClick={closeSidebar} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <Users size={18} /> 用户管理
            </NavLink>
            <NavLink to="/operations/notices" onClick={closeSidebar} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <Megaphone size={18} /> 公告运营
            </NavLink>
            <NavLink to="/support" onClick={closeSidebar} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <LifeBuoy size={18} /> 客服工单
            </NavLink>
          </div>

          <div className="nav-group">
            <div className="nav-group-title">商业运营</div>
            <NavLink to="/commerce/products" onClick={closeSidebar} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <ShoppingCart size={18} /> 商品与套餐
            </NavLink>
            <NavLink to="/commerce/orders" onClick={closeSidebar} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <ListOrdered size={18} /> 订单管理
            </NavLink>
            <NavLink to="/commerce/payments" onClick={closeSidebar} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <CreditCard size={18} /> 支付运营
            </NavLink>
            <NavLink to="/referrals" onClick={closeSidebar} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <UserPlus size={18} /> 邀请推广
            </NavLink>
          </div>

          <div className="nav-group">
            <div className="nav-group-title">技术与合规</div>
            <NavLink to="/providers" onClick={closeSidebar} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <Server size={18} /> 供应商配置
            </NavLink>
            <NavLink to="/ai" onClick={closeSidebar} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <Cpu size={18} /> AI 运行配置
            </NavLink>
            <NavLink to="/audit" onClick={closeSidebar} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <ShieldCheck size={18} /> 合规审计
            </NavLink>
            <NavLink to="/system/settings" onClick={closeSidebar} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <Settings size={18} /> 网站设置
            </NavLink>
          </div>
        </nav>
      </aside>
      <main className="main-content" style={{ maxWidth: '100vw', overflowX: 'hidden' }}>
        <header className="topbar">
          <button
            className="menu-trigger btn-ghost"
            onClick={toggleSidebar}
            aria-label="打开菜单"
            aria-expanded={sidebarOpen}
            style={{ border: 'none', background: 'none' }}
          >
            <Menu size={20} />
          </button>
          <div style={{ flex: 1, fontWeight: 500, color: 'var(--color-text-secondary)', fontSize: '13px' }}>
            {brandName}
          </div>
          <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>admin</div>
        </header>
        <div className="page-container" style={{ width: '100%', overflowX: 'hidden' }}>
          <Outlet />
        </div>
      </main>
    </div>
  );
};
