import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { Check, ChevronUp, KeyRound, LogOut } from "lucide-react";

const ROLE_LABELS = {
  OWNER: "Owner",
  ADMIN: "Admin",
  SALES: "Sales",
  WAREHOUSE: "Warehouse",
  ACCOUNTS: "Accounts",
  VIEWER: "Viewer",
};

const roleLabel = (role) =>
  ROLE_LABELS[role] || (role ? role.charAt(0) + role.slice(1).toLowerCase() : "");

// One line at the bottom of the sidebar (avatar, name, role). Clicking it
// opens a menu above it with the account actions.
export default function UserMenu({ user, onChangePassword, onLogout, onSwitchWorkspace }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const triggerRef = useRef(null);
  const menuRef = useRef(null);
  const location = useLocation();

  const activeWorkspaceId = user.workspace?.workspace_id;
  const workspaces = user.memberships || [];
  const role = roleLabel(user.workspace?.role);
  const initial = (user.full_name || user.username || "?").trim().charAt(0).toUpperCase();

  // Close when the page changes.
  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  // Close on a click outside; move focus into the menu when it opens.
  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = (event) => {
      if (rootRef.current && !rootRef.current.contains(event.target)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    menuRef.current?.querySelector('[role^="menuitem"]')?.focus();
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  const handleKeyDown = (event) => {
    if (!open) return;

    if (event.key === "Escape") {
      // Stop here so the mobile drawer does not also close.
      event.stopPropagation();
      setOpen(false);
      triggerRef.current?.focus();
      return;
    }

    if (event.key === "Tab") {
      setOpen(false);
      return;
    }

    if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
      const items = [...(menuRef.current?.querySelectorAll('[role^="menuitem"]') || [])];
      if (items.length === 0) return;
      event.preventDefault();
      const current = items.indexOf(document.activeElement);
      let next = current;
      if (event.key === "ArrowDown") next = (current + 1) % items.length;
      if (event.key === "ArrowUp") next = (current - 1 + items.length) % items.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = items.length - 1;
      items[next].focus();
    }
  };

  const run = (action) => () => {
    setOpen(false);
    action();
  };

  return (
    <div className="user-menu" ref={rootRef} onKeyDown={handleKeyDown}>
      {open && (
        <div className="user-menu-popover" role="menu" aria-label="Account" ref={menuRef}>
          <div className="user-menu-head">
            <div className="user-menu-name">{user.full_name}</div>
            <div className="user-menu-meta">
              {[user.workspace?.business_name, role].filter(Boolean).join(" · ")}
            </div>
          </div>

          {workspaces.length > 1 && (
            <>
              <div className="user-menu-divider" role="separator" />
              <div className="user-menu-label" id="user-menu-workspaces">Workspaces</div>
              {workspaces.map((workspace) => {
                const active = workspace.workspace_id === activeWorkspaceId;
                return (
                  <button
                    key={workspace.workspace_id}
                    type="button"
                    role="menuitemradio"
                    aria-checked={active}
                    className="user-menu-item"
                    onClick={run(() => onSwitchWorkspace(workspace.workspace_id))}
                  >
                    <span className="user-menu-item-text">{workspace.business_name}</span>
                    {active && <Check size={16} className="user-menu-check" aria-hidden="true" />}
                  </button>
                );
              })}
            </>
          )}

          <div className="user-menu-divider" role="separator" />
          <button type="button" role="menuitem" className="user-menu-item" onClick={run(onChangePassword)}>
            <KeyRound size={16} aria-hidden="true" />
            Change password
          </button>
          <button type="button" role="menuitem" className="user-menu-item" onClick={run(onLogout)}>
            <LogOut size={16} aria-hidden="true" />
            Logout
          </button>
        </div>
      )}

      <button
        ref={triggerRef}
        type="button"
        className={"user-menu-trigger" + (open ? " is-open" : "")}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="user-avatar" aria-hidden="true">{initial}</span>
        <span className="user-menu-text">
          <span className="user-menu-trigger-name">{user.full_name}</span>
          <span className="user-menu-trigger-role">{role}</span>
        </span>
        <ChevronUp size={16} className="user-menu-chevron" aria-hidden="true" />
      </button>
    </div>
  );
}