import type { ReactNode } from "react";

export function PhoneFrame({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto w-[390px] max-w-full overflow-hidden rounded-[28px] border border-white/10 bg-[#0e1630] shadow-[0_0_0_1px_rgba(255,255,255,0.04)]">
      <div className="flex items-center justify-between px-5 py-3 text-[11px] text-white/50">
        <span>9:41</span>
        <span className="h-3 w-20 rounded-full bg-white/10" />
        <span>5G</span>
      </div>
      <div className="min-h-[640px] bg-white text-[#111]">{children}</div>
    </div>
  );
}
