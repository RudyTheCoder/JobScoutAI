"use client";

import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { getIntegrations, getSettings, updateSettings } from "@/lib/api";
import type { IntegrationStatus, UserSettings } from "@/lib/types";
import { Button, ErrorPanel, LoadingPanel, Panel, PanelHeader, SelectInput, StatusBadge, TextArea, TextInput } from "@/components/ui";

function join(values: string[] | undefined) {
  return (values ?? []).join(", ");
}

function split(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [integrations, setIntegrations] = useState<IntegrationStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    const [settingsData, integrationData] = await Promise.all([getSettings(), getIntegrations()]);
    setSettings(settingsData);
    setIntegrations(integrationData);
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message)).finally(() => setLoading(false));
  }, []);

  async function save() {
    if (settings) setSettings(await updateSettings(settings));
  }

  if (loading || !settings) return <LoadingPanel label="Loading settings" />;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div><h1 className="text-3xl font-semibold tracking-normal">Settings</h1><p className="mt-2 text-sm text-muted">Persist profile preferences, scraping defaults, resume text, and integration visibility.</p></div>
        <Button onClick={save}><Save className="h-4 w-4" />Save</Button>
      </div>
      {error ? <ErrorPanel message={error} /> : null}
      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <Panel>
          <PanelHeader title="Job Preferences" subtitle="Used by deterministic match scoring" />
          <div className="grid gap-3 p-5">
            <TextInput value={join(settings.target_titles)} onChange={(event) => setSettings({ ...settings, target_titles: split(event.target.value) })} placeholder="Target titles" />
            <TextInput value={join(settings.preferred_locations)} onChange={(event) => setSettings({ ...settings, preferred_locations: split(event.target.value) })} placeholder="Preferred locations" />
            <TextInput value={join(settings.required_skills)} onChange={(event) => setSettings({ ...settings, required_skills: split(event.target.value) })} placeholder="Required skills" />
            <TextInput type="number" value={settings.minimum_salary ?? ""} onChange={(event) => setSettings({ ...settings, minimum_salary: Number(event.target.value) || null })} placeholder="Minimum salary" />
            <SelectInput value={settings.work_arrangement} onChange={(event) => setSettings({ ...settings, work_arrangement: event.target.value })}>
              <option value="any">Any arrangement</option>
              <option value="remote">Remote</option>
              <option value="hybrid">Hybrid</option>
              <option value="on_site">On-site</option>
            </SelectInput>
            <SelectInput value={settings.experience_level} onChange={(event) => setSettings({ ...settings, experience_level: event.target.value })}>
              <option value="entry">Entry</option>
              <option value="mid">Mid</option>
              <option value="senior">Senior</option>
              <option value="lead">Lead</option>
            </SelectInput>
          </div>
        </Panel>
        <Panel>
          <PanelHeader title="Scraping Defaults" subtitle="Backend-only operational settings" />
          <div className="grid gap-3 p-5">
            <SelectInput value={settings.default_scrape_frequency} onChange={(event) => setSettings({ ...settings, default_scrape_frequency: event.target.value })}>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
            </SelectInput>
            <TextInput type="number" value={settings.concurrency} onChange={(event) => setSettings({ ...settings, concurrency: Number(event.target.value) })} />
            <TextInput type="number" value={settings.retry_limit} onChange={(event) => setSettings({ ...settings, retry_limit: Number(event.target.value) })} />
            <TextInput type="number" value={settings.request_timeout} onChange={(event) => setSettings({ ...settings, request_timeout: Number(event.target.value) })} />
            <SelectInput value={settings.browser_automation} onChange={(event) => setSettings({ ...settings, browser_automation: event.target.value })}>
              <option value="auto">Auto</option>
              <option value="always">Always</option>
              <option value="never">Never</option>
            </SelectInput>
          </div>
        </Panel>
      </div>
      <Panel>
        <PanelHeader title="Resume Text" subtitle="Stored locally for deterministic matching in this MVP" />
        <div className="p-5"><TextArea value={settings.resume_text ?? ""} onChange={(event) => setSettings({ ...settings, resume_text: event.target.value })} /></div>
      </Panel>
      <Panel>
        <PanelHeader title="Integrations" subtitle="Status is based on backend environment variables" />
        <div className="grid gap-4 p-5 md:grid-cols-3">
          <div className="rounded-md border border-border p-4"><p className="font-semibold">OpenRouter</p><div className="mt-3"><StatusBadge status={integrations?.openrouter ?? "not_configured"} /></div></div>
          <div className="rounded-md border border-border p-4"><p className="font-semibold">Apify</p><div className="mt-3"><StatusBadge status={integrations?.apify ?? "not_configured"} /></div></div>
          <div className="rounded-md border border-border p-4"><p className="font-semibold">Google Sheets</p><div className="mt-3"><StatusBadge status={integrations?.google_sheets ?? "not_configured"} /></div></div>
        </div>
      </Panel>
    </div>
  );
}
