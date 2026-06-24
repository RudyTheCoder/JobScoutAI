"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Archive, ExternalLink, Heart, Search, X } from "lucide-react";
import { archiveJob, getCompanies, getJobs, saveJob, unsaveJob } from "@/lib/api";
import type { Company, Job, JobListResponse } from "@/lib/types";
import { formatDate, formatMoney } from "@/lib/format";
import { sourceLabel } from "@/lib/source";
import { Button, EmptyState, ErrorPanel, LoadingPanel, Panel, PanelHeader, SecondaryButton, SelectInput, StatusBadge, TextInput } from "@/components/ui";

const initialFilters = { keyword: "", location: "", arrangement: "", employment_type: "", experience_level: "", minimum_salary: "", skills: "", sort: "match", company_id: "", source: "" };

export default function JobsPage() {
  const [draft, setDraft] = useState(initialFilters);
  const [applied, setApplied] = useState(initialFilters);
  const [jobs, setJobs] = useState<JobListResponse | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    const [jobData, companyData] = await Promise.all([getJobs(applied), getCompanies()]);
    setJobs(jobData);
    setCompanies(companyData);
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message)).finally(() => setLoading(false));
  }, [applied]);

  async function toggleSave(job: Job) {
    if (job.is_saved) await unsaveJob(job.id);
    else await saveJob(job.id);
    await load();
  }

  async function archive(id: number) {
    await archiveJob(id);
    await load();
  }

  function applySearch() {
    setApplied(draft);
  }

  if (loading) return <LoadingPanel label="Loading jobs" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-normal">Job Search</h1>
        <p className="mt-2 text-sm text-muted">Search normalized listings from configured company career pages.</p>
      </div>

      {error ? <ErrorPanel message={error} /> : null}

      <Panel>
        <PanelHeader title="Filters" subtitle="Configure filters, then press Search" />
        <div className="grid gap-3 p-5 md:grid-cols-3 xl:grid-cols-5">
          <label className="relative block xl:col-span-2">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden="true" />
            <TextInput className="pl-9" placeholder="Keyword or title" value={draft.keyword} onChange={(event) => setDraft({ ...draft, keyword: event.target.value })} />
          </label>
          <TextInput placeholder="Location" value={draft.location} onChange={(event) => setDraft({ ...draft, location: event.target.value })} />
          <SelectInput value={draft.arrangement} onChange={(event) => setDraft({ ...draft, arrangement: event.target.value })}>
            <option value="">Any arrangement</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
            <option value="on_site">On-site</option>
          </SelectInput>
          <SelectInput value={draft.company_id} onChange={(event) => setDraft({ ...draft, company_id: event.target.value })}>
            <option value="">All companies</option>
            {companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
          </SelectInput>
          <SelectInput value={draft.source} onChange={(event) => setDraft({ ...draft, source: event.target.value })}>
            <option value="">Any source</option>
            <option value="fixture">Fixture</option>
            <option value="generic/html">Generic HTML</option>
            <option value="greenhouse">Greenhouse</option>
            <option value="lever">Lever</option>
            <option value="ashby">Ashby</option>
          </SelectInput>
          <SelectInput value={draft.experience_level} onChange={(event) => setDraft({ ...draft, experience_level: event.target.value })}>
            <option value="">Any level</option>
            <option value="entry">Entry</option>
            <option value="mid">Mid</option>
            <option value="senior">Senior</option>
            <option value="lead">Lead</option>
          </SelectInput>
          <SelectInput value={draft.employment_type} onChange={(event) => setDraft({ ...draft, employment_type: event.target.value })}>
            <option value="">Any employment</option>
            <option value="full_time">Full-time</option>
            <option value="part_time">Part-time</option>
            <option value="contract">Contract</option>
            <option value="internship">Internship</option>
          </SelectInput>
          <TextInput placeholder="Minimum salary" type="number" value={draft.minimum_salary} onChange={(event) => setDraft({ ...draft, minimum_salary: event.target.value })} />
          <TextInput placeholder="Skills, comma-separated" value={draft.skills} onChange={(event) => setDraft({ ...draft, skills: event.target.value })} />
          <SelectInput value={draft.sort} onChange={(event) => setDraft({ ...draft, sort: event.target.value })}>
            <option value="match">Best match</option>
            <option value="newest">Newest</option>
            <option value="salary">Salary</option>
            <option value="company">Company</option>
          </SelectInput>
          <div className="flex gap-2">
            <Button type="button" onClick={applySearch}>Search</Button>
            <SecondaryButton type="button" onClick={() => { setDraft(initialFilters); setApplied(initialFilters); }}>
              <X className="h-4 w-4" /> Clear
            </SecondaryButton>
          </div>
        </div>
      </Panel>

      <Panel>
        <PanelHeader title="Listings" subtitle={`${jobs?.total ?? 0} matching jobs`} />
        {!jobs || jobs.items.length === 0 ? (
          <EmptyState title="No jobs found" detail="Adjust filters or run a demo scrape from Companies." />
        ) : (
          <div className="table-scroll overflow-x-auto">
            <table className="w-full min-w-[1120px] text-left text-sm">
              <thead className="bg-surface text-xs uppercase text-muted">
                <tr>
                  <th className="px-5 py-3 font-semibold">Job</th>
                  <th className="px-5 py-3 font-semibold">Company</th>
                  <th className="px-5 py-3 font-semibold">Source</th>
                  <th className="px-5 py-3 font-semibold">Location</th>
                  <th className="px-5 py-3 font-semibold">Salary</th>
                  <th className="px-5 py-3 font-semibold">Posted</th>
                  <th className="px-5 py-3 font-semibold">Match</th>
                  <th className="px-5 py-3 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {jobs.items.map((job) => (
                  <tr key={job.id} className="hover:bg-surface/70">
                    <td className="px-5 py-4">
                      <Link href={`/jobs/${job.id}`} className="font-medium text-accent hover:underline">{job.title}</Link>
                      <div className="mt-2 flex flex-wrap gap-1">{job.skills.slice(0, 3).map((skill) => <span key={skill} className="rounded-full bg-surface px-2 py-1 text-xs text-muted">{skill}</span>)}</div>
                    </td>
                    <td className="px-5 py-4">{job.company_name}</td>
                    <td className="px-5 py-4">
                      <StatusBadge status={sourceLabel(job.source_type)} />
                      {job.source_url ? <a className="mt-2 inline-flex items-center gap-1 text-xs text-accent hover:underline" href={job.source_url} target="_blank" rel="noreferrer"><ExternalLink className="h-3 w-3" />Source</a> : null}
                    </td>
                    <td className="px-5 py-4 text-muted">{job.location ?? "Unknown"}<div className="mt-1"><StatusBadge status={job.work_arrangement ?? "unknown"} /></div></td>
                    <td className="px-5 py-4">{job.salary_text ?? formatMoney(job.salary_max, job.currency ?? "USD")}</td>
                    <td className="px-5 py-4 text-muted">{formatDate(job.posted_at)}</td>
                    <td className="px-5 py-4 font-semibold text-brand">{job.match_score}%</td>
                    <td className="px-5 py-4">
                      <div className="flex flex-wrap gap-2">
                        <SecondaryButton type="button" className="min-h-9 px-3" onClick={() => toggleSave(job)}><Heart className="h-4 w-4" />{job.is_saved ? "Unsave" : "Save"}</SecondaryButton>
                        <a className="inline-flex min-h-9 items-center gap-2 rounded-md border border-border px-3 py-2 font-semibold hover:bg-surface" href={job.application_url} target="_blank" rel="noreferrer"><ExternalLink className="h-4 w-4" />Apply</a>
                        <SecondaryButton type="button" className="min-h-9 px-3" onClick={() => archive(job.id)}><Archive className="h-4 w-4" />Archive</SecondaryButton>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
