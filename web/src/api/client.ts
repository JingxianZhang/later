const BASE = (localStorage.getItem('API_URL') || 'http://127.0.0.1:8000') + '/v1';

export type IngestResponse = { tool_id: string; status: string };
export type ToolInfo = {
  id: string;
  name: string;
  canonical_url?: string;
  status: string;
  one_pager: Record<string, any>;
  documents: number;
  updates: number;
  sources?: string[];
  media_items?: any[];
};

export type ToolListItem = {
  id: string;
  name: string;
  status: string;
  watchlist: boolean;
  last_updated: string;
  updates: number;
  canonical_url: string;
  overview?: string;
};

export async function ingest(input: { url?: string; name?: string; force?: boolean }): Promise<IngestResponse> {
  const userId = localStorage.getItem('USER_ID') || undefined;
  const res = await fetch(`${BASE}/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(userId ? { 'X-User-Id': userId } : {}) },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getTool(toolId: string): Promise<ToolInfo> {
  const userId = localStorage.getItem('USER_ID') || undefined;
  const res = await fetch(`${BASE}/tools/${toolId}`, {
    headers: { ...(userId ? { 'X-User-Id': userId } : {}) },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function chat(
  toolId: string | null | undefined,
  question: string,
  opts?: { scope?: 'tool' | 'global'; preferOnePager?: boolean; ragLimit?: number }
): Promise<{ answer: string; citations: { source_url: string; snippet: string }[] }>{
  const userId = localStorage.getItem('USER_ID') || undefined;
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(userId ? { 'X-User-Id': userId } : {}) },
    body: JSON.stringify({
      tool_id: toolId || undefined,
      question,
      scope: opts?.scope ?? (toolId ? 'tool' : 'global'),
      prefer_one_pager: !!opts?.preferOnePager,
      rag_limit: opts?.ragLimit,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listTools(): Promise<ToolListItem[]> {
  const userId = localStorage.getItem('USER_ID') || undefined;
  const res = await fetch(`${BASE}/tools`, { headers: { ...(userId ? { 'X-User-Id': userId } : {}) } });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function ingestImage(file: File): Promise<IngestResponse> {
  const userId = localStorage.getItem('USER_ID') || undefined;
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/ingest/image`, {
    method: 'POST',
    body: form,
    headers: { ...(userId ? { 'X-User-Id': userId } : {}) },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function startTelegramLink(): Promise<{ token: string; expires_at: string }> {
  const userId = localStorage.getItem('USER_ID');
  if (!userId) throw new Error('Not signed in');
  const res = await fetch(`${BASE}/auth/link/telegram/start`, {
    method: 'POST',
    headers: { 'X-User-Id': userId },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getTelegramLinkStatus(): Promise<{ linked: boolean }> {
  const userId = localStorage.getItem('USER_ID');
  if (!userId) throw new Error('Not signed in');
  const res = await fetch(`${BASE}/auth/link/telegram/status`, {
    headers: { 'X-User-Id': userId },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function setWatchlist(toolId: string, watch: boolean): Promise<void> {
  const userId = localStorage.getItem('USER_ID') || undefined;
  const res = await fetch(`${BASE}/tools/${toolId}/watchlist`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(userId ? { 'X-User-Id': userId } : {}) },
    body: JSON.stringify({ watch }),
  });
  if (!res.ok) throw new Error(await res.text());
}

export async function deleteLatestVersion(
  toolId: string,
  opts?: { userId?: string }
): Promise<
  | { ok: true; deleted_version_id: string; new_latest_version_id?: string | null }
  | { ok: true; unlinked_only: true; tool_id: string }
  | { ok: true; tool_deleted: true; tool_id: string }
>{
  const url = new URL(`${BASE}/tools/${toolId}/versions/latest`);
  if (opts?.userId) url.searchParams.set('user_id', opts.userId);
  const res = await fetch(url.toString(), {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Mapper: backend ToolInfo -> UI Tool shape (minimal)
export function mapTool(info: ToolInfo) {
  const op = info.one_pager || {};
  const host = (() => {
    try {
      if (!info.canonical_url) return '';
      const u = new URL(info.canonical_url);
      return u.hostname.split('.').slice(-2, undefined).join('.');
    } catch {
      return '';
    }
  })();
  const friendly = info.name && !info.name.startsWith('http')
    ? info.name
    : (host ? host.charAt(0).toUpperCase() + host.slice(1) : (info.name || 'Unknown'));
  const favicon = host ? `https://www.google.com/s2/favicons?domain=${host}&sz=64` : '';
  const features: string[] = Array.isArray(op.features) ? op.features : [];
  const tech: string[] = Array.isArray(op.tech_stack) ? op.tech_stack : [];
  const sources: string[] = Array.isArray(op.sources) ? op.sources : (info.sources ?? []);
  const howToUse: string[] = Array.isArray(op.how_to_use) ? op.how_to_use : [];
  const useCases: string[] = Array.isArray(op.use_cases) ? op.use_cases : [];
  const userFeedback: string[] = Array.isArray(op.user_feedback) ? op.user_feedback : [];
  const integrations: string[] = Array.isArray(op.integrations) ? op.integrations : [];
  const recentUpdates: string[] = Array.isArray(op.recent_updates) ? op.recent_updates : [];
  const competitors: string[] = Array.isArray(op.competitors) ? op.competitors : [];
  const pricingObj: Record<string, string> = typeof op.pricing === 'object' && op.pricing ? op.pricing : {};
  const pricing = Object.keys(pricingObj).map(k => ({
    tier: k,
    price: String(pricingObj[k] ?? ''),
    verified: true,
  }));
  return {
    id: info.id,
    name: friendly,
    icon: favicon || 'ri-robot-2-line',
    description: op.overview || '',
    canonicalUrl: info.canonical_url || '',
    categories: [],
    status: info.status === 'partially_verified' ? 'verified' : 'default',
    isWatchlisted: false,
    onePager: {
      overview: op.overview || '',
      pricing,
      techStack: tech.map(t => ({ name: t, verified: true })),
      keyFeatures: features,
      howToUse,
      useCases,
      userFeedback,
      integrations,
      recentUpdates,
      competitors,
      lastUpdated: op.last_updated || new Date().toISOString(),
      sources,
    },
    chatHistory: [],
    highlights: (info.media_items || []).map((m: any) => ({
      platform: m.platform,
      url: m.url,
      title: m.title,
      author: m.author || m.author_handle,
      thumbnailUrl: m.thumbnail_url,
      metrics: m.metrics || {},
    })),
  };
}

// Mapper: backend ToolListItem -> UI Tool (for gallery)
export function mapListItem(item: ToolListItem) {
  const status: 'new' | 'updated' | 'verified' | 'default' =
    item.status === 'partially_verified' ? 'new' : 'default';
  const host = (() => {
    try {
      const u = new URL(item.canonical_url);
      return u.hostname.split('.').slice(-2, undefined).join('.'); // domain.tld
    } catch {
      return '';
    }
  })();
  const friendly = item.name && !item.name.startsWith('http') ? item.name : (host ? host.charAt(0).toUpperCase() + host.slice(1) : 'Unknown');
  const favicon = host ? `https://www.google.com/s2/favicons?domain=${host}&sz=64` : '';
  return {
    id: item.id,
    name: friendly,
    icon: favicon || 'ri-robot-2-line',
    description: (item.overview || '').slice(0, 180),
    categories: [],
    status: item.watchlist && item.updates > 0 ? 'updated' : status,
    isWatchlisted: item.watchlist,
    onePager: {
      overview: item.overview || '',
      pricing: [],
      techStack: [],
      keyFeatures: [],
      lastUpdated: item.last_updated || new Date().toISOString(),
      sources: [],
    },
    chatHistory: [],
  };
}

