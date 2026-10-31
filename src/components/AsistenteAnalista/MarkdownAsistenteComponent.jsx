import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const ALLOWED_ELEMENTS = [
  'a', 'blockquote', 'br', 'code', 'del', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'hr', 'input', 'li', 'ol', 'p', 'pre', 'strong', 'table', 'tbody', 'td', 'th', 'thead', 'tr', 'ul',
];

function pageOrigin() {
  return globalThis.location?.origin || 'http://localhost';
}

export function safeMarkdownUrl(value) {
  const url = String(value || '').trim();
  if (!url) return '';
  if (url.startsWith('#')) return url;
  try {
    const parsed = new URL(url, `${pageOrigin()}/`);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? url : '';
  } catch {
    return '';
  }
}

function MarkdownLink({ href, children }) {
  const safeHref = safeMarkdownUrl(href);
  if (!safeHref) return <span>{children}</span>;
  let external = false;
  try { external = new URL(safeHref, `${pageOrigin()}/`).origin !== pageOrigin(); } catch { /* url was validated */ }
  return (
    <a href={safeHref} rel="noopener noreferrer" {...(external ? { target: '_blank' } : {})}>
      {children}
    </a>
  );
}

function DisabledTaskCheckbox({ checked }) {
  return <input type="checkbox" checked={Boolean(checked)} disabled readOnly aria-label="Tarea" />;
}

export function MarkdownAsistenteComponent({ content = '' }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      skipHtml
      allowedElements={ALLOWED_ELEMENTS}
      urlTransform={safeMarkdownUrl}
      components={{
        a: MarkdownLink,
        img: () => null,
        input: DisabledTaskCheckbox,
      }}
    >
      {String(content)}
    </ReactMarkdown>
  );
}
