"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getApplications, updateApplication } from "@/lib/api";
import type { Application, ApplicationStage } from "@/lib/types";
import { ErrorPanel, LoadingPanel, Panel, PanelHeader, SelectInput, TextArea, TextInput } from "@/components/ui";

const stages: ApplicationStage[] = ["wishlist", "applied", "interview", "offer", "rejected"];

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setApplications(await getApplications());
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message)).finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingPanel label="Loading applications" />;

  return (
    <div className="space-y-6">
      <div><h1 className="text-3xl font-semibold tracking-normal">Applications</h1><p className="mt-2 text-sm text-muted">Kanban-style tracking with persisted stages, notes, and next actions.</p></div>
      {error ? <ErrorPanel message={error} /> : null}
      <div className="grid gap-4 xl:grid-cols-5">
        {stages.map((stage) => (
          <Panel key={stage}>
            <PanelHeader title={stage.replace("_", " ")} subtitle={`${applications.filter((item) => item.stage === stage).length} jobs`} />
            <div className="space-y-3 p-3">
              {applications.filter((item) => item.stage === stage).map((application) => (
                <div key={application.id} className="rounded-md border border-border bg-white p-3">
                  <Link href={`/jobs/${application.job.id}`} className="text-sm font-semibold text-accent hover:underline">{application.job.title}</Link>
                  <p className="mt-1 text-xs text-muted">{application.job.company_name}</p>
                  <SelectInput className="mt-3" value={application.stage} onChange={async (event) => { await updateApplication(application.id, { stage: event.target.value as ApplicationStage }); await load(); }}>
                    {stages.map((option) => <option key={option} value={option}>{option}</option>)}
                  </SelectInput>
                  <TextInput className="mt-2" placeholder="Next action" defaultValue={application.next_action ?? ""} onBlur={async (event) => { await updateApplication(application.id, { next_action: event.target.value }); await load(); }} />
                  <TextArea className="mt-2 min-h-20" placeholder="Notes" defaultValue={application.notes ?? ""} onBlur={async (event) => { await updateApplication(application.id, { notes: event.target.value }); await load(); }} />
                </div>
              ))}
            </div>
          </Panel>
        ))}
      </div>
    </div>
  );
}
