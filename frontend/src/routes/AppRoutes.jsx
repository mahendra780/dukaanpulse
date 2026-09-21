import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from '../components/layout/Layout'
import Customers from '../pages/Customers/Customers'
import Dashboard from '../pages/Dashboard/Dashboard'
import Deliveries from '../pages/Deliveries/Deliveries'
import Invoices from '../pages/Invoices/Invoices'
import Orders from '../pages/Orders/Orders'
import Payments from '../pages/Payments/Payments'
import Products from '../pages/Products/Products'
import Purchases from '../pages/Purchases/Purchases'
import Reports from '../pages/Reports/Reports'
import Returns from '../pages/Returns/Returns'
import Suppliers from '../pages/Suppliers/Suppliers'

function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="products" element={<Products />} />
        <Route path="customers" element={<Customers />} />
        <Route path="suppliers" element={<Suppliers />} />
        <Route path="purchases" element={<Purchases />} />
        <Route path="orders" element={<Orders />} />
        <Route path="invoices" element={<Invoices />} />
        <Route path="deliveries" element={<Deliveries />} />
        <Route path="payments" element={<Payments />} />
        <Route path="returns" element={<Returns />} />
        <Route path="reports" element={<Reports />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default AppRoutes
