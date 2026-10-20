import { api } from "./client";

// ---- Authentication ----
export const login = (username, password) => {
  const data = new URLSearchParams({ username, password });
  return api.post("/auth/login", data, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  }).then((r) => r.data);
};
export const getCurrentUser = () => api.get("/auth/me").then((r) => r.data);
export const changePassword = (data) => api.post("/auth/change-password", data).then((r) => r.data);

// ---- User management ----
export const listUsers = () => api.get("/users").then((r) => r.data);
export const createUser = (data) => api.post("/users", data).then((r) => r.data);
export const updateUser = (id, data) => api.patch(`/users/${id}`, data).then((r) => r.data);
export const resetUserPassword = (id, data) => api.post(`/users/${id}/reset-password`, data).then((r) => r.data);

// ---- Dashboard / analytics ----
export const getDashboardSummary = () => api.get("/dashboard/summary").then((r) => r.data);
export const getSalesByMonth = (year) => api.get("/dashboard/sales", { params: { year } }).then((r) => r.data);
export const getPurchasesByMonth = (year) => api.get("/dashboard/purchases", { params: { year } }).then((r) => r.data);
export const getTopProducts = (limit = 10) => api.get("/dashboard/top-products", { params: { limit } }).then((r) => r.data);
export const getLowStock = (threshold = 100) => api.get("/dashboard/low-stock", { params: { threshold } }).then((r) => r.data);
export const getPaymentSummary = () => api.get("/dashboard/payment-summary").then((r) => r.data);
export const getDailySales = (sales_date) => api.get("/dashboard/sales/daily", { params: { sales_date } }).then((r) => r.data);

// ---- Categories ----
export const listCategories = () => api.get("/categories/").then((r) => r.data);
export const createCategory = (data) => api.post("/categories/", data).then((r) => r.data);

// ---- Products ----
export const listProducts = (search) => api.get("/products/", { params: { search } }).then((r) => r.data);
export const getProduct = (id) => api.get(`/products/${id}`).then((r) => r.data);
export const createProduct = (data) => api.post("/products/", data).then((r) => r.data);
export const updateProduct = (id, data) => api.patch(`/products/${id}`, data).then((r) => r.data);

// ---- Customers ----
export const listCustomers = (params) => api.get("/customers/", { params }).then((r) => r.data);
export const getCustomer = (id) => api.get(`/customers/${id}`).then((r) => r.data);
export const createCustomer = (data) => api.post("/customers/", data).then((r) => r.data);
export const updateCustomer = (id, data) => api.patch(`/customers/${id}`, data).then((r) => r.data);

// ---- Suppliers ----
export const listSuppliers = () => api.get("/suppliers/").then((r) => r.data);
export const getSupplier = (id) => api.get(`/suppliers/${id}`).then((r) => r.data);
export const createSupplier = (data) => api.post("/suppliers/", data).then((r) => r.data);
export const updateSupplier = (id, data) => api.patch(`/suppliers/${id}`, data).then((r) => r.data);

// ---- Purchases ----
export const listPurchases = (params) => api.get("/purchases/", { params }).then((r) => r.data);
export const getPurchase = (id) => api.get(`/purchases/${id}`).then((r) => r.data);
export const createPurchase = (data) => api.post("/purchases/", data).then((r) => r.data);
export const updatePurchaseStatus = (id, status) => api.patch(`/purchases/${id}/status`, { status }).then((r) => r.data);
export const receivePurchaseItems = (id, items) => api.patch(`/purchases/${id}/receive`, { items }).then((r) => r.data);

// ---- Purchase payments (accounts payable) ----
export const listPurchasePayments = () => api.get("/purchase-payments/").then((r) => r.data);
export const createPurchasePayment = (data) => api.post("/purchase-payments/", data).then((r) => r.data);

// ---- Orders ----
export const listOrders = (params) => api.get("/orders/", { params }).then((r) => r.data);
export const getOrder = (id) => api.get(`/orders/${id}`).then((r) => r.data);
export const createOrder = (data) => api.post("/orders/", data).then((r) => r.data);
export const updateOrderStatus = (id, status) => api.patch(`/orders/${id}/status`, { status }).then((r) => r.data);

// ---- Invoices ----
export const listInvoices = () => api.get("/invoices/").then((r) => r.data);
export const getInvoice = (id) => api.get(`/invoices/${id}`).then((r) => r.data);
export const createInvoice = (data) => api.post("/invoices/", data).then((r) => r.data);
export const cancelInvoice = (id) => api.patch(`/invoices/${id}/status`, { status: "CANCELLED" }).then((r) => r.data);

// ---- Deliveries ----
export const listDeliveries = () => api.get("/deliveries/").then((r) => r.data);
export const createDelivery = (data) => api.post("/deliveries/", data).then((r) => r.data);
export const updateDeliveryStatus = (id, status) => api.patch(`/deliveries/${id}/status`, { status }).then((r) => r.data);

// ---- Payments ----
export const listPayments = () => api.get("/payments/").then((r) => r.data);
export const createPayment = (data) => api.post("/payments/", data).then((r) => r.data);
export const applyCustomerCredit = (invoiceId) => api.post("/payments/apply-credit", { invoice_id: invoiceId }).then((r) => r.data);

// ---- Returns ----
export const listReturns = () => api.get("/returns/").then((r) => r.data);
export const getReturn = (id) => api.get(`/returns/${id}`).then((r) => r.data);
export const createReturn = (data) => api.post("/returns/", data).then((r) => r.data);
export const approveReturn = (id) => api.patch(`/returns/${id}/approve`).then((r) => r.data);
export const receiveReturn = (id) => api.patch(`/returns/${id}/receive`).then((r) => r.data);

// ---- Inventory ----
export const getProductStock = (productId) => api.get(`/inventory/stock/${productId}`).then((r) => r.data);
