import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { listReturns, listInvoices, getInvoice, createReturn, approveReturn, receiveReturn } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { Spinner, EmptyState, ErrorBanner } from "../components/Feedback";
import StatusBadge from "../components/StatusBadge";
import Modal from "../components/Modal";


const REASONS = ["DAMAGED", "EXPIRED", "WRONG_PRODUCT", "QUALITY_ISSUE", "EXCESS_QUANTITY", "OTHER"];
const CONDITIONS = ["RESELLABLE", "DAMAGED", "EXPIRED", "SUPPLIER_RETURN"];

function CreateReturnModal({ returnableInvoices, onClose, onCreated }) {
  const [invoiceId, setInvoiceId] = useState(returnableInvoices[0]?.invoice_id ?? "");
  const [invoiceDetail, setInvoiceDetail] = useState(null);
  const [returnDate, setReturnDate] = useState(new Date().toISOString().slice(0, 10));
  const [reason, setReason] = useState(REASONS[0]);
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState({});
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!invoiceId) return;
    getInvoice(invoiceId).then(setInvoiceDetail);
  }, [invoiceId]);

  const returnableItems = invoiceDetail ? invoiceDetail.items.filter((it) => it.returnable_quantity > 0) : [];

  const updateLine = (invoiceItemId, patch) =>
    setLines((l) => ({ ...l, [invoiceItemId]: { ...l[invoiceItemId], ...patch } }));

  const submit = async (e) => {
    e.preventDefault();
    setError("");

    const itemsToSend = returnableItems
      .filter((it) => Number(lines[it.invoice_item_id]?.quantity) > 0)
      .map((it) => ({
        product_id: it.product_id,
        packaging_id: it.packaging_id,
        quantity: Number(lines[it.invoice_item_id].quantity),
        condition: lines[it.invoice_item_id]?.condition || CONDITIONS[0],
      }));

    if (itemsToSend.length === 0) {
      setError("Enter a quantity for at least one item.");
      return;
    }

    setSaving(true);
    try {
      await createReturn({
        invoice_id: Number(invoiceId),
        return_date: returnDate,
        reason,
        status: "REQUESTED",
        notes: notes || null,
        items: itemsToSend,
      });
      onCreated();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="New return" onClose={onClose} maxWidth={720}>
      <form onSubmit={submit}>
        <ErrorBanner message={error} />
        <div className="field-row">
          <div className="field">
            <label>Invoice</label>
            <select required value={invoiceId} onChange={(e) => { setInvoiceId(e.target.value); setLines({}); }}>
              {returnableInvoices.map((inv) => (
                <option key={inv.invoice_id} value={inv.invoice_id}>{inv.invoice_number}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Return date</label>
            <input type="date" required value={returnDate} onChange={(e) => setReturnDate(e.target.value)} />
          </div>
          <div className="field">
            <label>Reason</label>
            <select required value={reason} onChange={(e) => setReason(e.target.value)}>
              {REASONS.map((r) => <option key={r} value={r}>{r.replaceAll("_", " ")}</option>)}
            </select>
          </div>
        </div>
        <div className="field">
          <label>Notes</label>
          <input value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>

        {invoiceDetail && returnableItems.length === 0 && (
          <EmptyState label="Every item on this invoice has already been fully returned." />
        )}

        {returnableItems.length > 0 && (
          <>
            <div className="item-row" style={{ gridTemplateColumns: "1.4fr 0.8fr 1fr", fontWeight: 600, fontSize: 12.5, color: "var(--muted)" }}>
              <div>Product</div>
              <div className="num">Qty to return</div>
              <div>Condition</div>
            </div>
            {returnableItems.map((it) => (
              <div className="item-row" key={it.invoice_item_id} style={{ gridTemplateColumns: "1.4fr 0.8fr 1fr" }}>
                <div>
                  {it.product_name}
                  <div className="muted" style={{ fontSize: 11.5 }}>
                    {it.returnable_quantity} of {it.quantity} {it.unit_name} returnable
                  </div>
                </div>
                <input
                  type="number" min="0" max={it.returnable_quantity} step="any"
                  placeholder="0"
                  value={lines[it.invoice_item_id]?.quantity ?? ""}
                  onChange={(e) => updateLine(it.invoice_item_id, { quantity: e.target.value })}
                />
                <select
                  value={lines[it.invoice_item_id]?.condition || CONDITIONS[0]}
                  onChange={(e) => updateLine(it.invoice_item_id, { condition: e.target.value })}
                >
                  {CONDITIONS.map((c) => <option key={c} value={c}>{c.replaceAll("_", " ")}</option>)}
                </select>
              </div>
            ))}
          </>
        )}

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={saving || returnableItems.length === 0}>{saving ? "Saving…" : "Create return"}</button>
        </div>
      </form>
    </Modal>
  );
}

export default function Returns() {
  const [returns, setReturns] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [busyId, setBusyId] = useState(null);

  const load = () => {
    setLoading(true);
    Promise.all([listReturns(), listInvoices()])
      .then(([r, inv]) => {
        setReturns(r);
        setInvoices(inv);
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const returnableInvoices = invoices.filter((inv) => inv.status !== "CANCELLED");

  const act = async (fn, id) => {
    setBusyId(id);
    setError("");
    try {
      await fn(id);
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
          <h1>Returns</h1>
          <p>{returns.length} return{returns.length === 1 ? "" : "s"}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)} disabled={returnableInvoices.length === 0}>
          <Plus size={15} /> New return
        </button>
      </div>

      <ErrorBanner message={error} />

      {loading ? (
        <Spinner />
      ) : returns.length === 0 ? (
        <EmptyState label="No returns found" />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Date</th>
                <th>Reason</th>
                <th>Items</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {returns.map((r) => (
                <tr key={r.return_id}>
                  <td>{r.invoice_number || "—"}</td>
                  <td>{r.return_date}</td>
                  <td>{r.reason.replaceAll("_", " ")}</td>
                  <td>{r.items.map((it) => `${it.product_name} (${it.quantity} ${it.unit_name})`).join(", ")}</td>
                  <td><StatusBadge status={r.status} /></td>
                  <td>
                    <div className="section-actions">
                      {r.status === "REQUESTED" && (
                        <button className="btn btn-secondary" disabled={busyId === r.return_id} onClick={() => act(approveReturn, r.return_id)}>Approve</button>
                      )}
                      {r.status === "APPROVED" && (
                        <button className="btn btn-secondary" disabled={busyId === r.return_id} onClick={() => act(receiveReturn, r.return_id)}>Receive</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreateReturnModal
          returnableInvoices={returnableInvoices}
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