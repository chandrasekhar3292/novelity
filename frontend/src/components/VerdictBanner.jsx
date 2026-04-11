import { motion } from 'motion/react';

const VERDICT_STYLES = {
  novel: {
    headline: 'NOVEL',
    color: 'text-signal-emerald',
    bg: 'bg-signal-emerald/10',
    border: 'border-signal-emerald/40',
    glow: 'shadow-[0_0_30px_rgba(16,185,129,0.20)]',
    icon: '✓',
  },
  not_novel: {
    headline: 'NOT NOVEL',
    color: 'text-signal-rose',
    bg: 'bg-signal-rose/10',
    border: 'border-signal-rose/40',
    glow: 'shadow-[0_0_30px_rgba(244,63,94,0.20)]',
    icon: '✗',
  },
  gap_to_investigate: {
    headline: 'GAP TO INVESTIGATE',
    color: 'text-signal-cyan',
    bg: 'bg-signal-cyan/10',
    border: 'border-signal-cyan/40',
    glow: 'shadow-[0_0_30px_rgba(6,182,212,0.20)]',
    icon: '◎',
  },
  out_of_scope: {
    headline: 'OUT OF SCOPE',
    color: 'text-signal-amber',
    bg: 'bg-signal-amber/10',
    border: 'border-signal-amber/40',
    glow: 'shadow-[0_0_30px_rgba(245,158,11,0.20)]',
    icon: '~',
  },
  uncertain: {
    headline: 'UNCERTAIN',
    color: 'text-signal-violet',
    bg: 'bg-signal-violet/10',
    border: 'border-signal-violet/40',
    glow: 'shadow-[0_0_30px_rgba(139,92,246,0.20)]',
    icon: '?',
  },
};

export default function VerdictBanner({ verdict, verdictText }) {
  const style = VERDICT_STYLES[verdict] || VERDICT_STYLES.uncertain;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className={`flex items-center gap-5 px-6 py-5 rounded-2xl border ${style.bg} ${style.border} ${style.glow}`}
    >
      <div className={`flex-shrink-0 w-14 h-14 rounded-full ${style.bg} border ${style.border} flex items-center justify-center`}>
        <span className={`text-3xl font-bold ${style.color}`}>{style.icon}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className={`text-2xl font-bold tracking-wide ${style.color}`}>
          {style.headline}
        </div>
        {verdictText && (
          <div className="text-sm text-gray-400 mt-1">{verdictText}</div>
        )}
      </div>
    </motion.div>
  );
}
