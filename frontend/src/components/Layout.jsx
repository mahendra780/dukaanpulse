import { NavLink, Outlet } from "react-router-dom";
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
} from "lucide-react";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/products", label: "Products", icon: Package },
  { to: "/customers", label: "Customers", icon: Users },
  { to: "/suppliers", label: "Suppliers", icon: Truck },
  { to: "/purchases", label: "Purchases", icon: ShoppingCart },
  { to: "/orders", label: "Orders", icon: ClipboardList },
  { to: "/invoices", label: "Invoices", icon: FileText },
  { to: "/deliveries", label: "Deliveries", icon: BikeIcon },
  { to: "/payments", label: "Customer payments", icon: Wallet },
  { to: "/purchase-payments", label: "Supplier payments", icon: Landmark },
  { to: "/returns", label: "Returns", icon: RotateCcw },
  { to: "/inventory", label: "Stock lookup", icon: Boxes },
];

export default function Layout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          Dukaan<span>Pulse</span>
        </div>
        {links.map(({ to, label, icon: Icon, end }) => (
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
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}