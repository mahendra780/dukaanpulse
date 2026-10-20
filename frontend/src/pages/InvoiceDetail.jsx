import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getInvoice, cancelInvoice, applyCustomerCredit } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { Spinner, ErrorBanner, EmptyState } from "../components/Feedback";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/ToastProvider";
import { useConfirm } from "../components/ConfirmProvider";
import { useAuth } from "../auth/AuthProvider";
import { successMessage } from "../lib/messages";

const currency = (n) => `₹${Number(n || 0).toLocaleString("en-IN")}`;

export default function InvoiceDetail() {
  const { id } = useParams();
  const [invoice, setInvoice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [applyingCredit, setApplyingCredit] = useState(false);
  const toast = useToast();
  const confirm = useConfirm();
  const { can } = useAuth();

  const load = () => {
    setLoading(true);
    setError("");
    getInvoice(id)
      .then(setInvoice)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [id]);

  const handleCancel = async () => {
    const ok = await confirm({
      title: "Cancel this invoice?",
      description: `Invoice ${invoice.invoice_number} will be cancelled and its quantities freed back onto the order, so a corrected invoice can be created. This can't be undone.`,
      confirmLabel: "Cancel invoice",
      cancelLabel: "Keep invoice",
      danger: true,
    });
    if (!ok) return;

    setCancelling(true);
    try {
      await cancelInvoice(id);
      toast.success(successMessage("Invoice", "cancelled"));
      load();
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setCancelling(false);
    }
  };

  const handleApplyCredit = async () => {
    setApplyingCredit(true);
    try {
      await applyCustomerCredit(id);
      toast.success(successMessage("Credit", "applied"));
      load();
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setApplyingCredit(false);
    }
  };

  if (loading) return <Spinner />;
  if (error && !invoice) return <ErrorBanner message={error} />;
  if (!invoice) return null;

  const totalPaid = invoice.payments.reduce((s, p) => s + Number(p.amount), 0);
  const remaining = Number(invoice.total_amount) - totalPaid;

  const canCancel = can("invoices:write") && invoice.status === "UNPAID" && !invoice.delivery;
  const canApplyCredit = can("payments:write") && remaining > 0 && invoice.status !== "CANCELLED" && Number(invoice.customer_credit_balance) > 0;
  const creditToApply = Math.min(remaining, Number(invoice.customer_credit_balance || 0));
  const cancelledDeliveryCount = (invoice.deliveries || []).filter((d) => d.status === "CANCELLED").length;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Invoice {invoice.invoice_number}</h1>
          <p>{invoice.invoice_date} · <StatusBadge status={invoice.status} /></p>
        </div>
        <div className="section-actions">
          {canCancel && (
            <button className="btn btn-ghost" disabled={cancelling} onClick={handleCancel}>
              {cancelling ? "Cancelling…" : "Cancel invoice"}
            </button>
          )}
          <Link to="/invoices" className="btn btn-secondary">Back to invoices</Link>
        </div>
      </div>

      <div className="panel">
        <h3 className="panel-title">Items</h3>
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Unit</th>
              <th className="num">Qty</th>
              <th className="num">Price</th>
              <th className="num">Discount</th>
              <th className="num">Tax</th>
              <th className="num">Line total</th>
            </tr>
          </thead>
          <tbody>
            {invoice.items.map((it) => (
              <tr key={it.invoice_item_id}>
                <td>{it.product_name}</td>
                <td>{it.unit_name}</td>
                <td className="num">{it.quantity}</td>
                <td className="num">{currency(it.unit_price)}</td>
                <td className="num">{currency(it.discount)}</td>
                <td className="num">{currency(it.tax)}</td>
                <td className="num">{currency(it.line_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="field-row" style={{ marginTop: 16 }}>
          <div><span className="muted">Subtotal</span><br />{currency(invoice.subtotal)}</div>
          <div><span className="muted">Discount</span><br />{currency(invoice.discount)}</div>
          <div><span className="muted">Tax</span><br />{currency(invoice.tax)}</div>
          <div><strong>Total: {currency(invoice.total_amount)}</strong></div>
        </div>
      </div>

      <div className="detail-grid">
        <div className="panel">
          <h3 className="panel-title">Payments</h3>
          {invoice.payments.length === 0 ? (
            <EmptyState label="No payments recorded yet." />
          ) : (
            <>
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th className="num">Amount</th>
                    <th>Method</th>
                    <th>Reference</th>
                  </tr>
                </thead>
                <tbody>
                  {invoice.payments.map((p) => (
                    <tr key={p.payment_id}>
                      <td>{p.payment_date}</td>
                      <td className="num">{currency(p.amount)}</td>
                      <td>
                        {p.payment_method === "RETURN_CREDIT" ? (
                          <span className="badge badge-accent">Return credit</span>
                        ) : p.payment_method === "CREDIT_APPLIED" ? (
                          <span className="badge badge-accent">Credit applied</span>
                        ) : (
                          p.payment_method?.replaceAll("_", " ")
                        )}
                      </td>
                      <td>{p.reference_number || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="muted" style={{ marginTop: 12, marginBottom: 0 }}>
                Paid {currency(totalPaid)} of {currency(invoice.total_amount)}
                {remaining > 0 ? ` · ${currency(remaining)} remaining` : " · fully paid"}
              </p>
            </>
          )}
          {canApplyCredit && (
            <div style={{ marginTop: 12, padding: "10px 12px", background: "var(--accent-soft)", borderRadius: "var(--radius)" }}>
              <p style={{ margin: "0 0 8px", fontSize: 13 }}>
                This customer has <strong>{currency(invoice.customer_credit_balance)}</strong> credit available
                (from an earlier return). Apply <strong>{currency(creditToApply)}</strong> of it to this invoice?
              </p>
              <button className="btn btn-primary" disabled={applyingCredit} onClick={handleApplyCredit}>
                {applyingCredit ? "Applying…" : `Apply ${currency(creditToApply)} credit`}
              </button>
            </div>
          )}
          {can("payments:write") && remaining > 0 && invoice.status !== "CANCELLED" && (
            <Link to="/payments" className="btn btn-secondary" style={{ marginTop: 12 }}>Record a payment</Link>
          )}
        </div>

        <div className="panel">
          <h3 className="panel-title">Delivery</h3>
          {invoice.delivery ? (
            <div style={{ fontSize: 13.5 }}>
              <p><StatusBadge status={invoice.delivery.status} /></p>
              <p className="muted" style={{ margin: "4px 0" }}>{invoice.delivery.delivery_date || "No date set"}</p>
              <p style={{ margin: "4px 0" }}>{invoice.delivery.delivery_address}</p>
              {invoice.delivery.vehicle_number && <p className="muted" style={{ margin: "4px 0" }}>Vehicle: {invoice.delivery.vehicle_number}</p>}
              {invoice.delivery.driver_name && <p className="muted" style={{ margin: "4px 0" }}>Driver: {invoice.delivery.driver_name}</p>}
              {can("deliveries:read") && (
                <Link to="/deliveries" className="btn btn-secondary" style={{ marginTop: 8 }}>Manage delivery</Link>
              )}
            </div>
          ) : (
            <>
              <EmptyState label="No active delivery for this invoice yet." />
              {can("deliveries:write") && (
                <Link to="/deliveries" className="btn btn-secondary">Create delivery</Link>
              )}
            </>
          )}
          {cancelledDeliveryCount > 0 && (
            <p className="muted" style={{ marginTop: 10, fontSize: 12 }}>
              {cancelledDeliveryCount} earlier delivery attempt{cancelledDeliveryCount === 1 ? "" : "s"} cancelled
            </p>
          )}
        </div>
      </div>

      <div className="panel">
        <h3 className="panel-title">Returns</h3>
        {invoice.returns.length === 0 ? (
          <EmptyState label="No returns for this invoice." />
        ) : (
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Reason</th>
                <th>Status</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {invoice.returns.map((r) => (
                <tr key={r.return_id}>
                  <td>{r.return_date}</td>
                  <td>{r.reason.replaceAll("_", " ")}</td>
                  <td><StatusBadge status={r.status} /></td>
                  <td>{r.notes || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}