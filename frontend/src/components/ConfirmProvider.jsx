import { createContext, useCallback, useContext, useRef, useState } from "react";
import Modal from "./Modal";

const ConfirmContext = createContext(null);

export function ConfirmProvider({ children }) {
  const [request, setRequest] = useState(null);
  const resolver = useRef(null);

  // confirm({ title, description, confirmLabel, cancelLabel, danger })
  // -> Promise<boolean>. Usage: const ok = await confirm({...}); if (!ok) return;
  const confirm = useCallback((options) => {
    return new Promise((resolve) => {
      resolver.current = resolve;
      setRequest(options);
    });
  }, []);

  const settle = (result) => {
    resolver.current?.(result);
    resolver.current = null;
    setRequest(null);
  };

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {request && (
        <Modal title={request.title} onClose={() => settle(false)}>
          <p style={{ fontSize: 13.5, lineHeight: 1.5 }}>{request.description}</p>
          <div className="modal-footer">
            {/* For a destructive action the SAFE button gets initial focus,
                so an accidental Enter press cancels instead of deleting. */}
            <button className="btn btn-secondary" onClick={() => settle(false)} autoFocus={!!request.danger}>
              {request.cancelLabel || "Cancel"}
            </button>
            <button
              className={request.danger ? "btn btn-danger" : "btn btn-primary"}
              onClick={() => settle(true)}
              autoFocus={!request.danger}
            >
              {request.confirmLabel || "Confirm"}
            </button>
          </div>
        </Modal>
      )}
    </ConfirmContext.Provider>
  );
}

// Returns an async confirm(options) function -- await it, proceed only if true.
export function useConfirm() {
  const ctx = useContext(ConfirmContext);
  if (!ctx) throw new Error("useConfirm must be used within a ConfirmProvider");
  return ctx;
}