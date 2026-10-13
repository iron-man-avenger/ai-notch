import React, { useState, useEffect } from 'react';
import { Newspaper, ExternalLink, RefreshCw, X, Tag } from 'lucide-react';
import type { NewsArticle } from '../types';
import { api } from '../api';

interface NewsDrawerProps {
  onClose: () => void;
  activeApp: string;
}

export const NewsDrawer: React.FC<NewsDrawerProps> = ({ onClose, activeApp }) => {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadNews();
  }, []);

  const loadNews = async () => {
    setLoading(true);
    try {
      const res = await api.getNews();
      setArticles(res.articles || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-xs z-50 flex justify-end">
      <div className="clean-white-panel w-full max-w-md h-full p-6 flex flex-col border-l border-neutral-200 shadow-2xl animate-in slide-in-from-right duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-neutral-200">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-black text-white">
              <Newspaper className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-black flex items-center gap-2">
                Tech Radar & News
              </h2>
              <p className="text-xs text-neutral-500">
                Curated articles matching your work in <span className="text-black font-semibold">{activeApp}</span>.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={loadNews}
              disabled={loading}
              className="text-neutral-400 hover:text-black p-2 rounded-xl hover:bg-neutral-100 transition cursor-pointer"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="text-neutral-400 hover:text-black p-2 rounded-xl hover:bg-neutral-100 transition cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Articles List */}
        <div className="flex-1 overflow-y-auto space-y-3 py-4 pr-1">
          {articles.length === 0 && !loading && (
            <div className="text-center py-12 text-neutral-400 text-xs">
              No articles found right now. Keep working and check back soon!
            </div>
          )}

          {articles.map((item, idx) => (
            <div
              key={idx}
              className="p-4 rounded-2xl bg-neutral-50 border border-neutral-200 hover:border-neutral-300 transition-all space-y-2 group"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-neutral-200 text-neutral-800 flex items-center gap-1">
                  <Tag className="w-2.5 h-2.5" /> {item.tag || item.source}
                </span>
                <span className="text-[10px] text-neutral-500 font-mono">
                  {item.published_at}
                </span>
              </div>

              <h4 className="text-xs font-semibold text-black leading-snug">
                {item.title}
              </h4>

              {item.description && (
                <p className="text-[11px] text-neutral-600 line-clamp-2">
                  {item.description}
                </p>
              )}

              <div className="pt-2 flex items-center justify-between border-t border-neutral-200 text-xs">
                <span className="text-[10px] text-neutral-500 font-medium">{item.source}</span>
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 text-[11px] font-semibold text-black hover:underline transition"
                >
                  <span>Read Article</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
};

export default NewsDrawer;
