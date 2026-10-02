import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { listDeliveries, listInvoices, createDelivery, updateDeliveryStatus } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { Spinner, EmptyState, ErrorBanner } from "../components/Feedback";
import StatusBadge from "../components/StatusBadge";
import Modal from "../components/Modal";

// Mirrors the backend's valid_transitions map exactly
// (app/routers/deliveries.py -> update_delivery_status).
// FAILED is not terminal -- it can retry back to OUT_FOR_DELIVERY.
// DELIVERED and CANCELLED are the only terminal states.
const NEXT_STATUS = {
  PENDING: [["DISPATCHED", "Dispatch"], ["CANCELLED", "Cancel"]],
  DISPATCHED: [["OUT_FOR_DELIVERY", "Out for delivery"], ["FAILED", "Mark failed"], ["CANCELLED", "Cancel"]],
  OUT_FOR_DELIVERY: [["DELIVERED", "Mark delivered"], ["FAILED", "Mark failed"], ["CANCELLED", "Cancel"]],
  FAILED: [["OUT_FOR_DELIVERY", "Retry delivery"], ["CANCELLED", "Cancel"]],
};

function CreateDeliveryModal({ deliverableInvoices, onClose, onCreated }) {
  const [invoiceId, setInvoiceId] = useState(deliverableInvoices[0]?.invoice_id ?? "");
  const [deliveryDate, setDeliveryDate] = useState(new Date().toISOString().slice(0, 10));
  const [deliveryAddress, setDeliveryAddress] = useState("");
  const [addressTouched, setAddressTouched] = useState(false);
  const [vehicleNumber, setVehicleNumber] = useState("");
  const [driverName, setDriverName] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  // Auto-fill from the selected invoice's customer address -- only
  // while the person hasn't typed their own address, so switching
  // invoices doesn't clobber a manual edit they already made.
  useEffect(() => {
    if (addressTouched) return;
    const invoice = deliverableInvoices.find((inv) => inv.invoice_id === Number(invoiceId));
    setDeliveryAddress(invoice?.customer_address || "");
  }, [invoiceId, deliverableInvoices, addressTouched]);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      // Always created as PENDING — the DISPATCHED/DELIVERED/CANCELLED
      // transitions happen afterwards via the status action, matching
      // the workflow the status-transition endpoint enforces.
      await createDelivery({
        invoice_id: Number(invoiceId),
        delivery_date: deliveryDate || null,
        status: "PENDING",
        delivery_address: deliveryAddress,
        vehicle_number: vehicleNumber || null,
        driver_name: driverName || null,
        notes: notes || null,
      });
      onCreated();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="New delivery" onClose={onClose}>
      <form onSubmit={submit}>
        <ErrorBanner message={error} />
        <div className="field-row">
          <div className="field">
            <label>Invoice</label>
            <select required value={invoiceId} onChange={(e) => { setInvoiceId(e.target.value); setAddressTouched(false); }}>
              {deliverableInvoices.map((inv) => (
                <option key={inv.invoice_id} value={inv.invoice_id}>
                  {inv.invoice_number}{inv.customer_name ? ` — ${inv.customer_name}` : ""}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Delivery date</label>
            <input type="date" value={deliveryDate} onChange={(e) => setDeliveryDate(e.target.value)} />
          </div>
        </div>
        <div className="field">
          <label>Delivery address</label>
          <input
            required
            value={deliveryAddress}
            onChange={(e) => { setDeliveryAddress(e.target.value); setAddressTouched(true); }}
          />
          <p className="muted" style={{ fontSize: 11.5, marginTop: 4, marginBottom: 0 }}>
            Auto-filled from the customer's saved address — edit if this delivery goes somewhere else.
          </p>
        </div>
        <div className="field-row">
          <div className="field">
            <label>Vehicle number</label>
            <input value={vehicleNumber} onChange={(e) => setVehicleNumber(e.target.value)} />
          </div>
          <div className="field">
            <label>Driver name</label>
            <input value={driverName} onChange={(e) => setDriverName(e.target.value)} />
          </div>
        </div>
        <div className="field">
          <label>Notes</label>
          <input value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? "Saving…" : "Create delivery"}</button>
        </div>
      </form>
    </Modal>
  );
}

export default function Deliveries() {
  const [deliveries, setDeliveries] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [busyId, setBusyId] = useState(null);

  const load = () => {
    setLoading(true);
    Promise.all([listDeliveries(), listInvoices()])
      .then(([d, inv]) => {
        setDeliveries(d);
        setInvoices(inv);
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  // Backend allows a new delivery once every existing delivery for
  // that invoice is CANCELLED (a fresh attempt after a failed/cancelled
  // one) -- only an ACTIVE (non-cancelled) delivery blocks a new one.
  const invoicesWithActiveDelivery = new Set(
    deliveries.filter((d) => d.status !== "CANCELLED").map((d) => d.invoice_id)
  );
  const deliverableInvoices = invoices.filter((inv) => !invoicesWithActiveDelivery.has(inv.invoice_id));

  // GET /deliveries/ has no status query param (unlike purchases/orders),
  // so filtering is done client-side here rather than re-fetching.
  const visibleDeliveries = statusFilter ? deliveries.filter((d) => d.status === statusFilter) : deliveries;

  const transition = async (id, status) => {
    setBusyId(id);
    setError("");
    try {
      await updateDeliveryStatus(id, status);
      load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Deliveries</h1>
          <p>{deliveries.length} delivery{deliveries.length === 1 ? "" : "ies"}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)} disabled={deliverableInvoices.length === 0}>
          <Plus size={15} /> New delivery
        </button>
      </div>
      {deliverableInvoices.length === 0 && !loading && (
        <p className="muted" style={{ marginTop: -10 }}>Every invoice already has an active (non-cancelled) delivery.</p>
      )}

      <div className="table-toolbar">
        <select style={{ maxWidth: 200 }} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="PENDING">Pending</option>
          <option value="DISPATCHED">Dispatched</option>
          <option value="OUT_FOR_DELIVERY">Out for delivery</option>
          <option value="DELIVERED">Delivered</option>
          <option value="FAILED">Failed</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
      </div>

      <ErrorBanner message={error} />

      {loading ? (
        <Spinner />
      ) : visibleDeliveries.length === 0 ? (
        <EmptyState label="No deliveries found" />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Date</th>
                <th>Address</th>
                <th>Vehicle</th>
                <th>Driver</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {visibleDeliveries.map((d) => (
                <tr key={d.delivery_id}>
                  <td>{d.invoice_number || "—"}</td>
                  <td>{d.delivery_date || "—"}</td>
                  <td>{d.delivery_address}</td>
                  <td>{d.vehicle_number || "—"}</td>
                  <td>{d.driver_name || "—"}</td>
                  <td><StatusBadge status={d.status} /></td>
                  <td>
                    <div className="section-actions">
                      {(NEXT_STATUS[d.status] || []).map(([next, label]) => (
                        <button
                          key={next}
                          className={next === "CANCELLED" ? "btn btn-ghost" : "btn btn-secondary"}
                          disabled={busyId === d.delivery_id}
                          onClick={() => transition(d.delivery_id, next)}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreateDeliveryModal
          deliverableInvoices={deliverableInvoices}
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