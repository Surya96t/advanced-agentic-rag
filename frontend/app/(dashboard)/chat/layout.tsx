/**
 * Chat-specific layout
 * Provides full-screen chat experience with fixed input at bottom
 * Uses absolute positioning to escape parent's padding/gap constraints
 */

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="absolute inset-0 flex flex-col">
      {children}
    </div>
  )
}
