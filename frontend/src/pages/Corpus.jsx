import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../api';

function StatusCard({ status }) {
  if (!status) return null;
  const items = [
    { label: 'Index Ready', value: status.index_ready ? 'Yes' : 'No', color: status.index_ready ? 'text-signal-emerald' : 'text-signal-rose' },
    { label: 'Embedding Model', value: status.embedding_model?.split('/').pop() || '—', color: 'text-gray-300' },
  ];

  return (
    <div className="grid grid-cols-2 gap-3">
      {items.map(({ label, value, color }) => (
        <div key={label} className="glass p-4 text-center">
          <div className={`text-2xl font-bold font-mono ${color}`}>{value}</div>
          <div className="text-xs text-gray-500 mt-1 uppercase tracking-wider">{label}</div>
        </div>
      ))}
    </div>
  );
}

function AddPaperModal({ onClose, onAdded }) {
  const [form, setForm] = useState({ id: '', title: '', abstract: '', year: '', concepts: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.id || !form.abstract || form.abstract.length < 10) {
      setError('ID and abstract (min 10 chars) are required.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const paper = {
        id: form.id,
        title: form.title || undefined,
        abstract: form.abstract,
        year: form.year ? parseInt(form.year) : undefined,
        concepts: form.concepts ? form.concepts.split(',').map((c) => c.trim()).filter(Boolean) : undefined,
      };
      await api.addPapers([paper]);
      onAdded();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-void-950/80 backdrop-blur-sm px-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="glass p-6 w-full max-w-lg"
      >
        <h3 className="font-display text-xl font-bold text-white mb-4">Add Paper</h3>
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            placeholder="Paper ID"
            value={form.id}
            onChange={(e) => setForm({ ...form, id: e.target.value })}
            className="input-field text-sm"
          />
          <input
            placeholder="Title (optional)"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="input-field text-sm"
          />
          <textarea
            placeholder="Abstract (required, min 10 chars)"
            value={form.abstract}
            onChange={(e) => setForm({ ...form, abstract: e.target.value })}
            rows={4}
            className="input-field text-sm resize-none"
          />
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="Year (e.g. 2024)"
              type="number"
              value={form.year}
              onChange={(e) => setForm({ ...form, year: e.target.value })}
              className="input-field text-sm"
            />
            <input
              placeholder="Concepts (comma-sep)"
              value={form.concepts}
              onChange={(e) => setForm({ ...form, concepts: e.target.value })}
              className="input-field text-sm"
            />
          </div>
          {error && <p className="text-xs text-signal-rose">{error}</p>}
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-ghost text-sm">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn-primary text-sm">
              {loading ? 'Adding...' : 'Add Paper'}
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
}

function FetchModal({ onClose, onFetched }) {
  const [query, setQuery] = useState('');
  const [maxResults, setMaxResults] = useState(100);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFetch = async (e) => {
    e.preventDefault();
    if (query.trim().length < 2) {
      setError('Enter a search query (min 2 characters).');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.fetchArxiv(query.trim(), maxResults);
      setResult(res);
      if (res.added > 0) onFetched();
    } catch (err) {
      setError(err.message || 'Failed to fetch papers.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-void-950/80 backdrop-blur-sm px-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="glass p-6 w-full max-w-lg"
      >
        <h3 className="font-display text-xl font-bold text-white mb-1">Fetch Papers</h3>
        <p className="text-xs text-gray-500 mb-5">
          Search for papers by topic and add them to your corpus automatically.
        </p>
        <form onSubmit={handleFetch} className="space-y-3">
          <input
            placeholder="Search query (e.g. 'transformer attention', 'graph neural networks')"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="input-field text-sm"
            autoFocus
          />
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <label className="text-xs text-gray-500 mb-1 block">Max papers</label>
              <input
                type="number"
                min={1}
                max={500}
                value={maxResults}
                onChange={(e) => setMaxResults(Math.min(500, Math.max(1, parseInt(e.target.value) || 100)))}
                className="input-field text-sm"
              />
            </div>
            <div className="flex-1 pt-5">
              <button
                type="submit"
                disabled={loading || query.trim().length < 2}
                className="btn-primary text-sm w-full disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <motion.span
                      className="inline-block w-3 h-3 border-2 border-void-950/30 border-t-void-950 rounded-full"
                      animate={{ rotate: 360 }}
                      transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
                    />
                    Fetching...
                  </span>
                ) : 'Fetch Papers'}
              </button>
            </div>
          </div>

          {error && (
            <p className="text-xs text-signal-rose px-1">{error}</p>
          )}

          {result && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`rounded-xl p-4 text-sm ${
                result.added > 0
                  ? 'bg-signal-emerald/10 border border-signal-emerald/20'
                  : 'bg-signal-amber/10 border border-signal-amber/20'
              }`}
            >
              <div className="grid grid-cols-2 gap-y-2 gap-x-4 text-xs">
                <span className="text-gray-400">Papers found</span>
                <span className="font-mono text-gray-200">{result.fetched}</span>
                <span className="text-gray-400">Added to corpus</span>
                <span className="font-mono text-signal-emerald">{result.added}</span>
                <span className="text-gray-400">Skipped (duplicates)</span>
                <span className="font-mono text-gray-500">{result.skipped}</span>
              </div>
            </motion.div>
          )}

          <div className="flex justify-end pt-1">
            <button type="button" onClick={onClose} className="btn-ghost text-sm">
              {result ? 'Done' : 'Cancel'}
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
}

function DeleteConfirm({ paperId, onClose, onDeleted }) {
  const [loading, setLoading] = useState(false);

  const handleDelete = async () => {
    setLoading(true);
    try {
      await api.deletePaper(paperId);
      onDeleted();
      onClose();
    } catch {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-void-950/80 backdrop-blur-sm px-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95 }}
        animate={{ scale: 1 }}
        exit={{ scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="glass p-6 max-w-sm w-full text-center"
      >
        <div className="text-3xl mb-3">&#9888;</div>
        <h3 className="font-display text-lg font-bold text-white mb-2">Delete Paper?</h3>
        <p className="text-sm text-gray-400 mb-1">
          This will remove <span className="font-mono text-xs text-signal-rose">{paperId}</span> and rebuild the index.
        </p>
        <div className="flex justify-center gap-3 mt-5">
          <button onClick={onClose} className="btn-ghost text-sm">Cancel</button>
          <button
            onClick={handleDelete}
            disabled={loading}
            className="px-6 py-2.5 rounded-xl font-medium text-white bg-signal-rose/80 hover:bg-signal-rose transition-colors text-sm"
          >
            {loading ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

export default function Corpus() {
  const [status, setStatus] = useState(null);
  const [papers, setPapers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [deleteId, setDeleteId] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [showFetch, setShowFetch] = useState(false);
  const limit = 20;

  const fetchData = useCallback(async () => {
    try {
      const [st, papersRes] = await Promise.all([
        api.corpusStatus(),
        api.listPapers(limit, page * limit),
      ]);
      setStatus(st);
      setPapers(papersRes.papers || []);
      setTotal(papersRes.total || 0);
    } catch {
      // backend may be offline
    }
  }, [page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await api.uploadCorpus(file);
      fetchData();
    } catch {
      // handle error silently
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const filtered = search
    ? papers.filter(
        (p) =>
          p.title?.toLowerCase().includes(search.toLowerCase()) ||
          p.id?.toLowerCase().includes(search.toLowerCase())
      )
    : papers;

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="min-h-screen pt-24 pb-16 px-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="font-display text-4xl font-bold text-white">
            Corpus <span className="text-gradient">Manager</span>
          </h1>
          <p className="mt-2 text-gray-500">
            Manage the research paper corpus that powers novelty analysis.
          </p>
        </motion.div>

        {/* Status */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <StatusCard status={status} />
        </motion.div>

        {/* Toolbar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mt-8"
        >
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search papers by title or ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-field text-sm"
            />
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setShowFetch(true)} className="btn-primary text-sm whitespace-nowrap">
              Fetch Papers
            </button>
            <button onClick={() => setShowAdd(true)} className="btn-ghost text-sm whitespace-nowrap">
              + Add Paper
            </button>
            <label className="btn-ghost text-sm cursor-pointer whitespace-nowrap">
              {uploading ? 'Uploading...' : 'Upload JSON'}
              <input type="file" accept=".json" onChange={handleUpload} className="hidden" />
            </label>
          </div>
        </motion.div>

        {/* Paper table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-6 glass overflow-hidden"
        >
          {/* Table header */}
          <div className="grid grid-cols-[1fr_auto_auto_auto] gap-4 px-5 py-3 border-b border-white/[0.04] text-xs text-gray-500 uppercase tracking-wider">
            <span>Title / ID</span>
            <span className="w-16 text-center">Year</span>
            <span className="w-20 text-center">Concepts</span>
            <span className="w-16" />
          </div>

          {/* Rows */}
          {filtered.length === 0 ? (
            <div className="px-5 py-12 text-center text-sm text-gray-600">
              {search ? 'No papers match your search.' : 'No papers in corpus.'}
            </div>
          ) : (
            filtered.map((paper, i) => (
              <motion.div
                key={paper.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.03 }}
                className="grid grid-cols-[1fr_auto_auto_auto] gap-4 items-center px-5 py-3
                           border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors group"
              >
                <div className="min-w-0">
                  <div className="text-sm text-gray-300 truncate">
                    {paper.title || paper.id}
                  </div>
                  {paper.title && (
                    <div className="text-[10px] font-mono text-gray-600 truncate">{paper.id}</div>
                  )}
                </div>
                <div className="w-16 text-center font-mono text-xs text-gray-500">
                  {paper.year || '—'}
                </div>
                <div className="w-20 text-center font-mono text-xs text-gray-500">
                  {paper.concepts?.length || 0}
                </div>
                <div className="w-16 text-right">
                  <button
                    onClick={() => setDeleteId(paper.id)}
                    className="opacity-0 group-hover:opacity-100 text-xs text-signal-rose/60
                               hover:text-signal-rose transition-all duration-200"
                  >
                    Delete
                  </button>
                </div>
              </motion.div>
            ))
          )}
        </motion.div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-6">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="btn-ghost text-xs disabled:opacity-30"
            >
              &larr; Prev
            </button>
            <span className="text-xs text-gray-500 font-mono px-3">
              {page + 1} / {totalPages}
            </span>
            <button
              onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
              disabled={page >= totalPages - 1}
              className="btn-ghost text-xs disabled:opacity-30"
            >
              Next &rarr;
            </button>
          </div>
        )}
      </div>

      {/* Modals */}
      <AnimatePresence>
        {showFetch && <FetchModal onClose={() => setShowFetch(false)} onFetched={fetchData} />}
        {showAdd && <AddPaperModal onClose={() => setShowAdd(false)} onAdded={fetchData} />}
        {deleteId && (
          <DeleteConfirm
            paperId={deleteId}
            onClose={() => setDeleteId(null)}
            onDeleted={fetchData}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
