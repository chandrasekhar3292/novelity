import { motion } from 'motion/react';

const SIGNAL_META = {
  max_similarity: {
    label: 'Max Similarity',
    desc: 'Closest paper in corpus',
    color: 'from-signal-cyan to-signal-sky',
    max: 1,
  },
  mean_similarity: {
    label: 'Mean Similarity',
    desc: 'Avg of top-20 papers',
    color: 'from-signal-cyan/80 to-signal-sky/80',
    max: 1,
  },
  similarity_spread: {
    label: 'Sim. Spread',
    desc: 'Consistency of matches',
    color: 'from-signal-violet to-nebula-400',
    max: 0.5,
  },
  density_score: {
    label: 'Density',
    desc: 'Publication volume in area',
    color: 'from-signal-amber to-yellow-400',
    max: 10,
  },
  recency_score: {
    label: 'Recency',
    desc: 'Growth trend (>1 = growing)',
    color: 'from-signal-emerald to-green-400',
    max: 5,
  },
  crosslink_score: {
    label: 'Cross-Link',
    desc: 'Concept rarity score',
    color: 'from-signal-rose to-pink-400',
    max: 1,
  },
};

export default function SignalGauge({ name, value, degraded = false }) {
  const meta = SIGNAL_META[name] || { label: name, desc: '', color: 'from-gray-400 to-gray-500', max: 1 };
  const pct = degraded ? 0 : Math.min((value / meta.max) * 100, 100);
  const fillColor = degraded ? 'from-gray-700 to-gray-600' : meta.color;
  const valueColor = degraded ? 'text-gray-600' : 'text-gray-400';
  const labelColor = degraded ? 'text-gray-600' : 'text-gray-300 group-hover:text-white';

  return (
    <div className="group">
      <div className="flex items-baseline justify-between mb-2">
        <div>
          <span className={`text-sm font-medium transition-colors ${labelColor}`}>
            {meta.label}
          </span>
          <span className="ml-2 text-xs text-gray-600 hidden group-hover:inline transition-all">
            {degraded ? 'not informative for this corpus' : meta.desc}
          </span>
        </div>
        {degraded && (
          <span className={`font-mono text-xs tabular-nums ${valueColor}`}>
            n/a
          </span>
        )}
      </div>
      <div className="signal-bar">
        <motion.div
          className={`signal-bar-fill bg-gradient-to-r ${fillColor}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 1, ease: 'easeOut', delay: 0.2 }}
        />
      </div>
    </div>
  );
}
