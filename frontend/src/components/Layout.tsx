import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../auth";

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>Finance</h1>
        <nav>
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/transactions">Transactions</NavLink>
          <NavLink to="/import">Import CSV</NavLink>
          <NavLink to="/rules">Rules</NavLink>
          <NavLink to="/budgets">Budgets</NavLink>
        </nav>
        <div className="user-box">
          <div className="email">{user?.email}</div>
          <button className="secondary" onClick={logout} style={{ width: "100%" }}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
