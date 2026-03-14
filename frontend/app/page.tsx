import { NeuralCanvas } from '@/components/landing-page/neural-canvas';
import { CustomCursor } from '@/components/landing-page/custom-cursor';
import { NavSection } from '@/components/landing-page/nav-section';
import { HeroSection } from '@/components/landing-page/hero-section';
import { PipelineSection } from '@/components/landing-page/pipeline-section';
import { ArchitectureSection } from '@/components/landing-page/architecture-section';
import { FeaturesSection } from '@/components/landing-page/features-section';
import { TechStackSection } from '@/components/landing-page/tech-stack-section';
import { FooterSection } from '@/components/landing-page/footer-section';

export default function Home() {
  return (
    <main
      className="bg-[#0a0a0a] text-white antialiased overflow-x-hidden selection:bg-[#fce9c8]/30 selection:text-white cursor-none"
      style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
    >
      <NeuralCanvas />
      <CustomCursor />
      <NavSection />
      <HeroSection />
      <PipelineSection />
      <ArchitectureSection />
      <FeaturesSection />
      <TechStackSection />
      <FooterSection />
    </main>
  );
}
