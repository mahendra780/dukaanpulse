import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Plus } from "lucide-react";
import { listInvoices, listOrders, getOrder, createInvoice } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { Spinner, EmptyState, ErrorBanner } from "../components/Feedback";
import StatusBadge from "../components/StatusBadge";
import Modal from "../components/Modal";
import { useToast } from "../components/ToastProvider";
import { useAuth } from "../auth/AuthProvider";
import { successMessage } from "../lib/messages";


function CreateInvoiceModal({ orders, onClose, onCreated }) {
  const [orderId, setOrderId] = useState(orders[0]?.order_id ?? "");
  const [orderDetail, setOrderDetail] = useState(null);
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().slice(0, 10));
  const [lines, setLines] = useState({});
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (!orderId) return;
    setError("");
    getOrder(orderId)
      .then((o) => {
        setOrderDetail(o);
        const l = {};
        o.items.forEach((it) => {
          if (it.remaining_quantity > 0) {
            l[it.order_item_id] = { quantity: it.remaining_quantity, unit_price: "", discount: 0, tax: 0 };
          }
        });
        setLines(l);
      })
      .catch((err) => setError(extractErrorMessage(err)));
  }, [orderId]);

  const invoiceableItems = orderDetail ? orderDetail.items.filter((it) => it.remaining_quantity > 0) : [];

  const lineTotal = (it) => {
    const l = lines[it.order_item_id] || {};
    return Number(l.quantity || 0) * Number(l.unit_price || 0) - Number(l.discount || 0) + Number(l.tax || 0);
  };

  const subtotal = invoiceableItems.reduce((s, it) => s + Number(lines[it.order_item_id]?.quantity || 0) * Number(lines[it.order_item_id]?.unit_price || 0), 0);
  const discount = invoiceableItems.reduce((s, it) => s + Number(lines[it.order_item_id]?.discount || 0), 0);
  const tax = invoiceableItems.reduce((s, it) => s + Number(lines[it.order_item_id]?.tax || 0), 0);
  const total = invoiceableItems.reduce((s, it) => s + lineTotal(it), 0);

  const submit = async (e) => {
    e.preventDefault();
    setError("");


    const itemsToSend = invoiceableItems
      .filter((it) => Number(lines[it.order_item_id]?.quantity) > 0)
      .map((it) => ({
        product_id: it.product_id,
        packaging_id: it.packaging_id,
        quantity: Number(lines[it.order_item_id].quantity),
        unit_price: Number(lines[it.order_item_id]?.unit_price || 0),
        discount: Number(lines[it.order_item_id]?.discount || 0),
        tax: Number(lines[it.order_item_id]?.tax || 0),
        line_total: lineTotal(it),
      }));

    if (itemsToSend.length === 0) {
      setError("Please enter a quantity for at least one item.");
      return;
    }

    setSaving(true);
    try {
      const result = await createInvoice({
        order_id: Number(orderId),
        invoice_number: invoiceNumber,
        invoice_date: invoiceDate,
        subtotal,
        discount,
        tax,
        total_amount: total,
        status: "UNPAID",
        items: itemsToSend,
      });
      toast.success(successMessage("Invoice", "created"));
      onCreated(result.invoice_id);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="New invoice" onClose={onClose} maxWidth={760}>
      <form onSubmit={submit}>
        <ErrorBanner message={error} />
        <div className="field-row">
          <div className="field">
            <label>Order</label>
            <select required value={orderId} onChange={(e) => setOrderId(e.target.value)}>
              {orders.map((o) => (
                <option key={o.order_id} value={o.order_id}>#{o.order_id} — {o.customer_name} ({o.order_date}) — {o.status.replaceAll("_", " ")}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Invoice number</label>
            <input required value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} />
          </div>
          <div className="field">
            <label>Invoice date</label>
            <input type="date" required value={invoiceDate} onChange={(e) => setInvoiceDate(e.target.value)} />
          </div>
        </div>

        {orderDetail && invoiceableItems.length === 0 && (
          <EmptyState label="Every item on this order has already been fully invoiced." />
        )}

        {invoiceableItems.length > 0 && (
          <>
            <div className="item-row" style={{ gridTemplateColumns: "1.4fr 0.9fr 0.7fr 0.7fr 0.7fr", fontWeight: 600, fontSize: 12.5, color: "var(--muted)" }}>
              <div>Product</div>
              <div className="num">Qty to invoice</div>
              <div className="num">Unit price</div>
              <div className="num">Discount</div>
              <div className="num">Tax</div>
            </div>
            {invoiceableItems.map((it) => (
              <div className="item-row" key={it.order_item_id} style={{ gridTemplateColumns: "1.4fr 0.9fr 0.7fr 0.7fr 0.7fr" }}>
                <div>
                  {it.product_name}
                  <div className="muted" style={{ fontSize: 11.5 }}>
                    {it.remaining_quantity} of {it.quantity} {it.unit_name} remaining
                  </div>
                </div>
                <input
                  type="number" min="0" max={it.remaining_quantity} step="any" required
                  value={lines[it.order_item_id]?.quantity ?? ""}
                  onChange={(e) => setLines((l) => ({ ...l, [it.order_item_id]: { ...l[it.order_item_id], quantity: e.target.value } }))}
                />
                <input
                  type="number" min="0" step="any" placeholder="Unit price" required
                  value={lines[it.order_item_id]?.unit_price ?? ""}
                  onChange={(e) => setLines((l) => ({ ...l, [it.order_item_id]: { ...l[it.order_item_id], unit_price: e.target.value } }))}
                />
                <input
                  type="number" min="0" step="any" placeholder="Discount"
                  value={lines[it.order_item_id]?.discount ?? 0}
                  onChange={(e) => setLines((l) => ({ ...l, [it.order_item_id]: { ...l[it.order_item_id], discount: e.target.value } }))}
                />
                <input
                  type="number" min="0" step="any" placeholder="Tax"
                  value={lines[it.order_item_id]?.tax ?? 0}
                  onChange={(e) => setLines((l) => ({ ...l, [it.order_item_id]: { ...l[it.order_item_id], tax: e.target.value } }))}
                />
              </div>
            ))}

            <div className="panel" style={{ marginTop: 16, marginBottom: 0 }}>
              <div className="field-row">
                <div><span className="muted">Subtotal</span><br />₹{subtotal.toLocaleString("en-IN")}</div>
                <div><span className="muted">Discount</span><br />₹{discount.toLocaleString("en-IN")}</div>
                <div><span className="muted">Tax</span><br />₹{tax.toLocaleString("en-IN")}</div>
                <div><strong>Total: ₹{total.toLocaleString("en-IN")}</strong></div>
              </div>
            </div>
          </>
        )}

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={saving || invoiceableItems.length === 0}>{saving ? "Creating invoice…" : "Create invoice"}</button>
        </div>
      </form>
    </Modal>
  );
}

export default function Invoices() {
  const navigate = useNavigate();
  const [invoices, setInvoices] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const { can } = useAuth();

  const load = () => {
    setLoading(true);
    setError("");

    Promise.all([listInvoices(), listOrders({ status: "CONFIRMED" }), listOrders({ status: "PARTIALLY_FULFILLED" })])
      .then(([inv, confirmed, partial]) => {
        setInvoices(inv);
        setOrders([...confirmed, ...partial]);
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Invoices</h1>
          <p>{invoices.length} invoice{invoices.length === 1 ? "" : "s"}</p>
        </div>
        {can("invoices:write") && (
          <button className="btn btn-primary" onClick={() => setShowCreate(true)} disabled={orders.length === 0}>
            <Plus size={15} /> New invoice
          </button>
        )}
      </div>
      {orders.length === 0 && !loading && (
        <p className="muted" style={{ marginTop: -10 }}>No confirmed or partially fulfilled orders are available to invoice yet.</p>
      )}

      <ErrorBanner message={error} />

      {loading ? (
        <Spinner />
      ) : invoices.length === 0 ? (
        <EmptyState label="No invoices found. Invoices are created from confirmed orders — confirm an order first, then create its invoice here." />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Invoice #</th>
                <th>Date</th>
                <th className="num">Total</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.invoice_id}>
                  <td><Link to={`/invoices/${inv.invoice_id}`}>{inv.invoice_number}</Link></td>
                  <td>{inv.invoice_date}</td>
                  <td className="num">₹{inv.total_amount.toLocaleString("en-IN")}</td>
                  <td><StatusBadge status={inv.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreateInvoiceModal
          orders={orders}
          onClose={() => setShowCreate(false)}
          onCreated={(invoiceId) => {
            setShowCreate(false);
            
            navigate(`/invoices/${invoiceId}`);
          }}
        />
      )}
    </div>
  );
}