import { useState } from "react";
import { Check, Pencil, ShieldCheck, X } from "lucide-react";
import type {
  ApprovalRequest,
  ApprovalSubmission,
  ApprovalDecisionInput,
} from "@/api/types";

interface ApprovalGateProps {
  requests: ApprovalRequest[];
  submitting: boolean;
  onSubmit: (submission: ApprovalSubmission) => void;
}

function ApprovalCard({
  request,
  submitting,
  onDecide,
}: {
  request: ApprovalRequest;
  submitting: boolean;
  onDecide: (decision: ApprovalDecisionInput) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [instruction, setInstruction] = useState(request.proposed_action);
  const [note, setNote] = useState("");

  return (
    <div className="rounded-md border border-accent-amber/40 bg-accent-amber/[0.06] p-4">
      <div className="mb-2 flex items-center gap-2">
        <ShieldCheck className="h-4 w-4 text-accent-amber" />
        <span className="font-mono text-[11px] uppercase tracking-wider text-accent-amber">
          approval required
        </span>
        <span className="font-mono text-[11px] text-content-faint">
          {request.step_id}
        </span>
      </div>

      <p className="text-[13px] leading-relaxed text-content-primary">
        {request.reason}
      </p>

      <div className="mt-3">
        <div className="mono-label mb-1">proposed action</div>
        <p className="rounded border border-hairline bg-base px-3 py-2 font-mono text-[12px] leading-relaxed text-content-muted">
          {request.proposed_action}
        </p>
      </div>

      {editing && (
        <div className="mt-3 space-y-2">
          <div>
            <label className="mono-label mb-1 block">edited instruction</label>
            <textarea
              className="field font-mono text-[12px]"
              rows={3}
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
            />
          </div>
          <div>
            <label className="mono-label mb-1 block">note (optional)</label>
            <input
              className="field font-mono text-[12px]"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="context for the reviewer log"
            />
          </div>
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        {editing ? (
          <>
            <button
              type="button"
              className="btn btn-amber"
              disabled={submitting}
              onClick={() =>
                onDecide({
                  decision: "edited",
                  edited_instruction: instruction,
                  note: note || undefined,
                })
              }
            >
              <Check className="h-3.5 w-3.5" />
              Submit edit
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => setEditing(false)}
            >
              Cancel
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              className="btn btn-primary"
              disabled={submitting}
              onClick={() => onDecide({ decision: "approved" })}
            >
              <Check className="h-3.5 w-3.5" />
              Approve
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              disabled={submitting}
              onClick={() => onDecide({ decision: "rejected" })}
            >
              <X className="h-3.5 w-3.5" />
              Reject
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              disabled={submitting}
              onClick={() => setEditing(true)}
            >
              <Pencil className="h-3.5 w-3.5" />
              Edit
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export function ApprovalGate({
  requests,
  submitting,
  onSubmit,
}: ApprovalGateProps) {
  if (requests.length === 0) return null;

  const decide = (request: ApprovalRequest, decision: ApprovalDecisionInput) => {
    onSubmit({ decisions: { [request.step_id]: decision } });
  };

  return (
    <div className="space-y-3">
      {requests.map((request) => (
        <ApprovalCard
          key={request.id}
          request={request}
          submitting={submitting}
          onDecide={(decision) => decide(request, decision)}
        />
      ))}
    </div>
  );
}
