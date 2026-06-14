import React from "react";
import ReactDOM from "react-dom/client";
import { SettingsApp } from "./components/Settings/SettingsApp";
import "./i18n";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <SettingsApp />
  </React.StrictMode>,
);
