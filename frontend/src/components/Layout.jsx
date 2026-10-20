import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Package,
  Users,
  Truck,
  ShoppingCart,
  ClipboardList,
  FileText,
  BikeIcon,
  Wallet,
  Landmark,
  RotateCcw,
  Boxes,
  UserCog,
  KeyRound,
  LogOut,
} from "lucide-react";
import ErrorBoundary from "./ErrorBoundary";
import { useAuth } from "../auth/AuthProvider";
import ChangePasswordModal from "./ChangePasswordModal";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true, requiredPermissions: ["dashboard:read"] },
  { to: "/products", label: "Products", icon: Package, requiredPermissions: ["products:read", "categories:read"] },
  { to: "/customers", label: "Customers", icon: Users, requiredPermissions: ["customers:read"] },
  { to: "/suppliers", label: "Suppliers", icon: Truck, requiredPermissions: ["suppliers:read"] },
  { to: "/purchases", label: "Purchases", icon: ShoppingCart, requiredPermissions: ["purchases:read", "suppliers:read", "products:read"] },
  { to: "/orders", label: "Orders", icon: ClipboardList, requiredPermissions: ["orders:read", "customers:read", "products:read"] },
  { to: "/invoices", label: "Invoices", icon: FileText, requiredPermissions: ["invoices:read", "orders:read"] },
  { to: "/deliveries", label: "Deliveries", icon: BikeIcon, requiredPermissions: ["deliveries:read", "invoices:read"] },
  { to: "/payments", label: "Customer payments", icon: Wallet, requiredPermissions: ["payments:read", "invoices:read"] },
  { to: "/purchase-payments", label: "Supplier payments", icon: Landmark, requiredPermissions: ["purchase_payments:read", "purchases:read"] },
  { to: "/returns", label: "Returns", icon: RotateCcw, requiredPermissions: ["returns:read", "invoices:read"] },
  { to: "/inventory", label: "Stock lookup", icon: Boxes, requiredPermissions: ["inventory:read", "products:read"] },
  { to: "/users", label: "Users", icon: UserCog, requiredPermissions: ["users:manage"] },
];

export default function Layout() {
  const location = useLocation();
  const { user, logout, can } = useAuth();
  const [showChangePassword, setShowChangePassword] = useState(false);
  const currentPage = links.find(({ to, end }) => (
    end
      ? location.pathname === to
      : location.pathname === to || location.pathname.startsWith(`${to}/`)
  ));
  const canAccessCurrentPage = !currentPage
    || currentPage.requiredPermissions.every(can);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          Dukaan<span>Pulse</span>
        </div>
        {links
          .filter(({ requiredPermissions }) => requiredPermissions.every(can))
          .map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
          >
            <Icon size={16} />
            {label}
          </NavLink>
          ))}
        <div className="sidebar-user">
          <div className="sidebar-user-name">{user.full_name}</div>
          <div className="sidebar-user-role">{user.role}</div>
          <button className="sidebar-logout" type="button" onClick={() => setShowChangePassword(true)}>
            <KeyRound size={16} />
            Change password
          </button>
          <button className="sidebar-logout" type="button" onClick={logout}>
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </aside>
      <main className="main">
        {/* Keyed by path: if a page crashes, the sidebar still works and
            navigating to another page starts the boundary fresh. */}
        <ErrorBoundary key={location.pathname}>
          {canAccessCurrentPage ? (
            <Outlet />
          ) : (
            <section className="panel">
              <h1>Access denied</h1>
              <p>You don't have access to this page.</p>
            </section>
          )}
        </ErrorBoundary>
      </main>
      {showChangePassword && <ChangePasswordModal onClose={() => setShowChangePassword(false)} />}
    </div>
  );
}