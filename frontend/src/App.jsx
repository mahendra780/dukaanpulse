import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ToastProvider } from "./components/ToastProvider";
import { ConfirmProvider } from "./components/ConfirmProvider";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider, useAuth } from "./auth/AuthProvider";
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
import Users from "./pages/Users";
import Login from "./pages/Login";
import { Spinner } from "./components/Feedback";

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

function LoginRoute() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="auth-loading">
        <Spinner label="Checking your session…" />
      </div>
    );
  }

  return user ? <Navigate to="/" replace /> : <Login />;
}

export default function App() {
  return (
    <ToastProvider>
      <ConfirmProvider>
        <BrowserRouter>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<LoginRoute />} />
              <Route element={<ProtectedRoute />}>
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
                  <Route path="users" element={<Users />} />
                  <Route path="*" element={<ComingSoon label="Not found" />} />
                </Route>
              </Route>
            </Routes>
          </AuthProvider>
        </BrowserRouter>
      </ConfirmProvider>
    </ToastProvider>
  );
}