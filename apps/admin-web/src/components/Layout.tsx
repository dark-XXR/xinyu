/**
 * 主布局组件。
 * 负责左侧导航栏、移动端汉堡菜单和右侧主内容区域渲染。
 */
import React, { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, Server, ShoppingCart, ListOrdered, Menu } from 'lucide-react';

export const Layout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const toggleSidebar = () => setSidebarOpen(!sidebarOpen);
  const closeSidebar = () => setSidebarOpen(false);

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && sidebarOpen) {
        closeSidebar();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [sidebarOpen]);

  return (
    <div className="app-container">
      {sidebarOpen && (
        <div className="overlay" style={{ zIndex: 80 }} onClick={closeSidebar} />
      )}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="brand-mark"></div>
          心语运营台 / ADMIN
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/" end onClick={closeSidebar} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <LayoutDashboard size={18} /> 工作台
          </NavLink>
          <NavLink to="/providers" onClick={closeSidebar} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Server size={18} /> 供应商配置
          </NavLink>
          <NavLink to="/commerce/products" onClick={closeSidebar} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <ShoppingCart size={18} /> 商品与套餐
          </NavLink>
          <NavLink to="/commerce/orders" onClick={closeSidebar} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <ListOrdered size={18} /> 订单管理
          </NavLink>
        </nav>
      </aside>
      <main className="main-content">
        <header className="topbar">
          <button className="menu-trigger btn-ghost" onClick={toggleSidebar} aria-label="打开菜单" aria-expanded={sidebarOpen} style={{ border: 'none', background: 'none' }}>
            <Menu size={20} />
          </button>
          <div style={{ flex: 1 }} />
          <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>admin</div>
        </header>
        <div className="page-container">
          <Outlet />
        </div>
      </main>
    </div>
  );
};
