import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { listSuppliers, createSupplier, updateSupplier } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { Spinner, EmptyState, ErrorBanner } from "../components/Feedback";
import StatusBadge from "../components/StatusBadge";
import Modal from "../components/Modal";
import { useToast } from "../components/ToastProvider";
import { useConfirm } from "../components/ConfirmProvider";
import { useAuth } from "../auth/AuthProvider";
import { successMessage } from "../lib/messages";

function CreateSupplierModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ supplier_name: "", phone: "", address: "", gst_number: "", payment_terms_days: 0, status: "ACTIVE" });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const toast = useToast();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await createSupplier({ ...form, payment_terms_days: Number(form.payment_terms_days) });
      toast.success(successMessage("Supplier", "added"));
      onCreated();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="Add supplier" onClose={onClose}>
      <form onSubmit={submit}>
        <ErrorBanner message={error} />
        <div className="field-row">
          <div className="field">
            <label>Supplier name</label>
            <input required minLength={2} value={form.supplier_name} onChange={(e) => setForm({ ...form, supplier_name: e.target.value })} />
          </div>
          <div className="field">
            <label>Phone</label>
            <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </div>
        </div>
        <div className="field">
          <label>Address</label>
          <input required value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
        </div>
        <div className="field-row">
          <div className="field">
            <label>GST number</label>
            <input maxLength={15} value={form.gst_number} onChange={(e) => setForm({ ...form, gst_number: e.target.value })} />
          </div>
          <div className="field">
            <label>Payment terms (days)</label>
            <input type="number" min="0" value={form.payment_terms_days} onChange={(e) => setForm({ ...form, payment_terms_days: e.target.value })} />
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? "Adding supplier…" : "Create supplier"}</button>
        </div>
      </form>
    </Modal>
  );
}

export default function Suppliers() {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const toast = useToast();
  const confirm = useConfirm();
  const { can } = useAuth();

  const load = () => {
    setLoading(true);
    listSuppliers()
      .then(setSuppliers)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const toggleStatus = async (supplier) => {
    const activating = supplier.status !== "ACTIVE";

    if (!activating) {
      const ok = await confirm({
        title: "Deactivate this supplier?",
                description: `"${supplier.supplier_name}" will no longer be offered when creating new purchases. Existing purchases and payments are not affected, and you can reactivate them anytime.`,
        confirmLabel: "Deactivate",
        danger: true,
      });
      if (!ok) return;
    }

    setBusyId(supplier.supplier_id);
    try {
      await updateSupplier(supplier.supplier_id, { status: activating ? "ACTIVE" : "INACTIVE" });
      toast.success(successMessage("Supplier", activating ? "activated" : "deactivated"));
      load();
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Suppliers</h1>
          <p>{suppliers.length} supplier{suppliers.length === 1 ? "" : "s"}</p>
        </div>
        {can("suppliers:write") && (
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            <Plus size={15} /> Add supplier
          </button>
        )}
      </div>

      <ErrorBanner message={error} />

      {loading ? (
        <Spinner />
      ) : suppliers.length === 0 ? (
        <EmptyState label="No suppliers found. Suppliers you add will appear here." />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Phone</th>
                <th>GST</th>
                <th className="num">Terms (days)</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((s) => (
                <tr key={s.supplier_id}>
                  <td>{s.supplier_name}</td>
                  <td>{s.phone || "—"}</td>
                  <td>{s.gst_number || "—"}</td>
                  <td className="num">{s.payment_terms_days}</td>
                  <td><StatusBadge status={s.status} /></td>
                  <td>
                    {can("suppliers:write") && (
                      <button className="btn btn-ghost" disabled={busyId === s.supplier_id} onClick={() => toggleStatus(s)}>
                        {busyId === s.supplier_id
                          ? (s.status === "ACTIVE" ? "Deactivating…" : "Activating…")
                          : (s.status === "ACTIVE" ? "Deactivate" : "Activate")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreateSupplierModal
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