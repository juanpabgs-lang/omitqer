import { NavLink, Outlet, useLocation } from "react-router-dom";

const LINKS = [
  { to: "/", label: "Historia" },
  { to: "/socio", label: "Socio" },
  { to: "/prestador", label: "Directo" },
  { to: "/integridad", label: "Integridad" },
  { to: "/caso", label: "Caso" },
  { to: "/direccion", label: "Dirección" },
  { to: "/operaciones", label: "Mesa" },
  { to: "/defensa", label: "951" },
  { to: "/sap", label: "SAP" },
  { to: "/discapacidad", label: "CUD" },
];

export function Layout() {
  const loc = useLocation();
  const member = loc.pathname.startsWith("/socio") || loc.pathname.startsWith("/prestador");
  return (
    <div className={member ? "min-h-screen bg-[#0b1020]" : "min-h-screen bg-paper"}>
      <header className="sticky top-0 z-20 border-b border-line/80 bg-paper/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between px-[clamp(16px,5.4vw,104px)] py-4">
          <NavLink to="/" className="flex items-center gap-2 text-[13px] tracking-tight">
            <span className="font-medium">Norfront</span>
            <span className="inline-block h-1.5 w-1.5 bg-mint" />
            <span className="text-mute">OMINT reintegros</span>
          </NavLink>
          <nav className="hidden flex-wrap items-center gap-4 text-[12px] text-mute md:flex">
            {LINKS.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) =>
                  isActive ? "text-ink underline decoration-mint underline-offset-4" : "hover:text-ink"
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <Outlet />
      <footer className="mt-24 border-t border-line px-[clamp(16px,5.4vw,104px)] py-6 text-[12px] text-mute">
        <div className="mx-auto flex max-w-[1440px] justify-between gap-6">
          <span>Datos sintéticos · Ley 25.326 · no es un sistema de OMINT</span>
          <span>Puertos 5178 / 8018</span>
        </div>
      </footer>
    </div>
  );
}
