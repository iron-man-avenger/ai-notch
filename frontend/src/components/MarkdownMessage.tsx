import React from 'react';
import ReactMarkdown from 'react-markdown';

interface MarkdownMessageProps {
  content: string;
}

export const MarkdownMessage: React.FC<MarkdownMessageProps> = ({ content }) => {
  return (
    <div className="markdown-content text-[12px] leading-relaxed select-text">
      <ReactMarkdown
        components={{
          h1: ({ children }) => (
            <h1 className="text-sm font-bold text-white mt-2 mb-1 tracking-tight">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-xs font-bold text-white mt-2 mb-1 tracking-tight">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-xs font-bold text-white mt-1.5 mb-1 tracking-tight">
              {children}
            </h3>
          ),
          p: ({ children }) => (
            <p className="mb-1.5 last:mb-0 text-[#c5cad3] leading-relaxed">
              {children}
            </p>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-white">
              {children}
            </strong>
          ),
          em: ({ children }) => (
            <em className="italic text-neutral-300">
              {children}
            </em>
          ),
          ul: ({ children }) => (
            <ul className="list-disc pl-4 space-y-1 mb-1.5 text-[#c5cad3]">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal pl-4 space-y-1 mb-1.5 text-[#c5cad3]">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="leading-relaxed pl-0.5">
              {children}
            </li>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-cyan-400/60 pl-2.5 py-0.5 my-1.5 text-neutral-300 text-[11px] italic bg-white/[0.03] rounded-r">
              {children}
            </blockquote>
          ),
          code: ({ className, children, ...props }) => {
            const isBlock = Boolean(className);
            if (isBlock) {
              return (
                <pre className="p-2.5 rounded-xl bg-black/60 border border-white/10 text-emerald-300 font-mono text-[11px] overflow-x-auto my-2">
                  <code {...props}>{children}</code>
                </pre>
              );
            }
            return (
              <code
                className="px-1.5 py-0.5 rounded-md bg-white/10 text-cyan-300 font-mono text-[11px]"
                {...props}
              >
                {children}
              </code>
            );
          },
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-400 hover:text-cyan-300 underline font-medium transition-colors"
            >
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownMessage;
