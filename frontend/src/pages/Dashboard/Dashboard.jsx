import { useMemo, useRef } from 'react'
import { useQueries } from '@tanstack/react-query'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AlertTriangle, CheckCircle2, Clock3, FileText, Package, ShoppingCart, Users, Wallet } from 'lucide-react'
import Card from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import {
  getDailySales,
  getDashboardSummary,
  getLowStockProducts,
  getMonthlyPurchases,
  getMonthlySales,
  getPaymentSummary,
  getTopProducts,
} from '../../services/dashboardService'

const currencyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})

const numberFormatter = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 })

const chartAxisStyle = { fill: '#94A3B8', fontSize: 12 }
const chartGridStroke = 'rgba(148, 163, 184, 0.14)'

function getLocalIsoDate() {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60_000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}

function formatCurrency(value) {
  return typeof value === 'number' ? currencyFormatter.format(value) : '—'
}

function formatNumber(value) {
  return typeof value === 'number' ? numberFormatter.format(value) : '—'
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null

  return (
    <div className="rounded-xl border border-white/10 bg-slate-950/95 px-3 py-2 text-xs shadow-xl backdrop-blur-xl">
      <p className="mb-1 text-slate-400">{label}</p>
      {payload.map((item) => (
        <p key={item.dataKey} style={{ color: item.color }}>
          {item.name}: {formatCurrency(item.value)}
        </p>
      ))}
    </div>
  )
}

function ChartEmptyState({ message = 'No data available for this period.' }) {
  return <div className="grid h-72 place-items-center text-sm text-slate-400">{message}</div>
}

function SkeletonBlock({ className = '', ...props }) {
  return <div className={`animate-pulse rounded-lg bg-emerald-300/10 ${className}`} aria-hidden="true" {...props} />
}

function KpiSparkline({ color, points }) {
  return (
    <svg viewBox="0 0 120 32" className="h-8 w-24" fill="none" aria-hidden="true">
      <path d="M1 29H119" stroke="rgba(148, 163, 184, 0.14)" />
      <polyline points={points} stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function ChartSkeleton({ className = '' }) {
  return (
    <Card className={className} padding="p-5 sm:p-6">
      <div className="mb-5 space-y-2">
        <SkeletonBlock className="h-5 w-32" />
        <SkeletonBlock className="h-4 w-52 bg-slate-400/10" />
      </div>
      <div className="relative h-72 overflow-hidden rounded-2xl border border-emerald-300/10 bg-slate-950/20 px-5 pb-7 pt-5">
        <div className="absolute inset-x-5 top-1/4 border-t border-dashed border-white/10" />
        <div className="absolute inset-x-5 top-1/2 border-t border-dashed border-white/10" />
        <div className="absolute inset-x-5 top-3/4 border-t border-dashed border-white/10" />
        <div className="flex h-full items-end justify-between gap-3">
          {[42, 66, 50, 82, 61, 74, 55, 90, 69, 78, 58, 86].map((height, index) => (
            <SkeletonBlock key={index} className="w-full rounded-t-md rounded-b-none bg-emerald-400/15" style={{ height: `${height}%` }} />
          ))}
        </div>
      </div>
    </Card>
  )
}

function TableSkeleton({ titleWidth = 'w-32', subtitleWidth = 'w-52' }) {
  return (
    <Card padding="p-5 sm:p-6">
      <div className="mb-5 space-y-2">
        <SkeletonBlock className={`h-5 ${titleWidth}`} />
        <SkeletonBlock className={`h-4 ${subtitleWidth} bg-slate-400/10`} />
      </div>
      <div className="overflow-hidden rounded-3xl border border-white/10 bg-slate-800/50">
        <div className="grid grid-cols-3 gap-5 border-b border-white/10 bg-white/5 px-5 py-3">
          <SkeletonBlock className="h-3 w-20 bg-slate-400/10" />
          <SkeletonBlock className="h-3 w-16 bg-slate-400/10" />
          <SkeletonBlock className="h-3 w-24 bg-slate-400/10" />
        </div>
        {[0, 1, 2, 3].map((row) => (
          <div key={row} className="grid grid-cols-3 items-center gap-5 border-b border-white/10 px-5 py-3.5 last:border-b-0">
            <div className="space-y-2"><SkeletonBlock className="h-4 w-32" /><SkeletonBlock className="h-3 w-20 bg-slate-400/10" /></div>
            <SkeletonBlock className="h-4 w-16 bg-slate-400/10" />
            <SkeletonBlock className="h-4 w-20 bg-slate-400/10" />
          </div>
        ))}
      </div>
    </Card>
  )
}

function ProductListSkeleton() {
  return (
    <div className="space-y-3" aria-label="Loading top products">
      {[0, 1, 2, 3, 4].map((row) => (
        <div key={row} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-2"><SkeletonBlock className="h-4 w-32" /><SkeletonBlock className="h-3 w-16 bg-slate-400/10" /></div>
            <SkeletonBlock className="h-4 w-20 bg-slate-400/10" />
          </div>
          <SkeletonBlock className="mt-4 h-1.5 w-full rounded-full bg-slate-400/10" />
        </div>
      ))}
    </div>
  )
}

function PaymentSummarySkeleton() {
  return (
    <div aria-label="Loading payment summary">
      <div className="grid grid-cols-2 gap-3">
        {[0, 1, 2, 3].map((item) => <SkeletonBlock key={item} className="h-24 rounded-2xl bg-white/[0.04]" />)}
      </div>
      <div className="mx-auto mt-6 h-28 w-28 rounded-full border-[10px] border-emerald-300/10" />
    </div>
  )
}

function LowStockTableSkeleton() {
  return (
    <div className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/35" aria-label="Loading low stock products">
      <div className="grid min-w-[680px] grid-cols-[2fr_1fr_1fr_1fr_1fr] gap-4 border-b border-white/10 bg-white/[0.05] px-5 py-3">
        {[0, 1, 2, 3, 4].map((column) => <SkeletonBlock key={column} className="h-3 w-16 bg-slate-400/10" />)}
      </div>
      {[0, 1, 2, 3].map((row) => (
        <div key={row} className="grid min-w-[680px] grid-cols-[2fr_1fr_1fr_1fr_1fr] items-center gap-4 border-b border-white/10 px-5 py-4 last:border-b-0">
          {[0, 1, 2, 3, 4].map((column) => <SkeletonBlock key={column} className="h-4 w-20 bg-slate-400/10" />)}
        </div>
      ))}
    </div>
  )
}

function DashboardSkeleton() {
  return (
    <div className="space-y-4 pb-8" role="status" aria-label="Loading dashboard analytics">
      <header>
        <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">Business Analytics</h1>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Loading business summary">
        {[0, 1, 2, 3].map((card) => (
          <Card key={card} padding="p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-3"><SkeletonBlock className="h-4 w-24 bg-slate-400/10" /><SkeletonBlock className="h-8 w-32" /></div>
              <SkeletonBlock className="h-10 w-10 rounded-2xl bg-emerald-400/15" />
            </div>
          </Card>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <ChartSkeleton />
        <ChartSkeleton />
        <ChartSkeleton className="xl:col-span-2" />
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <TableSkeleton titleWidth="w-28" subtitleWidth="w-48" />
        <TableSkeleton titleWidth="w-40" subtitleWidth="w-56" />
      </section>

      <Card padding="p-5 sm:p-6">
        <div className="mb-5 space-y-2"><SkeletonBlock className="h-5 w-36" /><SkeletonBlock className="h-4 w-44 bg-slate-400/10" /></div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((card) => <SkeletonBlock key={card} className="h-24 rounded-2xl bg-white/[0.04]" />)}
        </div>
      </Card>
    </div>
  )
}

function SectionError({ error, onRetry }) {
  const message = error?.response?.data?.detail || 'Unable to load this section. Please try again.'

  return (
    <div className="flex min-h-32 flex-col gap-4 rounded-2xl border border-red-400/30 bg-red-400/5 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex gap-3">
        <AlertTriangle className="mt-0.5 shrink-0 text-red-400" aria-hidden="true" />
        <div>
          <h3 className="font-semibold text-red-100">Section unavailable</h3>
          <p className="mt-1 text-sm text-slate-400">{message}</p>
        </div>
      </div>
      <Button variant="outline" onClick={onRetry}>Try again</Button>
    </div>
  )
}

function Dashboard() {
  const currentYear = new Date().getFullYear()
  const today = useMemo(getLocalIsoDate, [])
  const [summaryQuery, salesQuery, dailySalesQuery, purchasesQuery, topProductsQuery, lowStockQuery, paymentSummaryQuery] = useQueries({
    queries: [
      { queryKey: ['dashboard', 'summary'], queryFn: async () => (await getDashboardSummary()).data },
      { queryKey: ['dashboard', 'sales', currentYear], queryFn: async () => (await getMonthlySales(currentYear)).data },
      { queryKey: ['dashboard', 'daily-sales', today], queryFn: async () => (await getDailySales(today)).data },
      { queryKey: ['dashboard', 'purchases', currentYear], queryFn: async () => (await getMonthlyPurchases(currentYear)).data },
      { queryKey: ['dashboard', 'top-products'], queryFn: async () => (await getTopProducts()).data },
      { queryKey: ['dashboard', 'low-stock'], queryFn: async () => (await getLowStockProducts()).data },
      { queryKey: ['dashboard', 'payment-summary'], queryFn: async () => (await getPaymentSummary()).data },
    ],
  })
  const queries = [summaryQuery, salesQuery, dailySalesQuery, purchasesQuery, topProductsQuery, lowStockQuery, paymentSummaryQuery]
  const hasCachedDataOnMount = useRef(queries.some((query) => query.data !== undefined)).current
  const isInitialLoading = !hasCachedDataOnMount && queries.some((query) => query.isPending)

  if (isInitialLoading) {
    return <DashboardSkeleton />
  }

  const { data: summary } = summaryQuery
  const { data: sales } = salesQuery
  const { data: dailySales } = dailySalesQuery
  const { data: purchases } = purchasesQuery
  const { data: topProducts } = topProductsQuery
  const { data: lowStock } = lowStockQuery
  const { data: paymentSummary } = paymentSummaryQuery
  const displayedTopProducts = Array.isArray(topProducts) ? topProducts.slice(0, 5) : []
  const highestSoldQuantity = Math.max(...displayedTopProducts.map((product) => Number(product.sold_quantity) || 0), 0)
  const totalInvoiceAmount = Number(paymentSummary?.total_invoice_amount ?? paymentSummary?.total_sales_amount) || 0
  const paidAmount = Number(paymentSummary?.paid_amount ?? paymentSummary?.total_paid_amount) || 0
  const pendingAmount = Number(paymentSummary?.pending_amount) || Math.max(totalInvoiceAmount - paidAmount, 0)
  const paymentCompletion = totalInvoiceAmount > 0
    ? Math.min(Math.round((paidAmount / totalInvoiceAmount) * 100), 100)
    : 0
  const kpis = [
    { label: 'Total Sales', value: formatCurrency(summary?.total_sales), icon: Wallet, badge: '+12.5%', iconClass: 'bg-gradient-to-br from-emerald-300 to-emerald-600 text-emerald-950', badgeClass: 'border-emerald-300/20 bg-emerald-400/10 text-emerald-200', sparkColor: '#34d399', sparkPoints: '2,25 18,19 32,22 48,12 63,17 78,8 94,14 118,3' },
    { label: 'Total Purchases', value: formatCurrency(summary?.total_purchases), icon: ShoppingCart, badge: '+8.2%', iconClass: 'bg-gradient-to-br from-violet-300 to-purple-600 text-purple-950', badgeClass: 'border-violet-300/20 bg-violet-400/10 text-violet-200', sparkColor: '#c4b5fd', sparkPoints: '2,22 18,16 32,20 48,10 63,15 78,18 94,7 118,12' },
    { label: 'Customers', value: formatNumber(summary?.total_customers), icon: Users, badge: '+6.8%', iconClass: 'bg-gradient-to-br from-cyan-200 to-cyan-600 text-cyan-950', badgeClass: 'border-cyan-300/20 bg-cyan-400/10 text-cyan-200', sparkColor: '#67e8f9', sparkPoints: '2,26 18,23 32,15 48,19 63,10 78,14 94,5 118,9' },
    { label: 'Products', value: formatNumber(summary?.total_products), icon: Package, badge: '+4.1%', iconClass: 'bg-gradient-to-br from-amber-200 to-amber-500 text-amber-950', badgeClass: 'border-amber-300/20 bg-amber-400/10 text-amber-200', sparkColor: '#fcd34d', sparkPoints: '2,24 18,12 32,17 48,14 63,20 78,8 94,12 118,4' },
  ]

  const dailySalesData = Array.isArray(dailySales)
    ? dailySales
    : dailySales?.hourly_sales || dailySales?.invoices?.map((invoice) => ({
      hour: invoice.hour || invoice.invoice_number,
      sales: invoice.total_amount,
    })) || []

  return (
    <div className="space-y-4 pb-8">
      <header>
        <h1 id="business-analytics-title" className="text-xl font-bold tracking-tight text-white sm:text-2xl">Business Analytics</h1>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Business summary">
        {summaryQuery.isError ? (
          <Card className="border-red-400/30 sm:col-span-2 xl:col-span-4" padding="p-5">
            <SectionError error={summaryQuery.error} onRetry={summaryQuery.refetch} />
          </Card>
        ) : kpis.map(({ label, value, icon: Icon, badge, iconClass, badgeClass, sparkColor, sparkPoints }) => (
          <Card key={label} className="rounded-3xl border-white/10 bg-slate-800/50 transition-all duration-300 hover:-translate-y-1 hover:border-emerald-300/30 hover:shadow-[0_16px_35px_rgba(16,185,129,0.14)]" padding="p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm text-slate-400">{label}</p>
                <p className="mt-2 text-2xl font-bold tracking-tight text-white">{value}</p>
              </div>
              <span className={`grid h-11 w-11 place-items-center rounded-full shadow-lg ${iconClass}`}>
                <Icon size={20} aria-hidden="true" />
              </span>
            </div>
            <div className="mt-5 flex items-end justify-between gap-3">
              <span className={`rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass}`}>{badge}</span>
              <KpiSparkline color={sparkColor} points={sparkPoints} />
            </div>
          </Card>
        ))}
      </section>

      <section aria-labelledby="business-analytics-title">
        <div className="grid gap-6 xl:grid-cols-10">
          {salesQuery.isPending ? <ChartSkeleton className="xl:col-span-7" /> : (
            <Card className="xl:col-span-7" padding="p-5 sm:p-6">
              <div className="mb-5">
                <h3 className="font-semibold text-white">Monthly Sales</h3>
                <p className="mt-1 text-sm text-slate-400">Sales performance for {currentYear}</p>
              </div>
              {salesQuery.isError ? <SectionError error={salesQuery.error} onRetry={salesQuery.refetch} /> : sales?.length ? (
                <ResponsiveContainer width="100%" height={288}>
                  <BarChart data={sales} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                    <defs>
                      <linearGradient id="monthlySalesGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#6ee7b7" />
                        <stop offset="100%" stopColor="#059669" />
                      </linearGradient>
                    </defs>
                    <CartesianGrid vertical={false} stroke="rgba(255, 255, 255, 0.05)" />
                    <XAxis dataKey="month" axisLine={false} tickLine={false} tick={chartAxisStyle} />
                    <YAxis axisLine={false} tickLine={false} tick={chartAxisStyle} tickFormatter={formatCurrency} />
                    <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(16, 185, 129, 0.08)' }} />
                    <Legend wrapperStyle={{ color: '#f8fafc', fontSize: 12 }} />
                    <Bar dataKey="sales" name="Sales" fill="url(#monthlySalesGradient)" radius={[10, 10, 2, 2]} maxBarSize={46} />
                  </BarChart>
                </ResponsiveContainer>
              ) : <ChartEmptyState message="No sales data available" />}
            </Card>
          )}

          {dailySalesQuery.isPending ? <ChartSkeleton className="xl:col-span-3" /> : (
            <Card className="xl:col-span-3" padding="p-5 sm:p-6">
              <div className="mb-5">
                <h3 className="font-semibold text-white">Today&apos;s Sales</h3>
                <p className="mt-2 text-2xl font-bold tracking-tight text-emerald-300">{formatCurrency(dailySales?.total_sales)}</p>
              </div>
              {dailySalesQuery.isError ? <SectionError error={dailySalesQuery.error} onRetry={dailySalesQuery.refetch} /> : dailySalesData.length ? (
                <ResponsiveContainer width="100%" height={288}>
                  <AreaChart data={dailySalesData} margin={{ top: 8, right: 4, left: -18, bottom: 0 }}>
                    <defs>
                      <linearGradient id="todaySalesGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#34d399" stopOpacity={0.52} />
                        <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid vertical={false} stroke="rgba(255, 255, 255, 0.05)" />
                    <XAxis dataKey="hour" axisLine={false} tickLine={false} tick={chartAxisStyle} />
                    <YAxis axisLine={false} tickLine={false} tick={chartAxisStyle} tickFormatter={formatCurrency} />
                    <Tooltip content={<ChartTooltip />} />
                    <Legend wrapperStyle={{ color: '#f8fafc', fontSize: 12 }} />
                    <Area type="monotone" dataKey="sales" name="Sales" stroke="#34d399" strokeWidth={3} fill="url(#todaySalesGradient)" activeDot={{ r: 6, fill: '#f0fdf4', stroke: '#34d399', strokeWidth: 4 }} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : <ChartEmptyState message="No sales data available" />}
            </Card>
          )}

          {purchasesQuery.isPending ? <ChartSkeleton className="xl:col-span-10" /> : (
            <Card className="xl:col-span-10" padding="p-5">
              <div className="mb-2">
                <h3 className="font-semibold text-white">Monthly Purchases</h3>
              </div>
              {purchasesQuery.isError ? <SectionError error={purchasesQuery.error} onRetry={purchasesQuery.refetch} /> : purchases?.length ? (
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={purchases} margin={{ top: 2, right: 8, left: -18, bottom: 0 }}>
                    <defs>
                      <linearGradient id="purchasesLineGradient" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="#c4b5fd" />
                        <stop offset="100%" stopColor="#7c3aed" />
                      </linearGradient>
                    </defs>
                    <CartesianGrid vertical={false} stroke="rgba(255, 255, 255, 0.05)" />
                    <XAxis dataKey="month" axisLine={false} tickLine={false} tick={chartAxisStyle} />
                    <YAxis axisLine={false} tickLine={false} tick={chartAxisStyle} tickFormatter={formatCurrency} />
                    <Tooltip content={<ChartTooltip />} />
                    <Legend wrapperStyle={{ color: '#f8fafc', fontSize: 12 }} />
                    <Line type="monotone" dataKey="purchase" name="Purchases" stroke="url(#purchasesLineGradient)" strokeWidth={3} dot={{ fill: '#a78bfa', stroke: '#312e81', strokeWidth: 2, r: 3 }} activeDot={{ fill: '#f5f3ff', stroke: '#a78bfa', strokeWidth: 4, r: 6 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : <ChartEmptyState message="No sales data available" />}
            </Card>
          )}
        </div>
      </section>

      <section className="grid items-stretch gap-6 xl:grid-cols-2" aria-label="Product and payment insights">
        <Card className="h-full" padding="p-5">
          <div className="mb-4">
            <h2 className="font-semibold text-white">Top Selling Products</h2>
          </div>
          {topProductsQuery.isPending ? <ProductListSkeleton /> : topProductsQuery.isError ? <SectionError error={topProductsQuery.error} onRetry={topProductsQuery.refetch} /> : displayedTopProducts.length ? (
            <div className="space-y-2.5">
              {displayedTopProducts.map((product, index) => {
                const progress = highestSoldQuantity > 0 ? Math.round(((Number(product.sold_quantity) || 0) / highestSoldQuantity) * 100) : 0

                return (
                  <article key={product.product_id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-3.5 transition-all duration-300 hover:-translate-y-0.5 hover:border-emerald-300/35 hover:bg-emerald-400/[0.06] hover:shadow-[0_10px_28px_rgba(16,185,129,0.12)]">
                    <div className="flex items-start gap-3">
                      <span className="grid h-7 min-w-7 place-items-center rounded-lg border border-emerald-300/20 bg-emerald-400/10 px-1 text-xs font-bold text-emerald-200">#{index + 1}</span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-col gap-1.5 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
                          <p className="truncate font-semibold text-white">{product.product_name}</p>
                          <p className="shrink-0 text-base font-bold tracking-tight text-emerald-300">{formatCurrency(product.sales_amount)}</p>
                        </div>
                        <p className="text-sm text-slate-400"><span className="font-medium text-slate-200">{formatNumber(product.sold_quantity)}</span> {product.base_unit || 'units'}</p>
                        <div className="mt-3 flex items-center gap-3">
                          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-emerald-950/80">
                            <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-300 shadow-[0_0_12px_rgba(52,211,153,0.75)]" style={{ width: `${progress}%` }} />
                          </div>
                          <span className="w-9 text-right text-xs font-semibold text-emerald-200">{progress}%</span>
                        </div>
                      </div>
                    </div>
                  </article>
                )
              })}
            </div>
          ) : <ChartEmptyState message="No product sales available" />}
        </Card>

        <Card className="h-full" padding="p-5">
          <div className="mb-4">
            <h2 className="font-semibold text-white">Payment Summary</h2>
          </div>
          {paymentSummaryQuery.isPending ? <PaymentSummarySkeleton /> : paymentSummaryQuery.isError ? <SectionError error={paymentSummaryQuery.error} onRetry={paymentSummaryQuery.refetch} /> : (
            <>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'Total Invoice Amount', value: formatCurrency(totalInvoiceAmount), icon: FileText, iconClass: 'bg-sky-400/10 text-sky-300', badge: 'Invoiced', badgeClass: 'bg-sky-400/10 text-sky-200' },
                  { label: 'Paid Amount', value: formatCurrency(paidAmount), icon: CheckCircle2, iconClass: 'bg-emerald-400/10 text-emerald-300', badge: 'Collected', badgeClass: 'bg-emerald-400/10 text-emerald-200' },
                  { label: 'Pending Amount', value: formatCurrency(pendingAmount), icon: Clock3, iconClass: 'bg-amber-400/10 text-amber-300', badge: 'Due', badgeClass: 'bg-amber-400/10 text-amber-200' },
                  { label: 'Paid Invoices', value: formatNumber(paymentSummary?.paid_invoices), icon: Wallet, iconClass: 'bg-violet-400/10 text-violet-300', badge: 'Settled', badgeClass: 'bg-violet-400/10 text-violet-200' },
                ].map(({ label, value, icon: Icon, iconClass, badge, badgeClass }) => (
                  <div key={label} className="rounded-2xl border border-white/10 bg-white/[0.03] p-3 transition-colors hover:border-emerald-300/25 hover:bg-emerald-400/[0.04]">
                    <div className="flex items-start justify-between gap-2">
                      <span className={`grid h-8 w-8 place-items-center rounded-xl ${iconClass}`}><Icon size={16} aria-hidden="true" /></span>
                      <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${badgeClass}`}>{badge}</span>
                    </div>
                    <p className="mt-3 text-[11px] leading-4 text-slate-400">{label}</p>
                    <p className="mt-1 truncate text-base font-bold tracking-tight text-white">{value}</p>
                  </div>
                ))}
              </div>
              <div className="mt-5 flex items-center justify-center border-t border-white/10 pt-4">
                <div className="grid h-28 w-28 place-items-center rounded-full p-2" style={{ background: `conic-gradient(from -90deg, #059669 0%, #6ee7b7 ${paymentCompletion}%, rgba(148, 163, 184, 0.14) ${paymentCompletion}% 100%)` }} role="img" aria-label={`${paymentCompletion}% payment completion`}>
                  <div className="grid h-full w-full place-items-center rounded-full bg-slate-900/95 text-center shadow-inner">
                    <span className="text-2xl font-bold tracking-tight text-emerald-300">{paymentCompletion}%</span>
                  </div>
                </div>
              </div>
            </>
          )}
        </Card>
      </section>

      <section aria-labelledby="low-stock-title">
        <Card padding="p-5 sm:p-6">
          <div className="mb-5 flex gap-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-amber-400/10 text-amber-300"><AlertTriangle size={18} aria-hidden="true" /></span>
            <div>
              <h2 id="low-stock-title" className="font-semibold text-white">Low Stock Products</h2>
            </div>
          </div>
          {lowStockQuery.isPending ? <LowStockTableSkeleton /> : lowStockQuery.isError ? <SectionError error={lowStockQuery.error} onRetry={lowStockQuery.refetch} /> : Array.isArray(lowStock) && lowStock.length ? (
            <div className="overflow-x-auto rounded-3xl border border-white/10 bg-slate-950/35">
              <table className="min-w-[720px] w-full border-separate border-spacing-0 text-left text-sm">
                <thead className="sticky top-0 z-10 bg-slate-900/95 backdrop-blur-xl">
                  <tr className="text-xs uppercase tracking-wider text-slate-400">
                    <th className="px-5 py-3.5 font-semibold">Product</th>
                    <th className="px-5 py-3.5 font-semibold">SKU</th>
                    <th className="px-5 py-3.5 font-semibold">Current Stock</th>
                    <th className="px-5 py-3.5 font-semibold">Reorder Level</th>
                    <th className="px-5 py-3.5 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {lowStock.map((product) => {
                    const stock = Number(product.current_stock) || 0
                    const reorderLevel = Number(product.reorder_level ?? product.threshold) || 0
                    const sourceStatus = String(product.stock_status || '').toUpperCase()
                    const isCritical = sourceStatus.includes('CRITICAL') || sourceStatus.includes('OUT_OF_STOCK') || stock <= 0
                    const isLow = !isCritical && (sourceStatus.includes('LOW') || stock < reorderLevel)
                    const status = isCritical ? 'Critical' : isLow ? 'Low' : 'Healthy'
                    const statusClass = isCritical
                      ? 'border-red-400/20 bg-red-400/10 text-red-300'
                      : isLow
                        ? 'border-amber-400/20 bg-amber-400/10 text-amber-300'
                        : 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300'
                    const belowReorderLevel = stock < reorderLevel

                    return (
                      <tr key={product.product_id} className="group transition-colors hover:bg-emerald-400/[0.06]">
                        <td className="border-t border-white/10 px-5 py-4">
                          <div className="flex items-center gap-2">
                            {isCritical && <AlertTriangle size={16} className="shrink-0 text-red-300" aria-label="Critical stock level" />}
                            <div><p className="font-semibold text-white">{product.product_name}</p>{product.brand_name && <p className="mt-0.5 text-xs text-slate-500">{product.brand_name}</p>}</div>
                          </div>
                        </td>
                        <td className="border-t border-white/10 px-5 py-4 font-mono text-xs text-slate-400">{product.sku || '—'}</td>
                        <td className={`border-t border-white/10 px-5 py-4 font-semibold ${belowReorderLevel || isCritical ? 'text-red-300' : 'text-slate-200'}`}>{formatNumber(stock)} <span className="font-normal text-slate-500">{product.base_unit || 'units'}</span></td>
                        <td className="border-t border-white/10 px-5 py-4 text-slate-300">{formatNumber(reorderLevel)} <span className="text-slate-500">{product.base_unit || 'units'}</span></td>
                        <td className="border-t border-white/10 px-5 py-4"><span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${statusClass}`}>{status}</span></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex min-h-40 flex-col items-center justify-center rounded-3xl border border-emerald-400/20 bg-emerald-400/[0.05] text-center">
              <CheckCircle2 size={28} className="text-emerald-300" aria-hidden="true" />
              <p className="mt-3 font-semibold text-emerald-100">Inventory levels are healthy.</p>
            </div>
          )}
        </Card>
      </section>
    </div>
  )
}

export default Dashboard
