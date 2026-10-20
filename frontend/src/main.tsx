import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import "./index.css";
import { Caso } from "./routes/Caso";
import { Defensa } from "./routes/Defensa";
import { Direccion } from "./routes/Direccion";
import { Expediente } from "./routes/Expediente";
import { Hub } from "./routes/Hub";
import { Integridad } from "./routes/Integridad";
import { Operaciones } from "./routes/Operaciones";
import { Prestador } from "./routes/Prestador";
import { Sap } from "./routes/Sap";
import { Socio } from "./routes/Socio";
import { Verificar } from "./routes/Verificar";
import { Discapacidad } from "./routes/Discapacidad";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Hub />} />
          <Route path="/socio" element={<Socio />} />
          <Route path="/prestador" element={<Prestador />} />
          <Route path="/integridad" element={<Integridad />} />
          <Route path="/caso" element={<Caso />} />
          <Route path="/direccion" element={<Direccion />} />
          <Route path="/operaciones" element={<Operaciones />} />
          <Route path="/expediente/:id" element={<Expediente />} />
          <Route path="/defensa" element={<Defensa />} />
          <Route path="/sap" element={<Sap />} />
          <Route path="/verificar/:hash" element={<Verificar />} />
          <Route path="/discapacidad" element={<Discapacidad />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
