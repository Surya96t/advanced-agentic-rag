'use client';

import Link from 'next/link';
import { Icon } from '@iconify/react';
import { useScrollReveal } from './use-scroll-reveal';

const TECH_LOGOS = [
  { icon: 'simple-icons:nextdotjs', label: 'Next.js', hoverColor: '#ffffff' },
  { icon: 'simple-icons:typescript', label: 'TypeScript', hoverColor: '#3178c6' },
  { icon: 'simple-icons:tailwindcss', label: 'Tailwind', hoverColor: '#38bdf8' },
  { icon: 'simple-icons:python', label: 'Python', hoverColor: '#ffde57' },
  { icon: 'simple-icons:fastapi', label: 'FastAPI', hoverColor: '#009688' },
  { icon: 'simple-icons:openai', label: 'OpenAI', hoverColor: '#10a37f' },
  { icon: 'simple-icons:supabase', label: 'Supabase', hoverColor: '#3ecf8e' },
  { icon: 'simple-icons:redis', label: 'Redis', hoverColor: '#dc382d' },
] as const;

const IMPL_COLUMNS = [
  {
    icon: 'solar:shield-keyhole-linear',
    iconColor: '#fce9c8',
    title: 'Identity & Security',
    items: [
      'Clerk Authentication',
      'Postgres Row-Level Security (RLS)',
      'Redis API Rate Limiting',
      'LangSmith Tracing & Observability',
    ],
  },
  {
    icon: 'solar:magnifer-linear',
    iconColor: '#3b82f6',
    title: 'Advanced Retrieval',
    items: [
      'pgvector (HNSW) Dense Search',
      'Full-text (GIN) Sparse Fallback',
      'FlashRank Local Cross-Encoder',
      'Reciprocal Rank Fusion (RRF)',
    ],
  },
  {
    icon: 'solar:bolt-linear',
    iconColor: '#10b981',
    title: 'Agentic & Async Ops',
    items: [
      'LangGraph State Machines',
      'Async SSE Generation Streaming',
      'Celery Background Document Jobs',
      'Dynamic Query Routing',
    ],
  },
] as const;

export function TechStackSection() {
  useScrollReveal();

  return (
    <section id="try" className="py-32 px-6 bg-[#0a0a0a] border-t border-white/5 relative overflow-hidden">
      {/* Ambient glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-[#fce9c8]/5 rounded-full blur-[120px] pointer-events-none" />

      <div className="max-w-6xl mx-auto relative z-10 reveal">
        {/* Header */}
        <div className="text-center mb-16">
          <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-[#0a0a0a] border border-white/10 flex items-center justify-center shadow-[0_0_30px_rgba(252,233,200,0.1)]">
            <Icon icon="solar:server-square-linear" className="text-[#fce9c8] text-3xl" />
          </div>
          <h2 className="text-4xl md:text-5xl font-semibold tracking-tighter mb-4">
            Built for Production
          </h2>
          <p className="text-white/50 text-base font-light max-w-xl mx-auto">
            A modern, scalable technical stack meticulously chosen for robust document retrieval and agentic coordination.
          </p>
        </div>

        {/* Logo grid */}
        <div className="mb-24">
          <h3 className="text-xs font-mono tracking-widest text-white/30 uppercase text-center mb-10">
            Core Technologies
          </h3>
          <div className="flex flex-wrap justify-center items-center gap-10 md:gap-16">
            {TECH_LOGOS.map((tech) => (
              <div key={tech.label} className="group flex flex-col items-center gap-3 cursor-pointer">
                <Icon
                  icon={tech.icon}
                  className="text-4xl text-white/40 transition-all duration-300 group-hover:-translate-y-1"
                  onMouseEnter={(e) => { (e.currentTarget as unknown as HTMLElement).style.color = tech.hoverColor; }}
                  onMouseLeave={(e) => { (e.currentTarget as unknown as HTMLElement).style.color = ''; }}
                />
                <span className="text-[10px] font-mono tracking-wider text-white/30 group-hover:text-white/70 transition-colors opacity-0 group-hover:opacity-100">
                  {tech.label}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Implementation details table */}
        <div className="p-8 md:p-12 bg-white/1 border border-white/5 rounded-3xl backdrop-blur-xl">
          <h3 className="text-xs font-mono tracking-widest text-white/30 uppercase mb-8 border-b border-white/5 pb-4">
            Implementation Details
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
            {IMPL_COLUMNS.map((col) => (
              <div key={col.title}>
                <div className="flex items-center gap-2 mb-4 text-white/80">
                  <Icon icon={col.icon} style={{ color: col.iconColor }} />
                  <h4 className="text-sm font-semibold tracking-tight">{col.title}</h4>
                </div>
                <ul className="space-y-3 text-sm text-white/50 font-light">
                  {col.items.map((item) => (
                    <li key={item} className="flex items-start gap-2">
                      <span className="text-white/20 mt-0.5">•</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="mt-16 flex justify-center">
          <Link
            href="/sign-in"
            className="group bg-[#fce9c8] text-black px-8 py-3.5 rounded-full text-sm font-semibold tracking-tight hover:scale-105 transition-all inline-flex items-center gap-2 cursor-pointer shadow-[0_0_20px_rgba(252,233,200,0.15)]"
          >
            Sign In to Try
            <Icon
              icon="solar:arrow-right-up-linear"
              className="group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform"
            />
          </Link>
        </div>
      </div>
    </section>
  );
}
