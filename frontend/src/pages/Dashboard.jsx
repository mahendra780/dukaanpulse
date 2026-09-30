import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import {
  getDashboardSummary,
  getSalesByMonth,
  getPurchasesByMonth,
  getTopProducts,
  getLowStock,
  getPaymentSummary,
} from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { Spinner, ErrorBanner, EmptyState } from "../components/Feedback";
import StatCard from "../components/StatCard";

const currency = (n) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n || 0);

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState(null);
  const [sales, setSales] = useState([]);
  const [purchases, setPurchases] = useState([]);
  const [topProducts, setTopProducts] = useState([]);
  const [lowStock, setLowStock] = useState([]);
  const [paymentSummary, setPaymentSummary] = useState(null);

  const year = new Date().getFullYear();

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      getDashboardSummary(),
      getSalesByMonth(year),
      getPurchasesByMonth(year),
      getTopProducts(5),
      getLowStock(100),
      getPaymentSummary(),
    ])
      .then(([s, sl, pu, tp, ls, ps]) => {
        if (cancelled) return;
        setSummary(s);
        setSales(sl);
        setPurchases(pu);
        setTopProducts(tp);
        setLowStock(ls);
        setPaymentSummary(ps);
      })
      .catch((err) => !cancelled && setError(extractErrorMessage(err)))
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
    };
  }, [year]);

  if (loading) return <Spinner label="Loading dashboard…" />;

  const trend = sales.map((row, i) => ({
    month: row.month,
    sales: row.sales,
    purchases: purchases[i]?.purchase ?? 0,
  }));

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>Overview for {year}</p>
        </div>
      </div>

      <ErrorBanner message={error} />

      {summary && (
        <div className="stat-grid">
          <StatCard label="Products" value={summary.total_products} />
          <StatCard label="Customers" value={summary.total_customers} />
          <StatCard label="Suppliers" value={summary.total_suppliers} />
          <StatCard label="Orders" value={summary.total_orders} />
          <StatCard label="Total sales" value={currency(summary.total_sales)} />
          <StatCard
            label="Total purchases"
            value={currency(summary.total_purchases)}
          />
        </div>
      )}

      <div className="panel">
        <h3 className="panel-title">Sales vs purchases — {year}</h3>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={trend}>
            <CartesianGrid stroke="#e3e1d9" vertical={false} />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 12, fill: "#6e736f" }}
              axisLine={{ stroke: "#e3e1d9" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 12, fill: "#6e736f" }}
              axisLine={false}
              tickLine={false}
              width={70}
              tickFormatter={(v) => currency(v)}
            />
            <Tooltip
              formatter={(v) => currency(v)}
              contentStyle={{
                borderRadius: 6,
                border: "1px solid #e3e1d9",
                fontSize: 13,
              }}
            />
            <Line
              type="monotone"
              dataKey="sales"
              name="Sales"
              stroke="#1f4b4c"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="purchases"
              name="Purchases"
              stroke="#b7791f"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="detail-grid">
        <div className="panel">
          <h3 className="panel-title">Top products (by quantity sold)</h3>
          {topProducts.length === 0 ? (
            <EmptyState label="No sales recorded yet" />
          ) : (
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Product</th>
                  <th className="num">Sold</th>
                  <th className="num">Revenue</th>
                </tr>
              </thead>
              <tbody>
                {topProducts.map((p) => (
                  <tr key={p.product_id}>
                    <td>{p.rank}</td>
                    <td>
                      {p.product_name}
                      {p.brand_name ? ` · ${p.brand_name}` : ""}
                    </td>
                    <td className="num">
                      {p.sold_quantity} {p.base_unit}
                    </td>
                    <td className="num">{currency(p.sales_amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="panel">
          <h3 className="panel-title">Low stock</h3>
          {lowStock.length === 0 ? (
            <EmptyState label="No products under the threshold" />
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th className="num">Stock</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {lowStock.map((p) => (
                  <tr key={p.product_id}>
                    <td>{p.product_name}</td>
                    <td className="num">
                      {p.current_stock} {p.base_unit}
                    </td>
                    <td>
                      <span
                        className={`badge ${p.stock_status === "OUT_OF_STOCK" ? "badge-red" : "badge-amber"}`}
                      >
                        {p.stock_status.replaceAll("_", " ")}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {paymentSummary && (
        <div className="panel">
          <h3 className="panel-title">Payment status</h3>
          <div className="stat-grid">
            <StatCard
              label="Paid invoices"
              value={paymentSummary.paid_invoices}
            />
            <StatCard
              label="Partially paid"
              value={paymentSummary.partially_paid_invoices}
            />
            <StatCard label="Unpaid" value={paymentSummary.unpaid_invoices} />
            <StatCard
              label="Pending amount"
              value={currency(paymentSummary.pending_amount)}
            />
            {paymentSummary.total_customer_credit > 0 && (
              <StatCard
                label="Customer credit balance"
                value={currency(paymentSummary.total_customer_credit)}
              />
            )}
            {paymentSummary.refund_due_amount > 0 && (
              <StatCard
                label="Unresolved refund (check data)"
                value={currency(paymentSummary.refund_due_amount)}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
