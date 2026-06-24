"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { HeartOff } from "lucide-react";
import { getSavedJobs, unsaveJob } from "@/lib/api";
import type { SavedJob } from "@/lib/types";
import { formatDateTime } from "@/lib/format";
import { EmptyState, ErrorPanel, LoadingPanel, Panel, PanelHeader, SecondaryButton } from "@/components/ui";

export default function SavedPage() {
  const [saved, setSaved] = useState<SavedJob[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setSaved(await getSavedJobs());
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message)).finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingPanel label="Loading saved jobs" />;

  return (
    <div className="space-y-6">
      <div><h1 className="text-3xl font-semibold tracking-normal">Saved Jobs</h1><p className="mt-2 text-sm text-muted">Persistent shortlist from the job search workflow.</p></div>
      {error ? <ErrorPanel message={error} /> : null}
      <Panel>
        <PanelHeader title="Shortlist" subtitle={`${saved.length} saved jobs`} />
        {saved.length === 0 ? <EmptyState title="No saved jobs" detail="Save jobs from search to build a shortlist." /> : (
          <div className="divide-y divide-border">
            {saved.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-4 px-5 py-4">
                <div><Link href={`/jobs/${item.job.id}`} className="font-medium text-accent hover:underline">{item.job.title}</Link><p className="mt-1 text-sm text-muted">{item.job.company_name} · saved {formatDateTime(item.saved_at)}</p></div>
                <SecondaryButton onClick={async () => { await unsaveJob(item.job.id); await load(); }}><HeartOff className="h-4 w-4" />Unsave</SecondaryButton>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
