const BASE = '';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => request('/health'),

  analyzeLite: (idea) =>
    request('/api/analyze/lite', {
      method: 'POST',
      body: JSON.stringify({ idea }),
    }),

  analyzeFull: (idea) =>
    request('/api/analyze', {
      method: 'POST',
      body: JSON.stringify({ idea }),
    }),

  corpusStatus: () => request('/api/corpus/status'),

  listPapers: (limit = 50, offset = 0) =>
    request(`/api/corpus/papers?limit=${limit}&offset=${offset}`),

  addPapers: (papers) =>
    request('/api/corpus/papers', {
      method: 'POST',
      body: JSON.stringify({ papers }),
    }),

  uploadCorpus: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${BASE}/api/corpus/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Upload failed: ${res.status}`);
    }
    return res.json();
  },

  fetchArxiv: (query, maxResults = 100) =>
    request('/api/corpus/fetch-arxiv', {
      method: 'POST',
      body: JSON.stringify({ query, max_results: maxResults }),
    }),

  deletePaper: (paperId) =>
    request(`/api/corpus/papers/${encodeURIComponent(paperId)}`, {
      method: 'DELETE',
    }),
};
