export function Cup({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M7 3h10v6a5 5 0 0 1-10 0z" />
      <path d="M7 5H4a3 3 0 0 0 3 4.5M17 5h3a3 3 0 0 1-3 4.5M12 14v4M8 21h8M9 18h6" />
    </svg>
  );
}
