import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Products from "./pages/Products";
import Customers from "./pages/Customers";
import Suppliers from "./pages/Suppliers";
import Purchases from "./pages/Purchases";
import Orders from "./pages/Orders";
import Invoices from "./pages/Invoices";
import InvoiceDetail from "./pages/InvoiceDetail";
import Deliveries from "./pages/Deliveries";
import Payments from "./pages/Payments";
import PurchasePayments from "./pages/PurchasePayments";
import Returns from "./pages/Returns";
import Inventory from "./pages/Inventory";


function ComingSoon({ label }) {
  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{label}</h1>
        </div>
      </div>
      <div className="empty-state">This page hasn't been built yet.</div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="products" element={<Products />} />
          <Route path="customers" element={<Customers />} />
          <Route path="suppliers" element={<Suppliers />} />
          <Route path="purchases" element={<Purchases />} />
          <Route path="orders" element={<Orders />} />
          <Route path="invoices" element={<Invoices />} />
          <Route path="invoices/:id" element={<InvoiceDetail />} />
          <Route path="deliveries" element={<Deliveries />} />
          <Route path="payments" element={<Payments />} />
          <Route path="purchase-payments" element={<PurchasePayments />} />
          <Route path="returns" element={<Returns />} />
          <Route path="inventory" element={<Inventory />} />
          <Route path="*" element={<ComingSoon label="Not found" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}