'use client';

import { useScrollReveal } from './use-scroll-reveal';

const FEATURES = [
  {
    accent: '#fce9c8',
    label: 'Chat Interface',
    title: 'AI Chat with Citations',
    description:
      'Conversations stream token-by-token. Every answer includes inline citations linked back to the exact source chunk with text previews.',
    background: 'radial-gradient(circle at 80% 20%, rgba(252,233,200,0.15) 0%, transparent 50%)',
    decoration: null,
    delay: '0ms',
  },
  {
    accent: '#3b82f6',
    label: 'Smart Query Engine',
    title: 'Multi-part Resolution',
    description:
      'Complex questions break into sub-queries. Follow-up questions resolve pronouns seamlessly based on conversational history.',
    background: 'radial-gradient(circle at 20% 80%, rgba(59,130,246,0.15) 0%, transparent 50%)',
    decoration: 'rings',
    delay: '100ms',
  },
  {
    accent: '#10b981',
    label: 'Dashboard',
    title: 'Real-Time Metrics',
    description:
      'At-a-glance visibility into processed documents, total chunks, token usage, estimated costs, and real-time step durations.',
    background: 'radial-gradient(circle at 50% 50%, rgba(16,185,129,0.1) 0%, transparent 60%)',
    decoration: 'squares',
    delay: '200ms',
  },
] as const;

/**
 * Renders the "Core Capabilities" section of the landing page.
 *
 * Displays three tall hover-card tiles showcasing the system's key user-facing
 * features: AI Chat with Citations, Multi-part Resolution, and Real-Time
 * Metrics. Each card reveals a description and a radial accent glow on hover.
 * Scroll-reveal animations are applied via {@link useScrollReveal}.
 *
 * @returns {JSX.Element} The features section element.
 */
export function FeaturesSection() {
  useScrollReveal();

  return (
    <section id="features" className="py-32 px-6 border-t border-white/5 bg-[#0a0a0a]">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row justify-between items-end mb-16 gap-6 reveal">
          <div>
            <h2 className="text-3xl md:text-4xl font-semibold tracking-tighter text-white mb-4">
              Core Capabilities
            </h2>
            <p className="text-white/50 text-base max-w-xl font-light">
              Engineered to handle your private data at scale, securely.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {FEATURES.map((feat) => (
            <div
              key={feat.title}
              className="group relative aspect-4/5 md:aspect-3/4 rounded-2xl overflow-hidden border border-white/5 cursor-pointer bg-white/1 reveal"
              style={{ transitionDelay: feat.delay }}
            >
              {/* Radial glow */}
              <div
                className="absolute inset-0 opacity-40 group-hover:opacity-60 transition-opacity duration-700"
                style={{ background: feat.background }}
              />

              {/* Grid overlay */}
              <div
                className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)]"
                style={{
                  backgroundSize: '24px 24px',
                  maskImage: 'radial-gradient(ellipse 70% 70% at 50% 50%, #000 30%, transparent 100%)',
                }}
              />

              {/* Rings decoration (card 2) */}
              {feat.decoration === 'rings' && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="w-[120%] h-[120%] border border-white/2 rounded-full scale-75 group-hover:scale-100 transition-transform duration-1000 ease-out" />
                  <div className="absolute w-[80%] h-[80%] border border-white/2 rounded-full scale-75 group-hover:scale-100 transition-transform duration-1000 delay-100 ease-out" />
                </div>
              )}

              {/* Squares decoration (card 3) */}
              {feat.decoration === 'squares' && (
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full flex items-center justify-center pointer-events-none">
                  <div className="w-24 h-24 border border-white/5 rounded-lg rotate-45 group-hover:rotate-90 transition-transform duration-1000 ease-out" />
                  <div className="absolute w-16 h-16 border border-white/10 rounded-lg rotate-12 group-hover:-rotate-45 transition-transform duration-1000 delay-100 ease-out" />
                </div>
              )}

              {/* Text content */}
              <div className="absolute bottom-0 left-0 w-full p-8 translate-y-4 group-hover:translate-y-0 transition-transform duration-500 ease-out">
                <div
                  className="text-xs font-mono mb-3 tracking-widest uppercase"
                  style={{ color: feat.accent }}
                >
                  {feat.label}
                </div>
                <h3 className="text-2xl font-semibold tracking-tight text-white mb-2">{feat.title}</h3>
                <p className="text-white/50 text-sm opacity-100 md:opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity duration-500 delay-100 leading-relaxed font-light">
                  {feat.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
