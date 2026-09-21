import {
  BarChart3,
  Boxes,
  CreditCard,
  FileText,
  LayoutDashboard,
  PackageCheck,
  ReceiptText,
  RotateCcw,
  ShoppingBag,
  Truck,
  Users,
  Warehouse,
} from 'lucide-react'

export const navigationItems = [
  { label: 'Dashboard', path: '/', icon: LayoutDashboard },
  { label: 'Products', path: '/products', icon: Boxes },
  { label: 'Customers', path: '/customers', icon: Users },
  { label: 'Suppliers', path: '/suppliers', icon: Warehouse },
  { label: 'Purchases', path: '/purchases', icon: ShoppingBag },
  { label: 'Orders', path: '/orders', icon: PackageCheck },
  { label: 'Invoices', path: '/invoices', icon: FileText },
  { label: 'Deliveries', path: '/deliveries', icon: Truck },
  { label: 'Payments', path: '/payments', icon: CreditCard },
  { label: 'Returns', path: '/returns', icon: RotateCcw },
  { label: 'Reports', path: '/reports', icon: BarChart3 },
]

export function getPageTitle(pathname) {
  return navigationItems.find((item) => item.path === pathname)?.label || 'DukaanPulse'
}
