import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';

export default function PaperCard({ paper, index = 0, similarity }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08 }}
      className="glass-hover p-5 cursor-pointer"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-gray-200 leading-snug line-clamp-2">
            {paper.title || paper.id}
          </h4>
          <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
            {paper.year && <span className="font-mono">{paper.year}</span>}
            {paper.authors?.length > 0 && (
              <span className="truncate max-w-[200px]">
                {paper.authors.slice(0, 3).join(', ')}
                {paper.authors.length > 3 && ` +${paper.authors.length - 3}`}
              </span>
            )}
          </div>
        </div>
        {similarity !== undefined && (
          <div className="flex-shrink-0 text-right">
            <div className="font-mono text-sm font-bold text-nova-400">
              {(similarity * 100).toFixed(1)}%
            </div>
            <div className="text-[10px] text-gray-600 uppercase tracking-wider">match</div>
          </div>
        )}
      </div>

      {paper.concepts?.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {paper.concepts.slice(0, 5).map((c) => (
            <span key={c} className="tag text-[10px]">{c}</span>
          ))}
          {paper.concepts.length > 5 && (
            <span className="tag text-[10px] text-gray-500">+{paper.concepts.length - 5}</span>
          )}
        </div>
      )}

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="glow-line mt-4 mb-3" />
            <p className="text-xs text-gray-400 leading-relaxed">
              {paper.abstract}
            </p>
            {paper.url && (
              <a
                href={paper.url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="inline-flex items-center gap-1.5 mt-3 text-xs text-nova-400 hover:text-nova-500 transition-colors"
              >
                View paper &rarr;
              </a>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
