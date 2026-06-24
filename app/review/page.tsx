"use client";

import { useEffect, useState } from "react";
import { Check, CopyX, X } from "lucide-react";
import { approveReview, duplicateReview, getReviews, rejectReview } from "@/lib/api";
import type { ReviewRecord } from "@/lib/types";
import { formatDateTime } from "@/lib/format";
import { Button, EmptyState, ErrorPanel, LoadingPanel, Panel, PanelHeader, SecondaryButton, StatusBadge, TextArea } from "@/components/ui";

export default function ReviewPage() {
  const [reviews, setReviews] = useState<ReviewRecord[]>([]);
  const [selected, setSelected] = useState<ReviewRecord | null>(null);
  const [edited, setEdited] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    const data = await getReviews();
    setReviews(data);
    if (!selected && data[0]) {
      setSelected(data[0]);
      setEdited(JSON.stringify(data[0].extracted_data, null, 2));
    }
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message)).finally(() => setLoading(false));
  }, []);

  async function approve() {
    if (!selected) return;
    await approveReview(selected.id, JSON.parse(edited));
    setSelected(null);
    await load();
  }

  async function reject(status: "rejected" | "duplicate") {
    if (!selected) return;
    if (status === "duplicate") await duplicateReview(selected.id, "Marked as duplicate during review.");
    else await rejectReview(selected.id, "Rejected during review.");
    setSelected(null);
    await load();
  }

  if (loading) return <LoadingPanel label="Loading review queue" />;

  return (
    <div className="space-y-6">
      <div><h1 className="text-3xl font-semibold tracking-normal">Review Queue</h1><p className="mt-2 text-sm text-muted">Approve, edit, reject, or mark uncertain extracted records as duplicates.</p></div>
      {error ? <ErrorPanel message={error} /> : null}
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel>
          <PanelHeader title="Pending Records" subtitle={`${reviews.length} need review`} />
          {reviews.length === 0 ? <EmptyState title="Queue clear" detail="New uncertain records will appear after scraping." /> : (
            <div className="divide-y divide-border">
              {reviews.map((review) => (
                <button key={review.id} className="block w-full px-5 py-4 text-left hover:bg-surface/70" onClick={() => { setSelected(review); setEdited(JSON.stringify(review.extracted_data, null, 2)); }}>
                  <div className="flex items-start justify-between gap-4">
                    <div><p className="font-medium">{String(review.extracted_data.title ?? "Untitled record")}</p><p className="mt-1 text-sm text-muted">{review.issue_type} · {formatDateTime(review.created_at)}</p></div>
                    <StatusBadge status={review.status} />
                  </div>
                </button>
              ))}
            </div>
          )}
        </Panel>
        <Panel>
          <PanelHeader title="Record Detail" subtitle={selected ? `Confidence ${Math.round(selected.confidence * 100)}%` : "Select a record"} />
          {selected ? (
            <div className="space-y-4 p-5">
              <TextArea value={edited} onChange={(event) => setEdited(event.target.value)} className="min-h-72 font-mono text-xs" />
              <p className="text-sm text-muted">Evidence: {selected.source_evidence ?? "None"}</p>
              <div className="flex flex-wrap gap-2">
                <Button onClick={approve}><Check className="h-4 w-4" />Approve</Button>
                <SecondaryButton onClick={() => reject("duplicate")}><CopyX className="h-4 w-4" />Duplicate</SecondaryButton>
                <SecondaryButton onClick={() => reject("rejected")}><X className="h-4 w-4" />Reject</SecondaryButton>
              </div>
            </div>
          ) : <EmptyState title="No record selected" detail="Choose a pending record to inspect extracted fields." />}
        </Panel>
      </div>
    </div>
  );
}
