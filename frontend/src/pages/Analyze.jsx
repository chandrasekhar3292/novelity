import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../api';
import ResultsDisplay from '../components/ResultsDisplay';

const EXAMPLE_IDEAS = [
  'Using graph neural networks to predict protein-ligand binding affinity for drug discovery in rare diseases',
  'Applying transformer architectures to satellite imagery for real-time wildfire detection and spread prediction',
  'Combining federated learning with differential privacy for decentralized medical record analysis across hospitals',
];

function LoadingAnimation() {
  return (
    <div className="flex flex-col items-center justify-center py-16 space-y-6">
      {/* Scanning animation */}
      <div className="relative w-32 h-32">
        {/* Outer ring */}
        <motion.div
          className="absolute inset-0 rounded-full border-2 border-nova-500/20"
          animate={{ rotate: 360 }}
          transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
        />
        {/* Middle ring */}
        <motion.div
          className="absolute inset-3 rounded-full border border-nova-500/30"
          animate={{ rotate: -360 }}
          transition={{ duration: 6, repeat: Infinity, ease: 'linear' }}
        />
        {/* Inner ring */}
        <motion.div
          className="absolute inset-6 rounded-full border border-nova-400/40"
          animate={{ rotate: 360 }}
          transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
        />
        {/* Center dot */}
        <motion.div
          className="absolute inset-[38%] rounded-full bg-nova-500"
          animate={{ scale: [1, 1.3, 1], opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
        {/* Scanning line */}
        <motion.div
          className="absolute inset-x-0 top-1/2 h-px bg-gradient-to-r from-transparent via-nova-400 to-transparent"
          animate={{ top: ['20%', '80%', '20%'] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>

      <div className="text-center space-y-2">
        <motion.p
          className="text-sm font-medium text-nova-400"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          Analyzing novelty signals...
        </motion.p>
        <p className="text-xs text-gray-600">
          Searching corpus, computing embeddings, scoring signals
        </p>
      </div>

      {/* Progress steps */}
      <div className="flex items-center gap-6 text-xs text-gray-500">
        {['Embedding', 'Retrieval', 'Scoring', 'Classifying'].map((step, i) => (
          <motion.span
            key={step}
            initial={{ opacity: 0.3 }}
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 2, repeat: Infinity, delay: i * 0.5 }}
            className="flex items-center gap-1.5"
          >
            <span className="w-1 h-1 rounded-full bg-nova-500" />
            {step}
          </motion.span>
        ))}
      </div>
    </div>
  );
}

export default function Analyze() {
  const [idea, setIdea] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const textareaRef = useRef(null);

  const handleAnalyze = async () => {
    if (idea.trim().length < 10) {
      setError('Please enter at least 10 characters describing your research idea.');
      return;
    }
    setError(null);
    setResults(null);
    setLoading(true);
    try {
      const data = await api.analyzeFull(idea.trim());
      setResults(data);
    } catch (err) {
      setError(err.message || 'Analysis failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleExample = (text) => {
    setIdea(text);
    setResults(null);
    setError(null);
    textareaRef.current?.focus();
  };

  return (
    <div className="min-h-screen pt-24 pb-16 px-6">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="font-display text-4xl font-bold text-white">
            Analyze <span className="text-gradient">Novelty</span>
          </h1>
          <p className="mt-2 text-gray-500">
            Describe your research idea and we'll evaluate its novelty against the corpus.
          </p>
        </motion.div>

        {/* Input area */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass p-6"
        >
          <textarea
            ref={textareaRef}
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="Describe your research idea, hypothesis, or abstract..."
            rows={6}
            className="input-field resize-none text-base leading-relaxed"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleAnalyze();
            }}
          />

          {/* Submit row */}
          <div className="flex items-center justify-end mt-4">
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-600 hidden sm:inline">
                {idea.length} chars &middot; Ctrl+Enter
              </span>
              <button
                onClick={handleAnalyze}
                disabled={loading || idea.trim().length < 10}
                className="btn-primary disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
              >
                {loading ? 'Analyzing...' : 'Analyze'}
              </button>
            </div>
          </div>

          {/* Example ideas */}
          {!results && !loading && (
            <div className="mt-5 pt-4 border-t border-white/[0.04]">
              <span className="text-xs text-gray-600 uppercase tracking-wider">Try an example</span>
              <div className="mt-2 space-y-2">
                {EXAMPLE_IDEAS.map((ex, i) => (
                  <button
                    key={i}
                    onClick={() => handleExample(ex)}
                    className="block w-full text-left px-3 py-2 rounded-lg text-xs text-gray-500
                               hover:text-gray-300 hover:bg-void-700/50 transition-all duration-200 leading-relaxed"
                  >
                    "{ex}"
                  </button>
                ))}
              </div>
            </div>
          )}
        </motion.div>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mt-4 px-4 py-3 rounded-xl bg-signal-rose/10 border border-signal-rose/20 text-sm text-signal-rose"
            >
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Loading */}
        {loading && <LoadingAnimation />}

        {/* Results */}
        <AnimatePresence>
          {results && !loading && <ResultsDisplay data={results} />}
        </AnimatePresence>
      </div>
    </div>
  );
}
