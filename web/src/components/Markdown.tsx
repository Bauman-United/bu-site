import Link from "next/link";
import type { ComponentProps } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import s from "./Markdown.module.css";

const EXTERNAL = /^(https?:)?\/\//i;

function MdLink({ href, children, node: _node, ...rest }: ComponentProps<"a"> & { node?: unknown }) {
  if (href && EXTERNAL.test(href)) {
    return <a {...rest} href={href} target="_blank" rel="noopener">{children}</a>;
  }
  if (href?.startsWith("/")) {
    return <Link {...rest} href={href}>{children}</Link>;
  }
  return <a {...rest} href={href}>{children}</a>;
}

const COMPONENTS: Components = { a: MdLink };

/**
 * Серверный рендер Markdown. Сырой HTML не исполняется (без rehype-raw он выводится как текст / отбрасывается),
 * опасные URL чистит defaultUrlTransform. Внешние ссылки — в новой вкладке с rel="noopener".
 * Цвета наследуются — компонент работает и на чёрном, и на белом фоне.
 */
export function Markdown({ source, className }: { source: string; className?: string }) {
  return (
    <div className={`${s.md} ${className ?? ""}`}>
      <ReactMarkdown skipHtml components={COMPONENTS}>{source}</ReactMarkdown>
    </div>
  );
}
