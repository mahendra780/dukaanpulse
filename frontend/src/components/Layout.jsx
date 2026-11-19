import { useEffect, useState } from "react";
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
  BarChart3,
  Menu,
  X,
} from "lucide-react";
import ErrorBoundary from "./ErrorBoundary";
import { useAuth } from "../auth/AuthProvider";
import { useToast } from "./ToastProvider";
import ChangePasswordModal from "./ChangePasswordModal";
import Logo from "./Logo";
import UserMenu from "./UserMenu";

// Grouped by what the person is doing, not by database table.
const groups = [
  {
    label: null,
    links: [
      { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, requiredPermissions: ["dashboard:read"] },
    ],
  },
  {
    label: "Sell",
    links: [
      { to: "/customers", label: "Customers", icon: Users, requiredPermissions: ["customers:read"] },
      { to: "/orders", label: "Orders", icon: ClipboardList, requiredPermissions: ["orders:read", "customers:read", "products:read"] },
      { to: "/invoices", label: "Invoices", icon: FileText, requiredPermissions: ["invoices:read", "orders:read"] },
      { to: "/deliveries", label: "Deliveries", icon: BikeIcon, requiredPermissions: ["deliveries:read", "invoices:read"] },
      { to: "/payments", label: "Customer payments", icon: Wallet, requiredPermissions: ["payments:read", "invoices:read"] },
      { to: "/returns", label: "Returns", icon: RotateCcw, requiredPermissions: ["returns:read", "invoices:read"] },
    ],
  },
  {
    label: "Buy",
    links: [
      { to: "/suppliers", label: "Suppliers", icon: Truck, requiredPermissions: ["suppliers:read"] },
      { to: "/purchases", label: "Purchases", icon: ShoppingCart, requiredPermissions: ["purchases:read", "suppliers:read", "products:read"] },
      { to: "/purchase-payments", label: "Supplier payments", icon: Landmark, requiredPermissions: ["purchase_payments:read", "purchases:read"] },
    ],
  },
  {
    label: "Stock",
    links: [
      { to: "/products", label: "Products", icon: Package, requiredPermissions: ["products:read", "categories:read"] },
      { to: "/inventory", label: "Stock lookup", icon: Boxes, requiredPermissions: ["inventory:read", "products:read"] },
    ],
  },
  {
    label: "Insights",
    links: [
      { to: "/cash-credit", label: "Cash & Credit", icon: BarChart3, requiredPermissions: ["reports:read"] },
    ],
  },
  {
    label: "Admin",
    links: [
      { to: "/users", label: "Users", icon: UserCog, requiredPermissions: ["users:manage"] },
    ],
  },
];

const links = groups.flatMap((group) => group.links);

export default function Layout() {
  const location = useLocation();
  const { user, logout, switchWorkspace, can } = useAuth();
  const toast = useToast();
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const currentPage = links.find(({ to, end }) => (
    end
      ? location.pathname === to
      : location.pathname === to || location.pathname.startsWith(`${to}/`)
  ));
  const canAccessCurrentPage = !currentPage
    || currentPage.requiredPermissions.every(can);

  const visibleGroups = groups
    .map((group) => ({
      ...group,
      links: group.links.filter(({ requiredPermissions }) => requiredPermissions.every(can)),
    }))
    .filter((group) => group.links.length > 0);

  // On a phone the sidebar is a drawer: close it after navigating, and on Escape.
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onKeyDown = (event) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [menuOpen]);

  const changeWorkspace = async (workspaceId) => {
    if (workspaceId === user.workspace?.workspace_id) return;
    try {
      await switchWorkspace(workspaceId);
    } catch {
      toast.error("Unable to switch workspace. Please try again.");
    }
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <button
          className="topbar-menu"
          type="button"
          aria-label="Open menu"
          aria-expanded={menuOpen}
          aria-controls="sidebar"
          onClick={() => setMenuOpen(true)}
        >
          <Menu size={20} />
        </button>
        <Logo onDark />
      </header>

      {menuOpen && <div className="sidebar-backdrop" onClick={() => setMenuOpen(false)} />}

      <aside id="sidebar" className={"sidebar" + (menuOpen ? " open" : "")}>
        <div className="sidebar-top">
          <div className="sidebar-brand">
            <Logo onDark />
          </div>
          <button
            className="sidebar-close"
            type="button"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        <nav className="sidebar-nav" aria-label="Main">
          {visibleGroups.map((group) => (
            <div className="nav-group" key={group.label || "overview"}>
              {group.label && <div className="nav-group-label">{group.label}</div>}
              {group.links.map(({ to, label, icon: Icon, end }) => (
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
            </div>
          ))}
        </nav>

        <div className="sidebar-user">
          <UserMenu
            user={user}
            onChangePassword={() => setShowChangePassword(true)}
            onLogout={logout}
            onSwitchWorkspace={changeWorkspace}
          />
        </div>
      </aside>

      <main className="main">
        {/* Keyed by path: if a page crashes, the sidebar still works and
            navigating to another page starts the boundary fresh. */}
        <ErrorBoundary key={location.pathname}>
          <div className="page-enter">
            {canAccessCurrentPage ? (
              <Outlet />
            ) : (
              <section className="panel">
                <h1>Access denied</h1>
                <p>You don't have access to this page.</p>
              </section>
            )}
          </div>
        </ErrorBoundary>
      </main>
      {showChangePassword && <ChangePasswordModal onClose={() => setShowChangePassword(false)} />}
    </div>
  );
}