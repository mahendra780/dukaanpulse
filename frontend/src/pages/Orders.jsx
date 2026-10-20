import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { listOrders, listCustomers, listProducts, createOrder, updateOrderStatus } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { Spinner, EmptyState, ErrorBanner } from "../components/Feedback";
import StatusBadge from "../components/StatusBadge";
import Modal from "../components/Modal";
import ProductPackagingSelect from "../components/ProductPackagingSelect";
import { useToast } from "../components/ToastProvider";
import { useConfirm } from "../components/ConfirmProvider";
import { useAuth } from "../auth/AuthProvider";
import { successMessage } from "../lib/messages";

const emptyItem = () => ({ product_id: "", packaging_id: "", quantity: "" });

const NEXT_STATUS = {
  PENDING: [["CONFIRMED", "Confirm"], ["CANCELLED", "Cancel"]],
  CONFIRMED: [["COMPLETED", "Complete"], ["CANCELLED", "Cancel"]],
  PARTIALLY_FULFILLED: [["COMPLETED", "Complete (waive rest)"], ["CANCELLED", "Cancel"]],
};

const BUSY_LABEL = {
  CONFIRMED: "Confirming…",
  COMPLETED: "Completing…",
  CANCELLED: "Cancelling…",
};

const DONE_VERB = {
  CONFIRMED: "confirmed",
  COMPLETED: "completed",
  CANCELLED: "cancelled",
};

function availableStock(products, productId, packagingId) {
  const product = products.find((p) => p.product_id === Number(productId));
  if (!product) return null;
  const packaging = product.packaging.find((pk) => pk.packaging_id === Number(packagingId));
  if (!packaging) return null;
  return {
    quantity: Number(product.current_stock || 0) / Number(packaging.conversion_to_base),
    unit: packaging.unit_name,
  };
}

function CreateOrderModal({ customers, products, onClose, onCreated }) {
  const [customerId, setCustomerId] = useState(customers[0]?.customer_id ?? "");
  const [orderDate, setOrderDate] = useState(new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState([emptyItem()]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const toast = useToast();

  const updateItem = (i, patch) => setItems((rows) => rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await createOrder({
        customer_id: Number(customerId),
        order_date: orderDate,
        status: "PENDING",
        notes: notes || null,
        items: items.map((it) => ({
          product_id: Number(it.product_id),
          packaging_id: Number(it.packaging_id),
          quantity: Number(it.quantity),
        })),
      });
      toast.success(successMessage("Order", "created"));
      onCreated();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="New order" onClose={onClose} maxWidth={680}>
      <form onSubmit={submit}>
        <ErrorBanner message={error} />
        <div className="field-row">
          <div className="field">
            <label>Customer</label>
            <select required value={customerId} onChange={(e) => setCustomerId(e.target.value)}>
              {customers.map((c) => <option key={c.customer_id} value={c.customer_id}>{c.customer_name}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Order date</label>
            <input type="date" required value={orderDate} onChange={(e) => setOrderDate(e.target.value)} />
          </div>
        </div>
        <div className="field">
          <label>Notes</label>
          <input value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>

        <label>Items</label>
        {items.map((it, i) => {
          const stock = availableStock(products, it.product_id, it.packaging_id);
          return (
            <div key={i}>
              <div className="item-row" style={{ gridTemplateColumns: "1.6fr 1fr 0.8fr auto", marginBottom: 2 }}>
                <ProductPackagingSelect
                  products={products}
                  productId={it.product_id}
                  packagingId={it.packaging_id}
                  filterPackaging={(pk) => pk.is_sale_unit}
                  onChange={(productId, packagingId) => updateItem(i, { product_id: productId, packaging_id: packagingId })}
                />
                <input type="number" min="0.001" step="any" placeholder="Qty" required value={it.quantity} onChange={(e) => updateItem(i, { quantity: e.target.value })} />
                <button type="button" className="btn btn-ghost" onClick={() => setItems((rows) => rows.filter((_, idx) => idx !== i))} disabled={items.length === 1}>
                  <Trash2 size={15} />
                </button>
              </div>
              {stock && (
                <p className="muted" style={{ margin: "0 0 8px", fontSize: 12 }}>
                  Available: {stock.quantity} {stock.unit}
                  {Number(it.quantity) > stock.quantity && (
                    <span style={{ color: "var(--amber)", fontWeight: 600 }}> — more than currently in stock; order can still be confirmed, but won't be deliverable until stock arrives</span>
                  )}
                </p>
              )}
            </div>
          );
        })}
        <button type="button" className="btn btn-secondary" onClick={() => setItems((rows) => [...rows, emptyItem()])}>
          <Plus size={14} /> Add item
        </button>

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? "Creating order…" : "Create order"}</button>
        </div>
      </form>
    </Modal>
  );
}

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [busy, setBusy] = useState(null); // { id, status } of the row action in flight
  const toast = useToast();
  const confirm = useConfirm();
  const { can } = useAuth();

  const load = () => {
    setLoading(true);
    setError("");
    Promise.all([listOrders({ status: statusFilter || undefined }), listCustomers(), listProducts()])
      .then(([o, c, p]) => {
        setOrders(o);
        setCustomers(c);
        setProducts(p);
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [statusFilter]);

  const transition = async (order, status) => {
    if (status === "CANCELLED") {
      const ok = await confirm({
        title: "Cancel this order?",
        description: `The order for ${order.customer_name} (${order.order_date}) will be cancelled. This can't be undone.`,
        confirmLabel: "Cancel order",
        cancelLabel: "Keep order",
        danger: true,
      });
      if (!ok) return;
    } else if (status === "COMPLETED") {
      const ok = await confirm({
        title: "Mark this order as completed?",
        description: `The order for ${order.customer_name} (${order.order_date}) will be closed, and no further invoices can be created for it. Any quantity not yet invoiced will be waived.`,
        confirmLabel: "Mark completed",
      });
      if (!ok) return;
    }

    setBusy({ id: order.order_id, status });
    try {
      await updateOrderStatus(order.order_id, status);
      toast.success(successMessage("Order", DONE_VERB[status]));
      load();
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  // INACTIVE customers/products can't be used on a NEW order (the
  // backend enforces this too), so they aren't offered.
  const activeCustomers = customers.filter((c) => c.status === "ACTIVE");
  const activeProducts = products.filter((p) => p.status === "ACTIVE");

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Orders</h1>
          <p>{orders.length} order{orders.length === 1 ? "" : "s"}</p>
        </div>
        {can("orders:write") && (
          <button className="btn btn-primary" onClick={() => setShowCreate(true)} disabled={activeCustomers.length === 0 || activeProducts.length === 0}>
            <Plus size={15} /> New order
          </button>
        )}
      </div>

      <div className="table-toolbar">
        <select style={{ maxWidth: 200 }} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="PENDING">Pending</option>
          <option value="CONFIRMED">Confirmed</option>
          <option value="PARTIALLY_FULFILLED">Partially fulfilled</option>
          <option value="COMPLETED">Completed</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
      </div>

      <ErrorBanner message={error} />

      {loading ? (
        <Spinner />
      ) : orders.length === 0 ? (
        <EmptyState
          label={
            statusFilter
              ? "No orders match the selected filter."
              : "No orders found. Create your first order to start billing customers."
          }
        />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Customer</th>
                <th>Date</th>
                <th className="num">Invoiced total</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => {
                const rowBusy = busy?.id === o.order_id;
                return (
                  <tr key={o.order_id}>
                    <td>{o.customer_name}</td>
                    <td>{o.order_date}</td>
                    <td className="num">₹{o.total_amount.toLocaleString("en-IN")}</td>
                    <td><StatusBadge status={o.status} /></td>
                    <td>
                      <div className="section-actions">
                        {can("orders:write") && (NEXT_STATUS[o.status] || []).map(([next, label]) => (
                          <button
                            key={next}
                            className={next === "CANCELLED" ? "btn btn-ghost" : "btn btn-secondary"}
                            disabled={rowBusy}
                            onClick={() => transition(o, next)}
                          >
                            {rowBusy && busy.status === next ? BUSY_LABEL[next] : label}
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreateOrderModal
          customers={activeCustomers}
          products={activeProducts}
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            load();
          }}
        />
      )}
    </div>
  );
}