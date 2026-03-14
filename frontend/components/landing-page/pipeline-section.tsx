'use client';

import { Icon } from '@iconify/react';
import { useScrollReveal } from './use-scroll-reveal';

const STEPS = [
  {
    icon: 'solar:document-add-linear',
    number: '01',
    color: '#3b82f6',
    title: 'Ingest Docs',
    description: 'Upload PDFs, Markdown, and plain text files. Processed automatically via Celery background jobs.',
  },
  {
    icon: 'solar:layers-linear',
    number: '02',
    color: '#a855f7',
    title: 'Embed Data',
    description: 'Generate robust embeddings using text-embedding-3-small and securely store in Supabase pgvector.',
  },
  {
    icon: 'solar:magnifer-linear',
    number: '03',
    color: '#10b981',
    title: 'Retrieve Context',
    description: 'Hybrid search combining dense (HNSW) and sparse (GIN) indexes, fused with Reciprocal Rank Fusion.',
  },
  {
    icon: 'solar:chat-round-line-linear',
    number: '04',
    color: '#fce9c8',
    title: 'Answer Human',
    description: 'Stream accurate, human-like responses token-by-token with fully traceable inline citations.',
  },
] as const;

export function PipelineSection() {
  useScrollReveal();

  return (
    <section id="pipeline" className="py-32 px-6 border-t border-white/5 bg-[#0a0a0a]">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row justify-between items-end mb-16 gap-6 reveal">
          <div>
            <div className="flex items-center gap-2 text-[#fce9c8] mb-4">
              <Icon icon="solar:route-linear" className="text-lg" />
              <span className="text-xs tracking-widest uppercase font-semibold font-mono">How it works</span>
            </div>
            <h2 className="text-3xl md:text-4xl font-semibold tracking-tighter text-white">
              From Document to Answer.
            </h2>
          </div>
          <p className="text-white/50 text-base max-w-md font-light text-right">
            A four-stage pipeline that handles ingestion, embedding, retrieval, and generation with full observability.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {STEPS.map((step, i) => (
            <div
              key={step.number}
              className="p-8 rounded-2xl border border-white/5 bg-[#0a0a0a] hover:bg-white/2 transition-colors relative group overflow-hidden cursor-pointer reveal"
              style={{ transitionDelay: `${i * 100}ms` }}
            >
              {/* Top glow line on hover */}
              <div
                className="absolute top-0 left-0 w-full h-px opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                style={{
                  background: `linear-gradient(to right, transparent, ${step.color}80, transparent)`,
                }}
              />
              <div className="flex justify-between items-start mb-8">
                <Icon
                  icon={step.icon}
                  className="text-white/30 text-3xl"
                />
                <span
                  className="text-xs font-mono px-2.5 py-1 rounded"
                  style={{ color: step.color, backgroundColor: `${step.color}1a` }}
                >
                  {step.number}
                </span>
              </div>
              <h3 className="text-lg font-semibold tracking-tight mb-3 text-white/90 group-hover:text-white transition-colors">
                {step.title}
              </h3>
              <p className="text-xs text-white/50 leading-relaxed">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
