import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Play } from "lucide-react";
import { api } from "@/api/client";
import type { CreateRunBody, RunDetail } from "@/api/types";

export function RunComposer() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [goal, setGoal] = useState("");
  const [autoApprove, setAutoApprove] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [maxSteps, setMaxSteps] = useState("");
  const [tags, setTags] = useState("");

  const mutation = useMutation<RunDetail, Error, CreateRunBody>({
    mutationFn: (body) => api.createRun(body),
    onSuccess: (run) => {
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
      navigate(`/runs/${run.id}`);
    },
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = goal.trim();
    if (!trimmed) return;
    const parsedSteps = maxSteps ? Number(maxSteps) : undefined;
    const parsedTags = tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    mutation.mutate({
      goal: trimmed,
      auto_approve: autoApprove,
      max_steps:
        parsedSteps && Number.isFinite(parsedSteps) ? parsedSteps : undefined,
      tags: parsedTags.length ? parsedTags : undefined,
    });
  };

  return (
    <form onSubmit={submit} className="card p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="mono-label">new run</span>
      </div>

      <textarea
        className="field min-h-[92px] resize-y font-sans text-sm leading-relaxed"
        placeholder="Describe the goal in plain language. e.g. Compare managed Postgres options for a small team and recommend one with reasoning and sources."
        value={goal}
        onChange={(e) => setGoal(e.target.value)}
        aria-label="Run goal"
      />

      <div className="mt-3 flex flex-wrap items-center gap-4">
        <label className="inline-flex cursor-pointer select-none items-center gap-2">
          <button
            type="button"
            role="switch"
            aria-checked={autoApprove}
            aria-label="Auto-approve tool actions"
            onClick={() => setAutoApprove((v) => !v)}
            className={
              "relative h-5 w-9 rounded-full border transition-colors " +
              (autoApprove
                ? "border-accent-cyan bg-accent-cyan/30"
                : "border-hairline bg-surface-raised")
            }
          >
            <span
              className={
                "absolute top-0.5 h-3.5 w-3.5 rounded-full transition-all " +
                (autoApprove
                  ? "left-[18px] bg-accent-cyan"
                  : "left-0.5 bg-content-faint")
              }
            />
          </button>
          <span className="font-mono text-[12px] text-content-muted">
            auto-approve
          </span>
        </label>

        <button
          type="button"
          className="inline-flex items-center gap-1 font-mono text-[12px] text-content-muted hover:text-content-primary"
          onClick={() => setShowAdvanced((v) => !v)}
          aria-expanded={showAdvanced}
        >
          <ChevronDown
            className={
              "h-3.5 w-3.5 transition-transform " +
              (showAdvanced ? "rotate-180" : "")
            }
          />
          advanced
        </button>

        <button
          type="submit"
          className="btn btn-primary ml-auto"
          disabled={mutation.isPending || !goal.trim()}
        >
          <Play className="h-3.5 w-3.5" />
          {mutation.isPending ? "Starting…" : "Run"}
        </button>
      </div>

      {showAdvanced && (
        <div className="mt-3 grid gap-3 border-t border-hairline pt-3 sm:grid-cols-2">
          <div>
            <label className="mono-label mb-1 block">max steps</label>
            <input
              className="field font-mono text-[13px]"
              inputMode="numeric"
              value={maxSteps}
              onChange={(e) =>
                setMaxSteps(e.target.value.replace(/[^0-9]/g, ""))
              }
              placeholder="e.g. 8"
            />
          </div>
          <div>
            <label className="mono-label mb-1 block">tags</label>
            <input
              className="field font-mono text-[13px]"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="comma,separated"
            />
          </div>
        </div>
      )}

      {mutation.isError && (
        <p className="mt-3 font-mono text-[12px] text-semantic-danger">
          {mutation.error.message}
        </p>
      )}
    </form>
  );
}
