import clsx from "clsx";
import type { ReactNode } from "react";

interface SectionLabelProps {
  children: ReactNode;
  right?: ReactNode;
  className?: string;
}

export function SectionLabel({ children, right, className }: SectionLabelProps) {
  return (
    <div
      className={clsx(
        "flex items-center justify-between border-b border-hairline px-4 py-3",
        className,
      )}
    >
      <span className="mono-label text-content-muted">{children}</span>
      {right}
    </div>
  );
}
