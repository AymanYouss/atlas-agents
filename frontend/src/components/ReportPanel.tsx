import { type ReactNode, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ExternalLink } from "lucide-react";
import type { Report } from "@/api/types";
import { ConfidenceGauge } from "./ConfidenceGauge";

interface ReportPanelProps {
  report: Report | null;
  draft: string;
  streaming: boolean;
}

// Turn "[1]" style markers in text nodes into superscript anchor links that
// jump to the matching citation entry.
function linkifyCitations(children: ReactNode): ReactNode {
  if (typeof children === "string") {
    const parts = children.split(/(\[\d+\])/g);
    return parts.map((part, i) => {
      const m = /^\[(\d+)\]$/.exec(part);
      if (m) {
        return (
          <sup key={i}>
            <a
              href={`#citation-${m[1]}`}
              className="text-accent-cyan no-underline hover:underline"
            >
              [{m[1]}]
            </a>
          </sup>
        );
      }
      return part;
    });
  }
  if (Array.isArray(children)) {
    return children.map((child, i) => (
      <span key={i}>{linkifyCitations(child)}</span>
    ));
  }
  return children;
}

export function ReportPanel({ report, draft, streaming }: ReportPanelProps) {
  const markdown = report?.body_markdown ?? draft;

  const content = useMemo(() => {
    if (!markdown) return null;
    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p>{linkifyCitations(children)}</p>,
          li: ({ children }) => <li>{linkifyCitations(children)}</li>,
          td: ({ children }) => <td>{linkifyCitations(children)}</td>,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer noopener">
              {children}
            </a>
          ),
        }}
      >
        {markdown}
      </ReactMarkdown>
    );
  }, [markdown]);

  if (!markdown) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 px-6 py-12 text-center">
        <div className="flex gap-1" aria-hidden>
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="h-1.5 w-1.5 rounded-full bg-content-faint animate-pulse-dot"
              style={{ animationDelay: `${i * 0.2}s` }}
            />
          ))}
        </div>
        <p className="max-w-[26ch] font-mono text-xs text-content-faint">
          the report will be synthesized here once the agents finish gathering
          and reviewing evidence
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-5 py-4">
        {report && (
          <div className="mb-4 flex items-start justify-between gap-4 border-b border-hairline pb-4">
            <p className="text-[13px] leading-relaxed text-content-muted">
              {report.summary}
            </p>
            <div className="shrink-0">
              <ConfidenceGauge value={report.confidence} />
            </div>
          </div>
        )}

        <div className="report-prose">{content}</div>

        {streaming && !report && (
          <span className="ml-0.5 inline-block h-4 w-2 animate-pulse-dot bg-accent-cyan align-text-bottom" />
        )}

        {report && report.citations.length > 0 && (
          <div className="mt-8 border-t border-hairline pt-4">
            <div className="mono-label mb-3">sources</div>
            <ol className="space-y-2">
              {report.citations.map((c) => (
                <li
                  key={c.marker}
                  id={`citation-${c.marker}`}
                  className="scroll-mt-4 rounded-md border border-hairline bg-surface-raised px-3 py-2"
                >
                  <div className="flex items-baseline gap-2">
                    <span className="font-mono text-[11px] text-accent-cyan">
                      [{c.marker}]
                    </span>
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="group inline-flex items-center gap-1 text-[13px] font-medium text-content-primary hover:text-accent-cyan"
                    >
                      {c.title}
                      <ExternalLink className="h-3 w-3 opacity-0 transition-opacity group-hover:opacity-100" />
                    </a>
                  </div>
                  <div className="ml-8 mt-0.5 font-mono text-[10px] text-content-faint">
                    {c.source}
                  </div>
                  {c.snippet && (
                    <p className="ml-8 mt-1 text-[12px] leading-relaxed text-content-muted">
                      {c.snippet}
                    </p>
                  )}
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </div>
  );
}
