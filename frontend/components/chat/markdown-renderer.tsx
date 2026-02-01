/**
 * Markdown renderer component (lazy-loaded)
 * Heavy dependencies: react-markdown, remark-gfm, rehype-highlight
 * This component is dynamically imported to reduce initial bundle size
 */

'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'

interface MarkdownRendererProps {
  content: string
}

/**
 * Renders markdown content with syntax highlighting
 * Used for AI message responses in chat
 */
export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          // Customize markdown rendering
          p: ({ children }) => (
            <p className="mb-2 last:mb-0">{children}</p>
          ),
          ul: ({ children }) => (
            <ul className="list-disc list-inside mb-2">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside mb-2">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="mb-1">{children}</li>
          ),
          code: ({ className, children, ...props }) => {
            // Determine if this is inline code or block code
            const hasLanguageClass = /language-(\w+)/.test(className || '')
            const hasNewlines = children?.toString().includes('\n')
            const isInlineCode = !hasLanguageClass && !hasNewlines
            
            if (isInlineCode) {
              return (
                <code
                  className="bg-muted px-1 py-0.5 rounded text-sm font-mono"
                  {...props}
                >
                  {children}
                </code>
              )
            }
            
            // Block code (inside <pre> with syntax highlighting from rehype-highlight)
            return (
              <code className={className} {...props}>
                {children}
              </code>
            )
          },
          pre: ({ children }) => (
            <pre className="bg-muted p-3 rounded-md overflow-x-auto mb-2">
              {children}
            </pre>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              className="text-primary hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              {children}
            </a>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-muted pl-4 italic mb-2">
              {children}
            </blockquote>
          ),
          h1: ({ children }) => (
            <h1 className="text-xl font-bold mb-2 mt-4">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-lg font-bold mb-2 mt-3">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-base font-bold mb-2 mt-2">{children}</h3>
          ),
          hr: () => (
            <hr className="my-4 border-muted" />
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto mb-2">
              <table className="min-w-full divide-y divide-muted">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider bg-muted">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2 text-sm border-t border-muted">
              {children}
            </td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
