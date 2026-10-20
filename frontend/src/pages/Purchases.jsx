import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { listPurchases, listSuppliers, listProducts, createPurchase, updatePurchaseStatus, getPurchase, receivePurchaseItems } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { Spinner, EmptyState, ErrorBanner } from "../components/Feedback";
import StatusBadge from "../components/StatusBadge";
import Modal from "../components/Modal";
import ProductPackagingSelect from "../components/ProductPackagingSelect";
import { useToast } from "../components/ToastProvider";
import { useConfirm } from "../components/ConfirmProvider";
import { useAuth } from "../auth/AuthProvider";
import { successMessage } from "../lib/messages";

const emptyItem = () => ({ product_id: "", packaging_id: "", quantity: "", unit_price: "", discount: "", tax: "" });
const lineTotal = (it) => Number(it.quantity || 0) * Number(it.unit_price || 0) - Number(it.discount || 0) + Number(it.tax || 0);

function CreatePurchaseModal({ suppliers, products, onClose, onCreated }) {
  const [supplierId, setSupplierId] = useState(suppliers[0]?.supplier_id ?? "");
  const [purchaseDate, setPurchaseDate] = useState(new Date().toISOString().slice(0, 10));
  const [invoiceNo, setInvoiceNo] = useState("");
  const [items, setItems] = useState([emptyItem()]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const toast = useToast();

  const updateItem = (i, patch) => setItems((rows) => rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));

  const subtotal = items.reduce((s, it) => s + Number(it.quantity || 0) * Number(it.unit_price || 0), 0);
  const discount = items.reduce((s, it) => s + Number(it.discount || 0), 0);
  const tax = items.reduce((s, it) => s + Number(it.tax || 0), 0);
  const total = items.reduce((s, it) => s + lineTotal(it), 0);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await createPurchase({
        supplier_id: Number(supplierId),
        purchase_date: purchaseDate,
        supplier_invoice_no: invoiceNo,
        subtotal,
        discount,
        tax,
        total_amount: total,
        status: "PENDING",
        items: items.map((it) => ({
          product_id: Number(it.product_id),
          packaging_id: Number(it.packaging_id),
          quantity: Number(it.quantity),
          // Always 0 at creation -- receiving happens ONLY through
          // "Receive items" / "Mark fully received" afterward, which
          // correctly create inventory movements.
          received_quantity: 0,
          unit_price: Number(it.unit_price),
          discount: Number(it.discount || 0),
          tax: Number(it.tax || 0),
          line_total: lineTotal(it),
        })),
      });
      toast.success(successMessage("Purchase", "created"));
      onCreated();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="New purchase" onClose={onClose} maxWidth={760}>
      <form onSubmit={submit}>
        <ErrorBanner message={error} />
        <div className="field-row">
          <div className="field">
            <label>Supplier</label>
            <select required value={supplierId} onChange={(e) => setSupplierId(e.target.value)}>
              {suppliers.map((s) => <option key={s.supplier_id} value={s.supplier_id}>{s.supplier_name}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Purchase date</label>
            <input type="date" required value={purchaseDate} onChange={(e) => setPurchaseDate(e.target.value)} />
          </div>
          <div className="field">
            <label>Supplier invoice no.</label>
            <input required value={invoiceNo} onChange={(e) => setInvoiceNo(e.target.value)} />
          </div>
        </div>

        <label>Items</label>
        {items.map((it, i) => (
          <div className="item-row" key={i} style={{ gridTemplateColumns: "1.5fr 0.8fr 0.8fr 0.7fr 0.7fr auto" }}>
            <ProductPackagingSelect
              products={products}
              productId={it.product_id}
              packagingId={it.packaging_id}
              onChange={(productId, packagingId) => updateItem(i, { product_id: productId, packaging_id: packagingId })}
            />
            <input type="number" min="0.001" step="any" placeholder="Qty" required value={it.quantity} onChange={(e) => updateItem(i, { quantity: e.target.value })} />
            <input type="number" min="0" step="any" placeholder="Price" required value={it.unit_price} onChange={(e) => updateItem(i, { unit_price: e.target.value })} />
            <input type="number" min="0" step="any" placeholder="Discount" value={it.discount} onChange={(e) => updateItem(i, { discount: e.target.value })} />
            <input type="number" min="0" step="any" placeholder="Tax" value={it.tax} onChange={(e) => updateItem(i, { tax: e.target.value })} />
            <button type="button" className="btn btn-ghost" onClick={() => setItems((rows) => rows.filter((_, idx) => idx !== i))} disabled={items.length === 1}>
              <Trash2 size={15} />
            </button>
          </div>
        ))}
        <button type="button" className="btn btn-secondary" onClick={() => setItems((rows) => [...rows, emptyItem()])}>
          <Plus size={14} /> Add item
        </button>

        <div className="panel" style={{ marginTop: 16, marginBottom: 0 }}>
          <div className="field-row">
            <div><span className="muted">Subtotal</span><br />₹{subtotal.toLocaleString("en-IN")}</div>
            <div><span className="muted">Discount</span><br />₹{discount.toLocaleString("en-IN")}</div>
            <div><span className="muted">Tax</span><br />₹{tax.toLocaleString("en-IN")}</div>
            <div><strong>Total: ₹{total.toLocaleString("en-IN")}</strong></div>
          </div>
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? "Creating purchase…" : "Create purchase"}</button>
        </div>
      </form>
    </Modal>
  );
}

function ReceiveItemsModal({ purchaseId, onClose, onReceived }) {
  const [purchase, setPurchase] = useState(null);
  const [receiving, setReceiving] = useState({}); // purchase_item_id -> quantity arriving now
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const toast = useToast();

  useEffect(() => {
    getPurchase(purchaseId)
      .then(setPurchase)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [purchaseId]);

  const submit = async (e) => {
    e.preventDefault();
    setError("");

    const items = Object.entries(receiving)
      .map(([purchase_item_id, quantity]) => ({ purchase_item_id: Number(purchase_item_id), quantity: Number(quantity) }))
      .filter((it) => it.quantity > 0);

    if (items.length === 0) {
      setError("Please enter a quantity for at least one item.");
      return;
    }

    setSaving(true);
    try {
      await receivePurchaseItems(purchaseId, items);
      toast.success(successMessage("Items", "received"));
      onReceived();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="Receive items" onClose={onClose} maxWidth={680}>
      {loading ? (
        <Spinner />
      ) : !purchase ? (
        <ErrorBanner message={error || "We couldn't load this purchase. Please close this window and try again."} />
      ) : (
        <form onSubmit={submit}>
          <ErrorBanner message={error} />
          <p className="muted" style={{ marginTop: -4 }}>
            Enter how much is arriving right now for each item — you can receive the rest later in a separate shipment.
          </p>
          <div className="item-row" style={{ gridTemplateColumns: "1.6fr 0.8fr 0.8fr 0.8fr", fontWeight: 600, fontSize: 12.5, color: "var(--muted)" }}>
            <div>Product</div>
            <div className="num">Ordered</div>
            <div className="num">Already received</div>
            <div className="num">Receiving now</div>
          </div>
          {purchase.items.map((it) => {
            const remaining = it.quantity - it.received_quantity;
            return (
              <div className="item-row" key={it.purchase_item_id} style={{ gridTemplateColumns: "1.6fr 0.8fr 0.8fr 0.8fr" }}>
                <div>{it.product_name}</div>
                <div className="num muted">{it.quantity} {it.unit_name}</div>
                <div className="num muted">{it.received_quantity} {it.unit_name}</div>
                <input
                  type="number" min="0" max={remaining} step="any"
                  placeholder="0"
                  disabled={remaining <= 0}
                  value={receiving[it.purchase_item_id] ?? ""}
                  onChange={(e) => setReceiving((r) => ({ ...r, [it.purchase_item_id]: e.target.value }))}
                />
              </div>
            );
          })}

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? "Receiving…" : "Receive"}</button>
          </div>
        </form>
      )}
    </Modal>
  );
}

export default function Purchases() {
  const [purchases, setPurchases] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [receivingId, setReceivingId] = useState(null);
  const [busy, setBusy] = useState(null); // { id, status } of the row action in flight
  const toast = useToast();
  const confirm = useConfirm();
  const { can } = useAuth();

  const load = () => {
    setLoading(true);
    setError("");
    Promise.all([listPurchases({ status: statusFilter || undefined }), listSuppliers(), listProducts()])
      .then(([pu, su, pr]) => {
        setPurchases(pu);
        setSuppliers(su);
        setProducts(pr);
      })
      // Page-level failure stays a persistent banner; quick row actions
      // below use toasts instead.
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [statusFilter]);

  const transition = async (purchase, status) => {
    if (status === "CANCELLED") {
      const ok = await confirm({
        title: "Cancel this purchase?",
        description: `Purchase ${purchase.supplier_invoice_no} from ${purchase.supplier_name} will be cancelled. Anything already received stays in stock; only the outstanding portion is cancelled. This can't be undone.`,
        confirmLabel: "Cancel purchase",
        cancelLabel: "Keep purchase",
        danger: true,
      });
      if (!ok) return;
    } else if (status === "RECEIVED") {
      const ok = await confirm({
        title: purchase.status === "PARTIALLY_RECEIVED" ? "Receive the remaining items?" : "Mark as fully received?",
        description: "The outstanding quantity of every item will be added to your stock. This can't be undone.",
        confirmLabel: "Receive into stock",
      });
      if (!ok) return;
    }

    setBusy({ id: purchase.purchase_id, status });
    try {
      await updatePurchaseStatus(purchase.purchase_id, status);
      toast.success(successMessage("Purchase", status === "RECEIVED" ? "marked as received" : "cancelled"));
      load();
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  // INACTIVE suppliers/products can't be used on a NEW purchase (the
  // backend enforces this too), so they aren't offered.
  const activeSuppliers = suppliers.filter((s) => s.status === "ACTIVE");
  const activeProducts = products.filter((p) => p.status === "ACTIVE");

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Purchases</h1>
          <p>{purchases.length} purchase{purchases.length === 1 ? "" : "s"}</p>
        </div>
        {can("purchases:write") && (
          <button className="btn btn-primary" onClick={() => setShowCreate(true)} disabled={activeSuppliers.length === 0 || activeProducts.length === 0}>
            <Plus size={15} /> New purchase
          </button>
        )}
      </div>

      <div className="table-toolbar">
        <select style={{ maxWidth: 200 }} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="PENDING">Pending</option>
          <option value="PARTIALLY_RECEIVED">Partially received</option>
          <option value="RECEIVED">Received</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
      </div>

      <ErrorBanner message={error} />

      {loading ? (
        <Spinner />
      ) : purchases.length === 0 ? (
        <EmptyState
          label={
            statusFilter
              ? "No purchases match the selected filter."
              : "No purchases found. Create your first purchase to start tracking stock coming in."
          }
        />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Supplier</th>
                <th>Date</th>
                <th>Invoice #</th>
                <th className="num">Total</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {purchases.map((p) => {
                const rowBusy = busy?.id === p.purchase_id;
                return (
                  <tr key={p.purchase_id}>
                    <td>{p.supplier_name}</td>
                    <td>{p.purchase_date}</td>
                    <td>{p.supplier_invoice_no}</td>
                    <td className="num">₹{p.total_amount.toLocaleString("en-IN")}</td>
                    <td><StatusBadge status={p.status} /></td>
                    <td>
                      {can("purchases:write") && (p.status === "PENDING" || p.status === "PARTIALLY_RECEIVED") && (
                        <div className="section-actions">
                          <button className="btn btn-secondary" disabled={rowBusy} onClick={() => setReceivingId(p.purchase_id)}>Receive items…</button>
                          <button className="btn btn-secondary" disabled={rowBusy} onClick={() => transition(p, "RECEIVED")}>
                            {rowBusy && busy.status === "RECEIVED"
                              ? "Receiving…"
                              : p.status === "PARTIALLY_RECEIVED" ? "Receive remaining" : "Mark fully received"}
                          </button>
                          <button className="btn btn-ghost" disabled={rowBusy} onClick={() => transition(p, "CANCELLED")}>
                            {rowBusy && busy.status === "CANCELLED" ? "Cancelling…" : "Cancel"}
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreatePurchaseModal
          suppliers={activeSuppliers}
          products={activeProducts}
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            load();
          }}
        />
      )}

      {receivingId && (
        <ReceiveItemsModal
          purchaseId={receivingId}
          onClose={() => setReceivingId(null)}
          onReceived={() => {
            setReceivingId(null);
            load();
          }}
        />
      )}
    </div>
  );
}