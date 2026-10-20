import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import {
  createUser,
  listUsers,
  resetUserPassword,
  updateUser,
} from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { EmptyState, ErrorBanner, Spinner } from "../components/Feedback";
import Modal from "../components/Modal";
import StatusBadge from "../components/StatusBadge";
import { useConfirm } from "../components/ConfirmProvider";
import { useToast } from "../components/ToastProvider";
import { successMessage } from "../lib/messages";

const ROLES = ["ADMIN", "SALES", "WAREHOUSE", "ACCOUNTS", "VIEWER"];
const USER_STATUSES = ["ACTIVE", "INACTIVE"];

function RoleBadge({ role }) {
  return <span className="badge badge-accent">{role}</span>;
}

function formatLastLogin(value) {
  if (!value) return "Never";
  return new Date(value).toLocaleString();
}

function CreateUserModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    username: "",
    full_name: "",
    role: "VIEWER",
    initial_password: "",
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const toast = useToast();

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setSaving(true);

    try {
      await createUser(form);
      toast.success(successMessage("User", "added"));
      onCreated();
    } catch (requestError) {
      setError(extractErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="Add user" onClose={onClose}>
      <form onSubmit={submit}>
        <ErrorBanner message={error} />
        <div className="field-row">
          <div className="field">
            <label>Username</label>
            <input
              value={form.username}
              onChange={(event) => setForm({ ...form, username: event.target.value })}
              autoComplete="username"
              maxLength={50}
              required
              disabled={saving}
            />
          </div>
          <div className="field">
            <label>Full name</label>
            <input
              value={form.full_name}
              onChange={(event) => setForm({ ...form, full_name: event.target.value })}
              autoComplete="name"
              maxLength={100}
              required
              disabled={saving}
            />
          </div>
        </div>
        <div className="field-row">
          <div className="field">
            <label>Role</label>
            <select
              value={form.role}
              onChange={(event) => setForm({ ...form, role: event.target.value })}
              disabled={saving}
            >
              {ROLES.map((role) => <option key={role} value={role}>{role}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Initial password</label>
            <input
              type="password"
              value={form.initial_password}
              onChange={(event) => setForm({ ...form, initial_password: event.target.value })}
              autoComplete="new-password"
              minLength={10}
              required
              disabled={saving}
            />
          </div>
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Adding user…" : "Add user"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function EditUserModal({ user, onClose, onUpdated }) {
  const [form, setForm] = useState({ role: user.role, status: user.status });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const toast = useToast();
  const confirm = useConfirm();

  const submit = async (event) => {
    event.preventDefault();
    setError("");

    const changes = {};
    if (form.role !== user.role) changes.role = form.role;
    if (form.status !== user.status) changes.status = form.status;
    if (Object.keys(changes).length === 0) {
      onClose();
      return;
    }

    const deactivating = user.status === "ACTIVE" && form.status === "INACTIVE";
    const demoting = user.role === "ADMIN" && form.role !== "ADMIN";
    if (deactivating || demoting) {
      const action = deactivating ? "deactivate" : "demote";
      const description = deactivating && demoting
        ? `${user.full_name} will be deactivated and lose administrator access.`
        : deactivating
          ? `${user.full_name} will no longer be able to sign in. Their existing session will be rejected on its next request.`
          : `${user.full_name} will lose administrator access.`;
      const confirmed = await confirm({
        title: `${action.charAt(0).toUpperCase()}${action.slice(1)} this user?`,
        description,
        confirmLabel: action.charAt(0).toUpperCase() + action.slice(1),
        danger: true,
      });
      if (!confirmed) return;
    }

    setSaving(true);
    try {
      await updateUser(user.user_id, changes);
      toast.success(successMessage("User", "updated"));
      onUpdated();
    } catch (requestError) {
      setError(extractErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={`Edit ${user.full_name}`} onClose={onClose}>
      <form onSubmit={submit}>
        <ErrorBanner message={error} />
        <div className="field">
          <label>Username</label>
          <input value={user.username} disabled />
        </div>
        <div className="field-row">
          <div className="field">
            <label>Role</label>
            <select
              value={form.role}
              onChange={(event) => setForm({ ...form, role: event.target.value })}
              disabled={saving}
            >
              {ROLES.map((role) => <option key={role} value={role}>{role}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Status</label>
            <select
              value={form.status}
              onChange={(event) => setForm({ ...form, status: event.target.value })}
              disabled={saving}
            >
              {USER_STATUSES.map((userStatus) => (
                <option key={userStatus} value={userStatus}>{userStatus}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Saving user…" : "Save changes"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ResetPasswordModal({ user, onClose, onReset }) {
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const toast = useToast();

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }

    setSaving(true);
    try {
      const result = await resetUserPassword(user.user_id, { new_password: newPassword });
      toast.success(result.message);
      onReset();
    } catch (requestError) {
      setError(extractErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={`Reset password for ${user.full_name}`} onClose={onClose}>
      <form onSubmit={submit}>
        <ErrorBanner message={error} />
        <div className="field">
          <label>New password</label>
          <input
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
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
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
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
            {saving ? "Resetting password…" : "Reset password"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export default function Users() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [resettingUser, setResettingUser] = useState(null);

  const load = () => {
    setLoading(true);
    setError("");
    listUsers()
      .then(setUsers)
      .catch((requestError) => setError(extractErrorMessage(requestError)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Users</h1>
          <p>{users.length} user{users.length === 1 ? "" : "s"}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          <Plus size={15} /> Add user
        </button>
      </div>

      <ErrorBanner message={error} />

      {loading ? (
        <Spinner />
      ) : users.length === 0 ? (
        <EmptyState label="No users found. Add a user to give someone access." />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Status</th>
                <th>Last sign-in</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.user_id}>
                  <td>
                    <div>{user.full_name}</div>
                    <div className="muted" style={{ fontSize: 12 }}>{user.username}</div>
                  </td>
                  <td><RoleBadge role={user.role} /></td>
                  <td><StatusBadge status={user.status} /></td>
                  <td>{formatLastLogin(user.last_login_at)}</td>
                  <td>
                    <div className="section-actions">
                      <button className="btn btn-ghost" onClick={() => setEditingUser(user)}>
                        Edit access
                      </button>
                      <button className="btn btn-ghost" onClick={() => setResettingUser(user)}>
                        Reset password
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreateUserModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            load();
          }}
        />
      )}
      {editingUser && (
        <EditUserModal
          user={editingUser}
          onClose={() => setEditingUser(null)}
          onUpdated={() => {
            setEditingUser(null);
            load();
          }}
        />
      )}
      {resettingUser && (
        <ResetPasswordModal
          user={resettingUser}
          onClose={() => setResettingUser(null)}
          onReset={() => {
            setResettingUser(null);
            load();
          }}
        />
      )}
    </div>
  );
}
