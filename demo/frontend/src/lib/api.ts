import type { ChatResponse, LLMConfig, RagVersion, ScenarioMeta } from "../types";

export async function fetchLLMConfig(): Promise<LLMConfig> {
  const r = await fetch("/api/llm");
  if (!r.ok) throw new Error(`GET /api/llm ${r.status}`);
  return r.json();
}

export async function saveLLMConfig(cfg: LLMConfig): Promise<LLMConfig> {
  const r = await fetch("/api/llm", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(cfg),
  });
  if (!r.ok) throw new Error(`POST /api/llm ${r.status}`);
  return r.json();
}

export async function newSession(scenarioId?: string): Promise<string> {
  const qs = scenarioId ? `?scenario_id=${encodeURIComponent(scenarioId)}` : "";
  const r = await fetch(`/api/sessions/new${qs}`, { method: "POST" });
  if (!r.ok) throw new Error(`POST /api/sessions/new ${r.status}`);
  const data = (await r.json()) as { session_id: string };
  return data.session_id;
}

export async function deleteSession(sessionId: string): Promise<void> {
  await fetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
}

export async function listScenarios(): Promise<ScenarioMeta[]> {
  const r = await fetch("/api/scenarios");
  if (!r.ok) return [];
  return r.json();
}

export async function activateScenario(pitId: string): Promise<ScenarioMeta> {
  const r = await fetch(`/api/scenarios/${pitId}/activate`, { method: "POST" });
  if (!r.ok) throw new Error(`activate ${pitId} ${r.status}`);
  return r.json();
}

export async function applyFix(): Promise<{ ok: boolean; version_id?: number; error?: string }> {
  const r = await fetch("/api/rag/apply-fix", { method: "POST" });
  return r.json();
}

export async function getCurrentRag(): Promise<{ source: string; version_id: number | null }> {
  const r = await fetch("/api/rag/current");
  return r.json();
}

export async function listVersions(scenarioId?: string): Promise<RagVersion[]> {
  const qs = scenarioId ? `?scenario_id=${encodeURIComponent(scenarioId)}` : "";
  const r = await fetch(`/api/rag/versions${qs}`);
  if (!r.ok) return [];
  return r.json();
}

export async function saveRagCode(
  source: string,
  label = "manual edit",
): Promise<{ ok: boolean; version_id?: number; error?: string }> {
  const r = await fetch("/api/rag/save", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ source, label }),
  });
  return r.json();
}

export async function revertToVersion(
  versionId: number,
): Promise<{ ok: boolean; error?: string }> {
  const r = await fetch(`/api/rag/revert/${versionId}`, { method: "POST" });
  return r.json();
}
