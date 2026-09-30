import { useEffect, useState, useMemo } from "react";
import { Plus } from "lucide-react";
import { listPayments, listInvoices, createPayment } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { Spinner, EmptyState, ErrorBanner } from "../components/Feedback";
import Modal from "../components/Modal";

const PAYMENT_METHODS = ["CASH", "UPI", "BANK_TRANSFER", "CHEQUE"];
const currency = (n) => `₹${Number(n || 0).toLocaleString("en-IN")}`;

function CreatePaymentModal({ payableInvoices, remainingByInvoice, onClose, onCreated }) {
  const [invoiceId, setInvoiceId] = useState(payableInvoices[0]?.invoice_id ?? "");
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().slice(0, 10));
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState(PAYMENT_METHODS[0]);
  const [referenceNumber, setReferenceNumber] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const remaining = remainingByInvoice[invoiceId] ?? 0;

  const submit = async (e) => {
    e.preventDefault();
    setError("");

    if (Number(amount) > remaining) {
      setError(`Payment exceeds remaining amount. Remaining: ${remaining}`);
      return;
    }

    setSaving(true);
    try {
      await createPayment({
        invoice_id: Number(invoiceId),
        payment_date: paymentDate,
        amount: Number(amount),
        payment_method: method,
        reference_number: referenceNumber || null,
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
    <Modal title="Record payment" onClose={onClose}>
      <form onSubmit={submit}>
        <ErrorBanner message={error} />
        <div className="field-row">
          <div className="field">
            <label>Invoice</label>
            <select required value={invoiceId} onChange={(e) => setInvoiceId(e.target.value)}>
              {payableInvoices.map((inv) => (
                <option key={inv.invoice_id} value={inv.invoice_id}>{inv.invoice_number}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Payment date</label>
            <input type="date" required value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} />
          </div>
        </div>

        <p className="muted" style={{ marginTop: -8, marginBottom: 14 }}>Remaining on this invoice: {currency(remaining)}</p>

        <div className="field-row">
          <div className="field">
            <label>Amount</label>
            <input type="number" min="0.01" step="any" max={remaining} required value={amount} onChange={(e) => setAmount(e.target.value)} />
          </div>
          <div className="field">
            <label>Payment method</label>
            <select required value={method} onChange={(e) => setMethod(e.target.value)}>
              {PAYMENT_METHODS.map((m) => <option key={m} value={m}>{m.replaceAll("_", " ")}</option>)}
            </select>
          </div>
        </div>
        <div className="field-row">
          <div className="field">
            <label>Reference number</label>
            <input value={referenceNumber} onChange={(e) => setReferenceNumber(e.target.value)} />
          </div>
          <div className="field">
            <label>Notes</label>
            <input value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={saving || remaining <= 0}>{saving ? "Saving…" : "Record payment"}</button>
        </div>
      </form>
    </Modal>
  );
}

export default function Payments() {
  const [payments, setPayments] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([listPayments(), listInvoices()])
      .then(([p, inv]) => {
        setPayments(p);
        setInvoices(inv);
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);
  const remainingByInvoice = useMemo(() => {
    const paidByInvoice = {};
    payments.forEach((p) => {
      paidByInvoice[p.invoice_id] = (paidByInvoice[p.invoice_id] || 0) + Number(p.amount);
    });
    const map = {};
    invoices.forEach((inv) => {
      map[inv.invoice_id] = Number(inv.total_amount) - (paidByInvoice[inv.invoice_id] || 0);
    });
    return map;
  }, [payments, invoices]);

  const payableInvoices = invoices.filter(
    (inv) => inv.status !== "CANCELLED" && (remainingByInvoice[inv.invoice_id] ?? 0) > 0
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Payments</h1>
          <p>{payments.length} payment{payments.length === 1 ? "" : "s"}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)} disabled={payableInvoices.length === 0}>
          <Plus size={15} /> Record payment
        </button>
      </div>
      {payableInvoices.length === 0 && !loading && (
        <p className="muted" style={{ marginTop: -10 }}>No invoices currently have a balance due.</p>
      )}

      <ErrorBanner message={error} />

      {loading ? (
        <Spinner />
      ) : payments.length === 0 ? (
        <EmptyState label="No payments recorded yet" />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Date</th>
                <th className="num">Amount</th>
                <th>Method</th>
                <th>Reference</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {payments.map((p) => (
                <tr key={p.payment_id}>
                  <td>{p.invoice_number || "—"}</td>
                  <td>{p.payment_date}</td>
                  <td className="num">{currency(p.amount)}</td>
                  <td>
                    {p.payment_method === "RETURN_CREDIT" ? (
                      <span className="badge badge-accent">Return credit</span>
                    ) : (
                      p.payment_method?.replaceAll("_", " ")
                    )}
                  </td>
                  <td>{p.reference_number || "—"}</td>
                  <td>{p.notes || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreatePaymentModal
          payableInvoices={payableInvoices}
          remainingByInvoice={remainingByInvoice}
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