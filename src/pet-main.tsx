import React from "react";
import ReactDOM from "react-dom/client";
import { PetApp } from "./components/Pet/PetApp";
import "./i18n";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <PetApp />
  </React.StrictMode>,
);
