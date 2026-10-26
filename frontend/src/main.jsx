import React from "react";
import ReactDOM from "react-dom/client";
import { MotionConfig } from "framer-motion";

import App from "./App.jsx";
import { AppProvider } from "./lib/AppContext.jsx";
import "./styles/base.css";
import "./styles/shell.css";
import "./styles/vistas.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <MotionConfig reducedMotion="user">
      <AppProvider>
        <App />
      </AppProvider>
    </MotionConfig>
  </React.StrictMode>
);
