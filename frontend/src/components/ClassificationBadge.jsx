import { motion } from 'motion/react';

const CLASSIFICATION_STYLES = {
  'Out-of-Domain': {
    color: 'text-signal-amber',
    bg: 'bg-signal-amber/10',
    border: 'border-signal-amber/30',
    glow: 'shadow-[0_0_20px_rgba(245,158,11,0.15)]',
    icon: '~',
  },
  'Independent Novelty': {
    color: 'text-signal-emerald',
    bg: 'bg-signal-emerald/10',
    border: 'border-signal-emerald/30',
    glow: 'shadow-[0_0_20px_rgba(16,185,129,0.15)]',
    icon: '\u2726',
  },
  'Cross-Link Novelty': {
    color: 'text-signal-cyan',
    bg: 'bg-signal-cyan/10',
    border: 'border-signal-cyan/30',
    glow: 'shadow-[0_0_20px_rgba(6,182,212,0.15)]',
    icon: '\u29BB',
  },
  'Direct Gap Fill': {
    color: 'text-signal-rose',
    bg: 'bg-signal-rose/10',
    border: 'border-signal-rose/30',
    glow: 'shadow-[0_0_20px_rgba(244,63,94,0.15)]',
    icon: '\u25CE',
  },
  'Uncertain Novelty': {
    color: 'text-signal-violet',
    bg: 'bg-signal-violet/10',
    border: 'border-signal-violet/30',
    glow: 'shadow-[0_0_20px_rgba(139,92,246,0.15)]',
    icon: '?',
  },
};

export default function ClassificationBadge({ label, confidence }) {
  const style = CLASSIFICATION_STYLES[label] || CLASSIFICATION_STYLES['Uncertain Novelty'];

  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 200, damping: 20 }}
      className={`inline-flex items-center gap-3 px-6 py-3 rounded-2xl border ${style.bg} ${style.border} ${style.glow}`}
    >
      <span className={`text-2xl ${style.color}`}>{style.icon}</span>
      <div>
        <div className={`text-sm font-semibold ${style.color}`}>{label}</div>
        <div className="text-xs text-gray-500">
          {(confidence * 100).toFixed(0)}% confidence
        </div>
      </div>
      {/* Confidence ring */}
      <div className="relative w-10 h-10 ml-2">
        <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
          <circle
            cx="18" cy="18" r="15"
            fill="none" stroke="currentColor"
            strokeWidth="3"
            className="text-void-700"
          />
          <motion.circle
            cx="18" cy="18" r="15"
            fill="none" stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={`${confidence * 94.25} 94.25`}
            className={style.color}
            initial={{ strokeDasharray: '0 94.25' }}
            animate={{ strokeDasharray: `${confidence * 94.25} 94.25` }}
            transition={{ duration: 1.2, ease: 'easeOut', delay: 0.3 }}
          />
        </svg>
        <div className={`absolute inset-0 flex items-center justify-center text-[10px] font-mono font-bold ${style.color}`}>
          {(confidence * 100).toFixed(0)}
        </div>
      </div>
    </motion.div>
  );
}
