import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import SplashGate from "./components/SplashGate";
import "./index.css";
import { installFriendlyValidation } from "./lib/formValidation";


installFriendlyValidation();

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <SplashGate>
      <App />
    </SplashGate>
  </React.StrictMode>
);