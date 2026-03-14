'use client';

import Link from 'next/link';
import { Icon } from '@iconify/react';
import { useScrollReveal } from './use-scroll-reveal';

/**
 * Hero section — full-viewport, centered, with pulsing rings, gradient headline,
 * feature pills, and dual CTA buttons.
 */
export function HeroSection() {
  useScrollReveal();

  return (
    <section id="vision" className="relative min-h-screen flex flex-col items-center justify-center pt-24 px-6 overflow-hidden bg-[#0a0a0a]">

      {/* Pulsing background rings */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none z-0 flex items-center justify-center">
        <div className="absolute w-[800px] h-[800px] bg-[#fce9c8]/10 rounded-full blur-[120px] animate-pulse" style={{ animationDuration: '5s' }} />
        <div className="absolute w-[300px] h-[300px] border-2 border-[#fce9c8]/20 rounded-full animate-ping" style={{ animationDuration: '6s' }} />
        <div className="absolute w-[500px] h-[500px] border border-[#fce9c8]/10 rounded-full animate-ping" style={{ animationDuration: '8s', animationDelay: '2s' }} />
      </div>

      {/* Main content */}
      <div className="relative z-10 text-center max-w-5xl mx-auto flex flex-col items-center reveal" style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}>

        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[#fce9c8]/30 bg-[#fce9c8]/10 mb-8 cursor-pointer">
          <span className="relative flex w-2 h-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#fce9c8] opacity-75" />
            <span className="relative inline-flex rounded-full w-2 h-2 bg-[#fce9c8]" />
          </span>
          <span className="text-xs font-medium text-[#fce9c8] tracking-wide">Production-Ready Architecture</span>
        </div>

        {/* Headline */}
        <h1 className="text-6xl md:text-8xl font-semibold tracking-tighter text-transparent bg-clip-text bg-linear-to-b from-white via-white/90 to-white/30 mb-6 leading-[1.05]" style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
          Advanced<br /><span className="text-[#fce9c8]">RAG System</span>
        </h1>

        {/* Sub-description */}
        <p className="text-base text-white/60 font-light leading-relaxed max-w-2xl mb-10">
          A production-grade architecture that ingests documents, generates robust embeddings, and retrieves precise semantic context to power accurate, human-like AI answers.
        </p>

        {/* Feature pills */}
        <div className="flex flex-col sm:flex-row gap-4 mb-12 opacity-80">
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/5 bg-white/2">
            <Icon icon="solar:documents-linear" className="text-[#3b82f6]" />
            <span className="text-xs text-white/70 tracking-wide">.pdf, .md, .txt</span>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/5 bg-white/2">
            <Icon icon="solar:magnifer-linear" className="text-[#10b981]" />
            <span className="text-xs text-white/70 tracking-wide">Hybrid Search</span>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/5 bg-white/2">
            <Icon icon="solar:route-linear" className="text-[#fce9c8]" />
            <span className="text-xs text-white/70 tracking-wide">Agentic workflows</span>
          </div>
        </div>

        {/* CTAs */}
        <div className="flex items-center gap-4">
          <Link
            href="/sign-in"
            className="group relative inline-flex items-center gap-3 px-8 py-3.5 bg-[#fce9c8] text-black rounded-full transition-all hover:bg-[#fce9c8]/90 hover:scale-105"
          >
            <span className="text-sm font-semibold tracking-tight">Try Me</span>
            <Icon icon="solar:arrow-right-linear" className="group-hover:translate-x-1 transition-transform" />
          </Link>
          <a
            href="https://github.com/surya96t/advanced-agentic-rag"
            target="_blank"
            rel="noopener noreferrer"
            className="group relative inline-flex items-center gap-3 px-8 py-3.5 bg-white/2 border border-white/10 text-white rounded-full transition-all hover:bg-white/5"
          >
            <span className="text-sm font-semibold tracking-tight">GitHub</span>
            <Icon icon="solar:code-circle-linear" />
          </a>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-3 opacity-50">
        <div className="w-px h-12 bg-linear-to-b from-transparent via-[#fce9c8]/50 to-transparent" />
        <span className="text-xs uppercase tracking-widest font-mono text-white/40">Scroll</span>
      </div>
    </section>
  );
}
