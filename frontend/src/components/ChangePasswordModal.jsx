import { useState } from "react";
import { changePassword } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { ErrorBanner } from "./Feedback";
import Modal from "./Modal";
import { useToast } from "./ToastProvider";
import { useAuth } from "../auth/AuthProvider";

export default function ChangePasswordModal({ onClose }) {
  const [form, setForm] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const toast = useToast();
  const { logout } = useAuth();

  const submit = async (event) => {
    event.preventDefault();
    setError("");

    if (form.newPassword !== form.confirmPassword) {
      setError("New passwords do not match.");
      return;
    }

    setSaving(true);
    try {
      const result = await changePassword({
        current_password: form.currentPassword,
        new_password: form.newPassword,
      });
      toast.success(result.message);
      onClose();
      logout();
    } catch (requestError) {
      setError(extractErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="Change my password" onClose={onClose}>
      <form onSubmit={submit}>
        <ErrorBanner message={error} />

        <div className="field">
          <label>Current password</label>
          <input
            type="password"
            value={form.currentPassword}
            onChange={(event) => setForm({ ...form, currentPassword: event.target.value })}
            autoComplete="current-password"
            required
            disabled={saving}
          />
        </div>
        <div className="field">
          <label>New password</label>
          <input
            type="password"
            value={form.newPassword}
            onChange={(event) => setForm({ ...form, newPassword: event.target.value })}
            autoComplete="new-password"
            minLength={10}
            required
            disabled={saving}
          />
        </div>
        <div className="field">
          <label>Confirm new password</label>
          <input
            type="password"
            value={form.confirmPassword}
            onChange={(event) => setForm({ ...form, confirmPassword: event.target.value })}
            autoComplete="new-password"
            minLength={10}
            required
            disabled={saving}
          />
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Changing password…" : "Change password"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
