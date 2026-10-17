import type { ReactNode } from 'react';
import { safeHref } from '../lib/safe-href';

export function SourceLink({ href, children, className }: {
  href: string | null | undefined; children: ReactNode; className?: string;
}) {
  const safe = safeHref(href);
  return safe ? <a href={safe} className={className} rel="noreferrer">{children}</a> :
    <span className={className}>{children}</span>;
}
