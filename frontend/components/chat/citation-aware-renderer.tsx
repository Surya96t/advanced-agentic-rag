/**
 * Citation-aware markdown renderer.
 *
 * Extends MarkdownRenderer to intercept inline [N] markers in the LLM
 * response and replace them with InlineCitation hover cards.  The mapping
 * from marker number ("1", "2", …) to source metadata is supplied via the
 * citationMap prop, which is populated from the citation_map SSE event.
 *
 * Implementation notes:
 * - A custom rehype plugin walks the hast text nodes to find /\[\d+\]/
 *   occurrences and wraps each one in a <cite data-marker="N"> element.
 * - ReactMarkdown's `components.cite` then renders these as InlineCitation
 *   hover cards using the pre-built ai-elements primitives.
 * - Plain [N] text with no matching map entry falls back to literal "[N]".
 */

'use client'

import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { CodeBlock, CodeBlockCopyButton, CodeBlockHeader, CodeBlockTitle } from '@/components/ai-elements/code-block'
import {
  InlineCitation,
  InlineCitationCard,
  InlineCitationCardBody,
  InlineCitationCardTrigger,
  InlineCitationCarousel,
  InlineCitationCarouselContent,
  InlineCitationCarouselHeader,
  InlineCitationCarouselIndex,
  InlineCitationCarouselItem,
  InlineCitationCarouselNext,
  InlineCitationCarouselPrev,
  InlineCitationSource,
} from '@/components/ai-elements/inline-citation'
import type { BundledLanguage } from 'shiki'
import { bundledLanguages } from 'shiki'
import type { CitationMarker } from '@/types/chat'

// ---------------------------------------------------------------------------
// Rehype plugin — transforms [N] text nodes → <cite data-marker="N"></cite>
// ---------------------------------------------------------------------------

/**
 * Minimal hast node types used by the rehype plugin.
 * These are compatible with the hast spec without requiring the hast package.
 */
interface HastText {
  type: 'text'
  value: string
}

interface HastElement {
  type: 'element'
  tagName: string
  properties: Record<string, string | number | boolean>
  children: HastNode[]
}

interface HastRoot {
  type: 'root'
  children: HastNode[]
}

type HastNode = HastText | HastElement | HastRoot | { type: string; children?: HastNode[] }

// ---------------------------------------------------------------------------
// Rehype plugin — transforms [N] text nodes → <cite data-marker="N"></cite>
// ---------------------------------------------------------------------------

/**
 * Rehype plugin that walks hast text nodes and splits any [N] patterns out
 * into <cite data-marker="N"> elements so ReactMarkdown can render them.
 *
 * No external dependencies required — we traverse the hast tree manually.
 */
function rehypeCitationRef() {
  const CITATION_RE = /(\[\d+\])/g

  function walk(node: HastNode, parent: HastNode | null, index: number): number {
    if (node.type === 'text') {
      // Do not rewrite text inside code/pre blocks — [1] is valid syntax there
      const parentTag = parent && 'tagName' in parent ? (parent as HastElement).tagName : ''
      if (parentTag === 'code' || parentTag === 'pre') return 0

      const text: string = (node as HastText).value
      const parts = text.split(CITATION_RE)

      // Nothing to replace
      if (parts.length <= 1) return 0

      const newNodes: HastNode[] = []
      for (const part of parts) {
        if (!part) continue
        const match = part.match(/^\[(\d+)\]$/)
        if (match) {
          newNodes.push({
            type: 'element',
            tagName: 'cite',
            properties: { 'data-marker': match[1] },
            children: [],
          } satisfies HastElement)
        } else {
          newNodes.push({ type: 'text', value: part } satisfies HastText)
        }
      }

      if (parent && 'children' in parent && Array.isArray(parent.children)) {
        parent.children.splice(index, 1, ...newNodes)
        // Return the number of EXTRA nodes inserted so the outer loop can skip them
        return newNodes.length - 1
      }
      return 0
    }

    if ('children' in node && Array.isArray(node.children)) {
      let i = 0
      while (i < node.children.length) {
        const extra = walk(node.children[i], node, i)
        i += extra + 1
      }
    }

    return 0
  }

  return (tree: HastRoot) => { walk(tree, null, 0) }
}

// ---------------------------------------------------------------------------
// Inline citation hover card
// ---------------------------------------------------------------------------

interface CitationBadgeProps {
  marker: string
  source: CitationMarker
}

function CitationBadge({ marker, source }: CitationBadgeProps) {
  return (
    <InlineCitation>
      <InlineCitationCard>
        <InlineCitationCardTrigger sources={[marker]} />
        <InlineCitationCardBody>
          <InlineCitationCarousel>
            <InlineCitationCarouselContent>
              <InlineCitationCarouselItem>
                <InlineCitationCarouselHeader>
                  <span className="flex-1 truncate text-xs font-medium text-foreground">
                    {source.document_title}
                  </span>
                  <InlineCitationCarouselIndex />
                  <div className="flex gap-1">
                    <InlineCitationCarouselPrev />
                    <InlineCitationCarouselNext />
                  </div>
                </InlineCitationCarouselHeader>
                <InlineCitationSource
                  title={source.document_title}
                  description={source.content ? source.content.slice(0, 180) : undefined}
                />
              </InlineCitationCarouselItem>
            </InlineCitationCarouselContent>
          </InlineCitationCarousel>
        </InlineCitationCardBody>
      </InlineCitationCard>
    </InlineCitation>
  )
}

// ---------------------------------------------------------------------------
// Main renderer
// ---------------------------------------------------------------------------

interface CitationAwareRendererProps {
  content: string
  citationMap: Record<string, CitationMarker>
}

/**
 * Renders markdown with inline [N] citation markers replaced by hover cards.
 */
export function CitationAwareRenderer({ content, citationMap }: CitationAwareRendererProps) {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none overflow-x-hidden">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeCitationRef]}
        components={{
          // Render <cite data-marker="N"> as an InlineCitation hover card
          cite: ({ 'data-marker': dataMarker, ...rest }: React.HTMLAttributes<HTMLElement> & { 'data-marker'?: string }) => {
            void rest
            const marker = String(dataMarker ?? '')
            if (!marker) return null
            const source = citationMap[marker]
            if (!source) {
              // No matching source — render as plain text
              return <span className="text-muted-foreground">[{marker}]</span>
            }
            return <CitationBadge marker={marker} source={source} />
          },

          // Preserve all other standard renderers from the base MarkdownRenderer
          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
          ul: ({ children }) => <ul className="list-disc list-inside mb-2">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal list-inside mb-2">{children}</ol>,
          li: ({ children }) => <li className="mb-1">{children}</li>,
          code: ({ className, children, ...rest }) => {
            const match = /language-(\w+)/.exec(className || '')
            const hasNewlines = String(children ?? '').includes('\n')
            const isInlineCode = !match && !hasNewlines

            if (isInlineCode) {
              return (
                <code className="bg-muted px-1 py-0.5 rounded text-sm font-mono" {...rest}>
                  {children}
                </code>
              )
            }

            const rawLang = match?.[1] ?? 'text'
            const language: BundledLanguage = (rawLang in bundledLanguages) ? rawLang as BundledLanguage : 'text'
            const codeString = String(children ?? '').replace(/\n$/, '')

            return (
              <CodeBlock
                code={codeString}
                language={language}
                showLineNumbers={false}
                className="my-2 overflow-x-auto"
              >
                <CodeBlockHeader>
                  <CodeBlockTitle>{language}</CodeBlockTitle>
                  <CodeBlockCopyButton />
                </CodeBlockHeader>
              </CodeBlock>
            )
          },
          pre: ({ children }) => <>{children}</>,
          a: ({ href, children }) => (
            <a href={href} className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-muted pl-4 italic mb-2">{children}</blockquote>
          ),
          h1: ({ children }) => <h1 className="text-xl font-bold mb-2 mt-4">{children}</h1>,
          h2: ({ children }) => <h2 className="text-lg font-bold mb-2 mt-3">{children}</h2>,
          h3: ({ children }) => <h3 className="text-base font-bold mb-2 mt-2">{children}</h3>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
