import { useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { useEffect, useState } from 'react';
import { api } from '../api';

function FloatingOrb({ className, delay = 0 }) {
  return (
    <motion.div
      className={`absolute rounded-full blur-3xl pointer-events-none ${className}`}
      animate={{
        y: [0, -30, 0],
        x: [0, 15, 0],
        scale: [1, 1.1, 1],
      }}
      transition={{
        duration: 8,
        repeat: Infinity,
        ease: 'easeInOut',
        delay,
      }}
    />
  );
}

function GridBackground() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {/* Grid lines */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(0,212,170,0.3) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,212,170,0.3) 1px, transparent 1px)
          `,
          backgroundSize: '60px 60px',
        }}
      />
      {/* Radial fade */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,#050810_70%)]" />
    </div>
  );
}

export default function Landing() {
  const navigate = useNavigate();
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => {});
  }, []);

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center px-6">
      <GridBackground />

      {/* Atmospheric orbs */}
      <FloatingOrb className="w-96 h-96 bg-nova-500/[0.07] -top-20 -left-48" delay={0} />
      <FloatingOrb className="w-80 h-80 bg-nebula-500/[0.06] top-1/3 -right-40" delay={2} />
      <FloatingOrb className="w-64 h-64 bg-signal-cyan/[0.05] bottom-20 left-1/4" delay={4} />

      {/* Main content */}
      <motion.div
        className="relative z-10 text-center max-w-3xl mx-auto"
        initial="hidden"
        animate="visible"
        variants={{
          hidden: {},
          visible: { transition: { staggerChildren: 0.12 } },
        }}
      >
        {/* Overline */}
        <motion.div
          variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full
                     bg-void-800/60 border border-white/[0.06] text-xs text-gray-400 mb-8"
        >
          <span className={`w-1.5 h-1.5 rounded-full ${health ? 'bg-signal-emerald animate-pulse' : 'bg-gray-600'}`} />
          {health ? 'Online' : 'Connecting...'}
        </motion.div>

        {/* Title */}
        <motion.h1
          variants={{ hidden: { opacity: 0, y: 30 }, visible: { opacity: 1, y: 0 } }}
          className="font-display text-6xl sm:text-7xl lg:text-8xl font-bold tracking-tight leading-[0.95]"
        >
          <span className="text-white">Novelity</span>
          <span className="text-gradient">Net</span>
        </motion.h1>

        {/* Tagline */}
        <motion.p
          variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
          className="mt-6 text-lg sm:text-xl text-gray-400 leading-relaxed max-w-xl mx-auto"
        >
          Discover if your research idea is truly novel.
          <span className="text-gray-500"> Multi-signal analysis across similarity, density, recency & cross-domain linkage.</span>
        </motion.p>

        {/* CTA */}
        <motion.div
          variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
          className="mt-10 flex items-center justify-center gap-4"
        >
          <button onClick={() => navigate('/analyze')} className="btn-primary text-base">
            Analyze an Idea
          </button>
          <button onClick={() => navigate('/corpus')} className="btn-ghost">
            Browse Corpus
          </button>
        </motion.div>

        {/* Signal cards */}
        <motion.div
          variants={{ hidden: { opacity: 0, y: 30 }, visible: { opacity: 1, y: 0 } }}
          className="mt-20 grid grid-cols-2 sm:grid-cols-3 gap-3"
        >
          {[
            { label: 'Similarity', desc: 'Semantic matching', icon: '\u2261' },
            { label: 'Density', desc: 'Publication volume', icon: '\u2593' },
            { label: 'Recency', desc: 'Trend analysis', icon: '\u2197' },
            { label: 'Cross-Link', desc: 'Concept rarity', icon: '\u29BB' },
            { label: 'Classification', desc: 'Rule-based label', icon: '\u25C8' },
            { label: 'Explanation', desc: 'Deterministic output', icon: '\u00B6' },
          ].map(({ label, desc, icon }, i) => (
            <motion.div
              key={label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 + i * 0.08 }}
              className="glass p-4 text-left group hover:border-nova-500/15 transition-all duration-300"
            >
              <span className="text-lg text-nova-500/60 group-hover:text-nova-400 transition-colors">
                {icon}
              </span>
              <div className="mt-2 text-sm font-medium text-gray-300">{label}</div>
              <div className="text-xs text-gray-600">{desc}</div>
            </motion.div>
          ))}
        </motion.div>
      </motion.div>
    </div>
  );
}
