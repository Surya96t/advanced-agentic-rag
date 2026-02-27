'use client';

import Link from 'next/link';
import { Github, FileText, Cpu, Database, Sparkles, ArrowRight, ArrowDown } from 'lucide-react';

/**
 * Hero Section
 *
 * Matches the reference design:
 * - Dark #0a0a0a background with grid pattern and radial vignette
 * - Space Grotesk headings and buttons
 * - CTA buttons: "View Architecture" (ghost) and "Deploy Pipeline" (warm cream)
 * - 3D isometric pipeline visualization with animated light beams
 * - 4-step pipeline flow: Ingest Docs → Embed Data → Retrieve Context → Answer Human
 */
export function HeroSection() {
  return (
    <section className="relative w-full h-screen flex flex-col items-center justify-center bg-[#0a0a0a] overflow-hidden selection:bg-white/20">
      {/* Grid background */}
      <div className="absolute inset-0 z-0 bg-[linear-gradient(to_right,#ffffff05_1px,transparent_1px),linear-gradient(to_bottom,#ffffff05_1px,transparent_1px)] bg-size-[3rem_3rem]" />
      {/* Radial vignette */}
      <div className="absolute inset-0 z-0 bg-[radial-gradient(circle_800px_at_center,transparent_20%,#0a0a0a_100%)] pointer-events-none" />

      {/* Main content */}
      <div className="relative z-10 w-full max-w-5xl px-6 flex flex-col items-center text-center">

        {/* Heading */}
        <h1
          className="text-5xl md:text-6xl font-medium tracking-tight text-white mb-5"
          style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
        >
          Advanced RAG System
        </h1>

        {/* Description */}
        <p className="text-lg md:text-xl text-gray-400 mb-10 max-w-3xl font-light leading-relaxed mx-auto">
          A production-grade architecture that ingests documents, generates robust
          embeddings, and retrieves precise semantic context to power accurate,
          human-like AI answers.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto mb-12">
          <Link
            href="https://github.com/yourusername/advanced-agentic-rag"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg border border-white/10 bg-[#ffffff05] hover:bg-[#ffffff0a] transition-colors text-base text-gray-200 font-normal w-full sm:w-auto"
            style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
          >
            <Github className="w-4 h-4" />
            View Architecture
          </Link>
          <Link
            href="/sign-in"
            className="flex items-center justify-center px-5 py-2.5 rounded-lg bg-[#fce9c8] hover:bg-[#f3dfbe] transition-colors text-base text-black font-normal w-full sm:w-auto"
            style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
          >
            Try Me
          </Link>
        </div>

        {/* Pipeline Visualization */}
        <div className="w-full max-w-3xl mx-auto mb-16 flex items-center justify-center gap-0">

          {/* Node 1: File Text (blue) */}
          <div className="relative w-16 h-16 sm:w-20 sm:h-20 flex items-center justify-center transition-all duration-500 hover:scale-110 cursor-pointer shrink-0">
            <div className="absolute inset-0 bg-blue-500/20 blur-xl rounded-full" />
            <div className="absolute inset-0 bg-[#111] border border-white/20 rounded-xl" />
            <div className="absolute inset-0 bg-blue-500/10 rounded-xl border border-blue-500/30" />
            <FileText className="relative text-blue-400 drop-shadow-[0_0_12px_rgba(59,130,246,0.6)] w-6 h-6 sm:w-8 sm:h-8" strokeWidth={1.5} />
          </div>

          {/* Connector 1 (blue) */}
          <div className="flex-1 h-[2px] bg-blue-500/20 relative overflow-hidden">
            <div className="absolute top-0 left-0 h-full w-full bg-linear-to-r from-transparent via-blue-400/80 to-transparent animate-travel-1" />
          </div>

          {/* Node 2: CPU (purple) */}
          <div className="relative w-16 h-16 sm:w-20 sm:h-20 flex items-center justify-center transition-all duration-500 hover:scale-110 cursor-pointer shrink-0">
            <div className="absolute inset-0 bg-purple-500/20 blur-xl rounded-full" />
            <div className="absolute inset-0 bg-[#111] border border-white/20 rounded-xl" />
            <div className="absolute inset-0 bg-purple-500/10 rounded-xl border border-purple-500/30" />
            <Cpu className="relative text-purple-400 drop-shadow-[0_0_12px_rgba(168,85,247,0.6)] w-6 h-6 sm:w-8 sm:h-8" strokeWidth={1.5} />
          </div>

          {/* Connector 2 (purple) */}
          <div className="flex-1 h-[2px] bg-purple-500/20 relative overflow-hidden">
            <div className="absolute top-0 left-0 h-full w-full bg-linear-to-r from-transparent via-purple-400/80 to-transparent animate-travel-2" />
          </div>

          {/* Node 3: Database (emerald) */}
          <div className="relative w-16 h-16 sm:w-20 sm:h-20 flex items-center justify-center transition-all duration-500 hover:scale-110 cursor-pointer shrink-0">
            <div className="absolute inset-0 bg-emerald-500/20 blur-xl rounded-full" />
            <div className="absolute inset-0 bg-[#111] border border-white/20 rounded-xl" />
            <div className="absolute inset-0 bg-emerald-500/10 rounded-xl border border-emerald-500/30" />
            <Database className="relative text-emerald-400 drop-shadow-[0_0_12px_rgba(16,185,129,0.6)] w-6 h-6 sm:w-8 sm:h-8" strokeWidth={1.5} />
          </div>

          {/* Connector 3 (emerald) */}
          <div className="flex-1 h-[2px] bg-emerald-500/20 relative overflow-hidden">
            <div className="absolute top-0 left-0 h-full w-full bg-linear-to-r from-transparent via-emerald-400/80 to-transparent animate-travel-3" />
          </div>

          {/* Node 4: Sparkles (warm cream) */}
          <div className="relative w-16 h-16 sm:w-20 sm:h-20 flex items-center justify-center transition-all duration-500 hover:scale-110 cursor-pointer shrink-0">
            <div className="absolute inset-0 bg-[#fce9c8]/20 blur-xl rounded-full" />
            <div className="absolute inset-0 bg-[#111] border border-white/20 rounded-xl" />
            <div className="absolute inset-0 bg-[#fce9c8]/10 rounded-xl border border-[#fce9c8]/30" />
            <Sparkles className="relative text-[#fce9c8] drop-shadow-[0_0_12px_rgba(252,233,200,0.6)] w-6 h-6 sm:w-8 sm:h-8" strokeWidth={1.5} />
          </div>

        </div>

        {/* Pipeline Flow Steps */}
        <div
          className="flex flex-col md:flex-row items-center justify-center gap-4 md:gap-6 text-base text-gray-400 font-normal"
          style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
        >
          {/* Step 1: Ingest Docs */}
          <div className="flex items-center gap-3 group cursor-default">
            <span className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-400 group-hover:bg-blue-500/20 group-hover:scale-110 transition-all">
              <FileText className="w-4 h-4" strokeWidth={1.5} />
            </span>
            <span className="text-blue-400/80 group-hover:text-blue-400 transition-colors font-medium">
              Ingest Docs
            </span>
          </div>

          <ArrowRight className="w-4 h-4 text-[#333] hidden md:block" strokeWidth={1.5} />
          <ArrowDown className="w-4 h-4 text-[#333] md:hidden" strokeWidth={1.5} />

          {/* Step 2: Embed Data */}
          <div className="flex items-center gap-3 group cursor-default">
            <span className="flex items-center justify-center w-8 h-8 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-400 group-hover:bg-purple-500/20 group-hover:scale-110 transition-all">
              <Cpu className="w-4 h-4" strokeWidth={1.5} />
            </span>
            <span className="text-purple-400/80 group-hover:text-purple-400 transition-colors font-medium">
              Embed Data
            </span>
          </div>

          <ArrowRight className="w-4 h-4 text-[#333] hidden md:block" strokeWidth={1.5} />
          <ArrowDown className="w-4 h-4 text-[#333] md:hidden" strokeWidth={1.5} />

          {/* Step 3: Retrieve Context */}
          <div className="flex items-center gap-3 group cursor-default">
            <span className="flex items-center justify-center w-8 h-8 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 group-hover:bg-emerald-500/20 group-hover:scale-110 transition-all">
              <Database className="w-4 h-4" strokeWidth={1.5} />
            </span>
            <span className="text-emerald-400/80 group-hover:text-emerald-400 transition-colors font-medium">
              Retrieve Context
            </span>
          </div>

          <ArrowRight className="w-4 h-4 text-[#333] hidden md:block" strokeWidth={1.5} />
          <ArrowDown className="w-4 h-4 text-[#333] md:hidden" strokeWidth={1.5} />

          {/* Step 4: Answer Human */}
          <div className="flex items-center gap-3 group cursor-default">
            <span className="flex items-center justify-center w-8 h-8 rounded-full bg-[#fce9c8]/10 border border-[#fce9c8]/30 text-[#fce9c8] group-hover:bg-[#fce9c8]/20 group-hover:scale-110 transition-all">
              <Sparkles className="w-4 h-4" strokeWidth={1.5} />
            </span>
            <span className="text-[#fce9c8]/80 group-hover:text-[#fce9c8] transition-colors font-medium">
              Answer Human
            </span>
          </div>
        </div>

      </div>
    </section>
  );
}
