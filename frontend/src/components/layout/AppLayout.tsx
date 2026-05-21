import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuthStore } from "../../store";
import { BookOpen, LogOut, Map, Code, BarChart3, Network } from "lucide-react";

export default function AppLayout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="app-layout">
      <header className="app-header">
        <div className="header-left">
          <BookOpen size={24} />
          <span className="app-title">CodePilgrim</span>
        </div>
        <nav className="header-nav">
          <NavLink to="/learn" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
            <Code size={18} /> 学习
          </NavLink>
          <NavLink to="/path" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
            <Map size={18} /> 路径
          </NavLink>
          <NavLink to="/graph" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
            <Network size={18} /> 图谱
          </NavLink>
          <NavLink to="/dashboard" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
            <BarChart3 size={18} /> 仪表盘
          </NavLink>
        </nav>
        <div className="header-right">
          <span className="user-name">{user?.display_name || user?.username}</span>
          <button onClick={handleLogout} className="btn-logout" title="退出">
            <LogOut size={18} />
          </button>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
