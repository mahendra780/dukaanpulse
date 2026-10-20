import { useEffect, useState, useMemo } from "react";
import { Plus } from "lucide-react";
import { listPurchasePayments, listPurchases, createPurchasePayment } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { Spinner, EmptyState, ErrorBanner } from "../components/Feedback";
import Modal from "../components/Modal";
import { useToast } from "../components/ToastProvider";
import { useAuth } from "../auth/AuthProvider";
import { successMessage } from "../lib/messages";

const PAYMENT_METHODS = ["CASH", "UPI", "BANK_TRANSFER", "CHEQUE"];
const currency = (n) => `₹${Number(n || 0).toLocaleString("en-IN")}`;

function CreatePurchasePaymentModal({ payablePurchases, remainingByPurchase, onClose, onCreated }) {
  const [purchaseId, setPurchaseId] = useState(payablePurchases[0]?.purchase_id ?? "");
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().slice(0, 10));
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState(PAYMENT_METHODS[0]);
  const [referenceNumber, setReferenceNumber] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const toast = useToast();

  const remaining = remainingByPurchase[purchaseId] ?? 0;

  const submit = async (e) => {
    e.preventDefault();
    setError("");

    if (Number(amount) > remaining) {
      setError(`Payment can't be more than the remaining amount (${currency(remaining)}).`);
      return;
    }

    setSaving(true);
    try {
      await createPurchasePayment({
        purchase_id: Number(purchaseId),
        payment_date: paymentDate,
        amount: Number(amount),
        payment_method: method,
        reference_number: referenceNumber || null,
        notes: notes || null,
      });
      toast.success(successMessage("Supplier payment", "recorded"));
      onCreated();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="Record supplier payment" onClose={onClose}>
      <form onSubmit={submit}>
        <ErrorBanner message={error} />
        <div className="field-row">
          <div className="field">
            <label>Purchase</label>
            <select required value={purchaseId} onChange={(e) => setPurchaseId(e.target.value)}>
              {payablePurchases.map((p) => (
                <option key={p.purchase_id} value={p.purchase_id}>{p.supplier_invoice_no} — {p.supplier_name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Payment date</label>
            <input type="date" required value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} />
          </div>
        </div>

        <p className="muted" style={{ marginTop: -8, marginBottom: 14 }}>Remaining on this purchase: {currency(remaining)}</p>

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
          <button type="submit" className="btn btn-primary" disabled={saving || remaining <= 0}>{saving ? "Recording payment…" : "Record payment"}</button>
        </div>
      </form>
    </Modal>
  );
}

export default function PurchasePayments() {
  const [payments, setPayments] = useState([]);
  const [purchases, setPurchases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const { can } = useAuth();

  const load = () => {
    setLoading(true);
    setError("");
    Promise.all([listPurchasePayments(), listPurchases()])
      .then(([p, pu]) => {
        setPayments(p);
        setPurchases(pu);
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const remainingByPurchase = useMemo(() => {
    const paidByPurchase = {};
    payments.forEach((p) => {
      paidByPurchase[p.purchase_id] = (paidByPurchase[p.purchase_id] || 0) + Number(p.amount);
    });
    const map = {};
    purchases.forEach((p) => {
      map[p.purchase_id] = Number(p.total_amount) - (paidByPurchase[p.purchase_id] || 0);
    });
    return map;
  }, [payments, purchases]);


  const payablePurchases = purchases.filter(
    (p) => p.status !== "CANCELLED" && (remainingByPurchase[p.purchase_id] ?? 0) > 0
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Supplier payments</h1>
          <p>{payments.length} payment{payments.length === 1 ? "" : "s"} to suppliers</p>
        </div>
        {can("purchase_payments:write") && (
          <button className="btn btn-primary" onClick={() => setShowCreate(true)} disabled={payablePurchases.length === 0}>
            <Plus size={15} /> Record payment
          </button>
        )}
      </div>
      {payablePurchases.length === 0 && !loading && (
        <p className="muted" style={{ marginTop: -10 }}>No purchases currently have a balance due.</p>
      )}

      <ErrorBanner message={error} />

      {loading ? (
        <Spinner />
      ) : payments.length === 0 ? (
        <EmptyState label="No supplier payments recorded yet. Payments you make against purchases will appear here." />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Supplier</th>
                <th>Purchase invoice #</th>
                <th>Date</th>
                <th className="num">Amount</th>
                <th>Method</th>
                <th>Reference</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {payments.map((p) => (
                <tr key={p.purchase_payment_id}>
                  <td>{p.supplier_name || "—"}</td>
                  <td>{p.supplier_invoice_no || "—"}</td>
                  <td>{p.payment_date}</td>
                  <td className="num">{currency(p.amount)}</td>
                  <td>{p.payment_method?.replaceAll("_", " ")}</td>
                  <td>{p.reference_number || "—"}</td>
                  <td>{p.notes || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreatePurchasePaymentModal
          payablePurchases={payablePurchases}
          remainingByPurchase={remainingByPurchase}
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