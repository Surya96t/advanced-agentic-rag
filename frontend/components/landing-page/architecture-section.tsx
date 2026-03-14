'use client';

import { Icon } from '@iconify/react';
import { useScrollReveal } from './use-scroll-reveal';

/**
 * Renders the "Agentic Chain-of-Thought" section of the landing page.
 *
 * Displays a two-column layout: explanatory copy on the left (LangGraph
 * orchestration, smart routing, and query expansion feature cards) and a
 * faux-3D terminal on the right that reveals a live trace log and a TTFT
 * metric panel on hover. Scroll-reveal animations are applied via
 * {@link useScrollReveal}.
 *
 * @returns {JSX.Element} The architecture section element.
 */
export function ArchitectureSection() {
  useScrollReveal();

  return (
    <section id="architecture" className="py-32 px-6 border-t border-white/5 bg-[#0a0a0a] relative">
      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">

        {/* Left — text content */}
        <div className="space-y-10 reveal">
          <div className="flex items-center gap-2 text-[#fce9c8]">
            <Icon icon="solar:route-linear" className="text-lg" />
            <span className="text-xs tracking-widest uppercase font-semibold font-mono">LangGraph Orchestration</span>
          </div>

          <h2 className="text-4xl md:text-5xl font-semibold tracking-tighter leading-[1.15]">
            Agentic <br />
            <span className="text-white/40">Chain-of-Thought.</span>
          </h2>

          <p className="text-base text-white/60 font-light leading-relaxed max-w-lg">
            See exactly what the AI is doing before it answers. Query classification, semantic retrieval, cross-encoder re-ranking, and validation steps are all exposed in a transparent chain-of-thought panel.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div className="p-6 rounded-2xl border border-white/5 bg-white/2 hover:bg-white/4 transition-colors group cursor-pointer">
              <Icon icon="solar:git-network-linear" className="text-[#fce9c8] mb-4 text-2xl group-hover:scale-110 transition-transform block" />
              <h3 className="text-base font-semibold tracking-tight mb-2 text-white/90">Smart Routing</h3>
              <p className="text-xs text-white/50 leading-relaxed">Simple greetings bypass retrieval entirely for instant answers, saving compute.</p>
            </div>
            <div className="p-6 rounded-2xl border border-white/5 bg-white/2 hover:bg-white/4 transition-colors group cursor-pointer">
              <Icon icon="solar:magic-stick-3-linear" className="text-[#10b981] mb-4 text-2xl group-hover:scale-110 transition-transform block" />
              <h3 className="text-base font-semibold tracking-tight mb-2 text-white/90">Query Expansion</h3>
              <p className="text-xs text-white/50 leading-relaxed">Uses HyDE (Hypothetical Document Embeddings) to drastically improve recall.</p>
            </div>
          </div>
        </div>

        {/* Right — faux 3D terminal */}
        <div
          className="relative h-[550px] w-full group cursor-pointer reveal"
          style={{ perspective: '1000px' }}
        >
          {/* Glow */}
          <div className="absolute inset-0 bg-linear-to-tr from-[#3b82f6]/10 to-[#10b981]/10 rounded-2xl blur-[80px] opacity-30 group-hover:opacity-50 transition-opacity duration-700" />

          {/* Terminal card */}
          <div
            className="relative w-full h-full border border-white/10 rounded-2xl bg-[#030303] flex flex-col shadow-2xl overflow-hidden group-hover:shadow-[0_0_50px_rgba(252,233,200,0.1)] transition-all duration-700 ease-out"
            style={{ transformStyle: 'preserve-3d', transform: 'rotateY(-8deg) rotateX(4deg)' }}
          >
            {/* Title bar */}
            <div className="h-10 border-b border-white/10 bg-white/5 flex items-center px-4 gap-2 shrink-0">
              <div className="w-3 h-3 rounded-full bg-white/20" />
              <div className="w-3 h-3 rounded-full bg-white/20" />
              <div className="w-3 h-3 rounded-full bg-white/20" />
              <div className="ml-auto text-xs text-white/40 font-mono tracking-wide">langgraph_trace.log</div>
            </div>

            {/* Log content */}
            <div className="p-6 flex-1 font-mono text-xs text-white/60 leading-loose relative overflow-hidden">
              {/* Fade out at bottom */}
              <div className="absolute inset-0 bg-linear-to-b from-transparent via-transparent to-[#030303] pointer-events-none z-10" />

              <p className="text-white">{`> User query: "How do the embedding models work?"`}</p>
              <p className="opacity-70 mt-2">
                {`> Classifying intent: `}
                <span className="text-[#3b82f6]">RAG_REQUIRED</span>
              </p>
              <p className="opacity-70">{`> Rewriting query resolving pronouns...`}</p>
              <p className="opacity-70">{`> Generating HyDE document representation...`}</p>
              <p className="text-[#10b981] mt-4">{`> Vector search (HNSW) over 1,420 chunks`}</p>
              <p className="text-[#10b981]">{`> Keyword search (GIN) fallback executed`}</p>
              <p className="animate-pulse text-[#a855f7] mt-2">{`> Applying Reciprocal Rank Fusion (RRF)...`}</p>
              <p className="mt-4 text-[#fce9c8] opacity-0 group-hover:opacity-100 transition-opacity delay-300">
                {`> Re-ranking top 10 chunks via FlashRank local cross-encoder...`}
              </p>
              <p className="text-white opacity-0 group-hover:opacity-100 transition-opacity delay-500">
                {`> Initiating real-time SSE stream generation...`}
              </p>

              {/* TTFT hover card */}
              <div className="absolute bottom-6 right-6 left-6 z-20 bg-white/5 border border-white/10 backdrop-blur-md rounded-xl p-4 translate-y-8 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 transition-all duration-700 ease-out">
                <div className="flex justify-between text-white text-xs mb-3 font-sans font-medium tracking-wide">
                  <span>Time to First Token (TTFT)</span>
                  <span>240ms</span>
                </div>
                <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                  <div className="h-full bg-[#10b981] w-[85%] relative">
                    <div className="absolute top-0 right-0 bottom-0 left-0 bg-white/20 animate-pulse" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
