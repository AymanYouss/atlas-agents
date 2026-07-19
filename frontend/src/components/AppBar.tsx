import { NavLink } from "react-router-dom";
import clsx from "clsx";
import { Github } from "lucide-react";

const GITHUB_URL = "https://github.com/AymanYouss/atlas-agents";

function navClass({ isActive }: { isActive: boolean }): string {
  return clsx(
    "font-mono text-[12px] uppercase tracking-wider transition-colors",
    isActive
      ? "text-accent-cyan"
      : "text-content-muted hover:text-content-primary",
  );
}

export function AppBar() {
  return (
    <header className="sticky top-0 z-20 border-b border-hairline bg-base/85 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-[1600px] items-center justify-between px-6">
        <NavLink to="/" className="flex items-baseline gap-3">
          <span className="flex items-center gap-2">
            <span
              className="status-dot animate-pulse-dot bg-accent-cyan"
              aria-hidden
            />
            <span className="font-mono text-[15px] font-semibold tracking-[0.28em] text-content-primary">
              ATLAS
            </span>
          </span>
          <span className="hidden font-mono text-[10px] uppercase tracking-[0.14em] text-content-faint sm:inline">
            multi-agent control plane
          </span>
        </NavLink>

        <nav className="flex items-center gap-6">
          <NavLink to="/runs" className={navClass}>
            Runs
          </NavLink>
          <NavLink to="/benchmarks" className={navClass}>
            Benchmarks
          </NavLink>
          <NavLink to="/demo" className={navClass}>
            Demo
          </NavLink>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer noopener"
            className="text-content-muted transition-colors hover:text-content-primary"
            aria-label="View Atlas on GitHub"
          >
            <Github className="h-4 w-4" />
          </a>
        </nav>
      </div>
    </header>
  );
}
