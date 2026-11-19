import { Component } from "react";

// Catches a crash while RENDERING a page, so one broken component shows
// a readable message (with the sidebar still usable) instead of a blank
// white screen. It does not catch errors inside event handlers or API
// calls -- those are already handled by the toast/banner flow.
export default class ErrorBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    // The technical detail stays in the developer console only.
    console.error("Unhandled UI error:", error, info?.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className="empty-state" role="alert">
        <h2 style={{ margin: "0 0 8px", color: "var(--ink)", fontSize: 16 }}>
          Something went wrong while showing this page.
        </h2>
        <p style={{ margin: "0 0 16px" }}>Please reload the page. If the problem continues, try again in a moment.</p>
        <button className="btn btn-primary" onClick={() => window.location.reload()}>
          Reload page
        </button>
      </div>
    );
  }
}