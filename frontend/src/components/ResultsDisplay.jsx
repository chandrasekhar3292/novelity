import { motion } from 'motion/react';
import ClassificationBadge from './ClassificationBadge';
import VerdictBanner from './VerdictBanner';
import SignalGauge from './SignalGauge';
import PaperCard from './PaperCard';

function Section({ title, delay = 0, children }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
    >
      <h3 className="text-xs uppercase tracking-[0.2em] text-gray-500 font-semibold mb-4">
        {title}
      </h3>
      {children}
    </motion.section>
  );
}

export default function ResultsDisplay({ data }) {
  const { idea, similar_papers, features, classification, explanation } = data;

  const signalOrder = [
    'max_similarity',
    'mean_similarity',
    'similarity_spread',
    'density_score',
    'recency_score',
    'crosslink_score',
  ];

  return (
    <div className="space-y-8 mt-10">
      {/* Verdict */}
      {classification.verdict && (
        <Section title="Verdict" delay={0}>
          <VerdictBanner
            verdict={classification.verdict}
            verdictText={classification.verdict_text}
            score={classification.novelty_score}
          />
        </Section>
      )}

      {/* Classification */}
      <Section title="Classification" delay={0.05}>
        <ClassificationBadge label={classification.label} confidence={classification.confidence} />
      </Section>

      {/* Extracted Concepts */}
      {idea && (
        <Section title="Extracted Signals" delay={0.15}>
          <div className="glass p-5 space-y-4">
            {idea.domains?.length > 0 && (
              <div>
                <span className="text-xs text-gray-500 uppercase tracking-wider">Domains</span>
                <div className="flex flex-wrap gap-2 mt-2">
                  {idea.domains.map((d) => (
                    <span key={d} className="tag border-nebula-500/20 text-nebula-400">{d}</span>
                  ))}
                </div>
              </div>
            )}
            {idea.concepts?.length > 0 && (
              <div>
                <span className="text-xs text-gray-500 uppercase tracking-wider">Concepts</span>
                <div className="flex flex-wrap gap-2 mt-2">
                  {idea.concepts.map((c) => (
                    <span key={c} className="tag border-nova-500/20 text-nova-400">{c}</span>
                  ))}
                </div>
              </div>
            )}
            {idea.applications?.length > 0 && (
              <div>
                <span className="text-xs text-gray-500 uppercase tracking-wider">Applications</span>
                <div className="flex flex-wrap gap-2 mt-2">
                  {idea.applications.map((a) => (
                    <span key={a} className="tag border-signal-amber/20 text-signal-amber">{a}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Section>
      )}

      {/* Signal Breakdown */}
      <Section title="Signal Breakdown" delay={0.3}>
        <div className="glass p-6 space-y-5">
          {signalOrder.map((key) => {
            // Map gauge keys to the informative_signals keys reported by the
            // backend. Similarity-derived gauges all share the "similarity"
            // informativeness flag.
            const sigKey = key
              .replace('max_similarity', 'similarity')
              .replace('mean_similarity', 'similarity')
              .replace('similarity_spread', 'similarity')
              .replace('density_score', 'density')
              .replace('recency_score', 'recency')
              .replace('crosslink_score', 'crosslink');
            const informative = classification.informative_signals;
            const degraded =
              informative !== undefined && informative[sigKey] === false;
            return (
              <SignalGauge
                key={key}
                name={key}
                value={features[key]}
                degraded={degraded}
              />
            );
          })}
        </div>
      </Section>

      {/* Explanation */}
      {explanation && (
        <Section title="Explanation" delay={0.45}>
          <div className="glass p-5">
            <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
              {explanation}
            </p>
          </div>
        </Section>
      )}

      {/* Similar Papers */}
      {similar_papers?.length > 0 && (
        <Section title={`Similar Papers (${similar_papers.length})`} delay={0.6}>
          <div className="space-y-3">
            {similar_papers.map((paper, i) => (
              <PaperCard
                key={paper.id}
                paper={paper}
                index={i}
                similarity={paper.similarity}
              />
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}
