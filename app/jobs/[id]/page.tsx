"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, ExternalLink, Heart, Send } from "lucide-react";
import { getJob, markApplied, saveJob, unsaveJob } from "@/lib/api";
import type { Job } from "@/lib/types";
import { formatDate, formatMoney } from "@/lib/format";
import { Button, ErrorPanel, LoadingPanel, Panel, PanelHeader, SecondaryButton, StatusBadge } from "@/components/ui";

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const data = await getJob(params.id);
    setJob(data);
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message)).finally(() => setLoading(false));
  }, [params.id]);

  if (loading) return <LoadingPanel label="Loading job" />;
  if (error) return <ErrorPanel message={error} />;
  if (!job) return <ErrorPanel message="Job not found." />;

  const explanation = (job.raw_data.match_explanation ?? {}) as Record<string, unknown>;

  return (
    <div className="space-y-6">
      <Link href="/jobs" className="inline-flex items-center gap-2 text-sm font-medium text-muted hover:text-ink">
        <ArrowLeft className="h-4 w-4" /> Back to jobs
      </Link>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-normal">{job.title}</h1>
          <p className="mt-2 text-sm text-muted">{job.company_name} · {job.location ?? "Unknown location"} · Posted {formatDate(job.posted_at)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <SecondaryButton onClick={async () => { job.is_saved ? await unsaveJob(job.id) : await saveJob(job.id); await load(); }}><Heart className="h-4 w-4" />{job.is_saved ? "Unsave" : "Save"}</SecondaryButton>
          <Button onClick={async () => { await markApplied(job.id); await load(); }}><Send className="h-4 w-4" />Mark Applied</Button>
          <a className="inline-flex min-h-10 items-center gap-2 rounded-md border border-border bg-white px-4 py-2 text-sm font-semibold hover:bg-surface" href={job.application_url} target="_blank" rel="noreferrer"><ExternalLink className="h-4 w-4" />Open Posting</a>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Panel className="p-5"><p className="text-sm text-muted">Match</p><p className="mt-2 text-2xl font-semibold">{job.match_score}%</p></Panel>
        <Panel className="p-5"><p className="text-sm text-muted">Confidence</p><p className="mt-2 text-2xl font-semibold">{Math.round(job.extraction_confidence * 100)}%</p></Panel>
        <Panel className="p-5"><p className="text-sm text-muted">Salary</p><p className="mt-2 text-lg font-semibold">{job.salary_text ?? formatMoney(job.salary_max, job.currency ?? "USD")}</p></Panel>
        <Panel className="p-5"><p className="text-sm text-muted">Status</p><div className="mt-3"><StatusBadge status={job.status} /></div></Panel>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <Panel>
          <PanelHeader title="Job Details" subtitle="Cleaned text from the source posting" />
          <div className="space-y-4 p-5 text-sm leading-6 text-muted">
            <p>{job.description ?? "No description was extracted."}</p>
            {job.requirements ? <p>{job.requirements}</p> : null}
            <div className="flex flex-wrap gap-2">{job.skills.map((skill) => <span key={skill} className="rounded-full bg-surface px-2.5 py-1 text-xs">{skill}</span>)}</div>
          </div>
        </Panel>
        <Panel>
          <PanelHeader title="Match Analysis" subtitle="Deterministic preference formula" />
          <dl className="space-y-3 p-5 text-sm">
            <div><dt className="font-semibold">Matching skills</dt><dd className="mt-1 text-muted">{((explanation.matching_skills as string[]) ?? []).join(", ") || "None configured"}</dd></div>
            <div><dt className="font-semibold">Missing skills</dt><dd className="mt-1 text-muted">{((explanation.missing_skills as string[]) ?? []).join(", ") || "None"}</dd></div>
            <div><dt className="font-semibold">Location</dt><dd className="mt-1 text-muted">{String(explanation.location_match ?? false)}</dd></div>
            <div><dt className="font-semibold">Experience</dt><dd className="mt-1 text-muted">{String(explanation.experience_match ?? false)}</dd></div>
            <div><dt className="font-semibold">Salary</dt><dd className="mt-1 text-muted">{String(explanation.salary_match ?? false)}</dd></div>
          </dl>
        </Panel>
      </div>

      <Panel>
        <PanelHeader title="Raw Extracted Data" subtitle="Available for auditing without crowding the main table" />
        <pre className="overflow-x-auto p-5 text-xs text-muted">{JSON.stringify(job.raw_data, null, 2)}</pre>
      </Panel>
    </div>
  );
}
