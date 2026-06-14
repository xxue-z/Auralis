import React from "react";
import ReactDOM from "react-dom/client";
import { ChatApp } from "./components/Chat/ChatApp";
import "./i18n";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <ChatApp />
  </React.StrictMode>,
);
