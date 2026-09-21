import api from './api'

export const getDashboardSummary = () => api.get('/dashboard/summary')

export const getMonthlySales = (year) => api.get('/dashboard/sales', { params: { year } })

export const getDailySales = (salesDate) => api.get('/dashboard/sales/daily', { params: { sales_date: salesDate } })

export const getMonthlyPurchases = (year) => api.get('/dashboard/purchases', { params: { year } })

export const getTopProducts = () => api.get('/dashboard/top-products')

export const getLowStockProducts = () => api.get('/dashboard/low-stock')

export const getPaymentSummary = () => api.get('/dashboard/payment-summary')
