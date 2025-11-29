
import ToolCard from './ToolCard';
import type { Tool } from '../types';
import { mockTools } from '../../../mocks/tools';
import { useState, useEffect } from 'react';

interface KnowledgeGalleryProps {
  onToolSelect: (tool: Tool) => void;
  tools?: Tool[];
}

export default function KnowledgeGallery({ onToolSelect, tools }: KnowledgeGalleryProps) {
  const [groupMode, setGroupMode] = useState<'category' | 'tag'>('category');
  const [perRow, setPerRow] = useState<number>(4);
  const [data, setData] = useState<Tool[]>(tools && tools.length ? tools : mockTools);
  useEffect(() => {
    if (tools && tools.length) {
      setData(tools);
    } else {
      setData(mockTools);
    }
  }, [tools]);
  const cardHeightPx = 260;
  const rowStep = Math.floor(cardHeightPx * 0.6);
  const getContainerMinHeight = (count: number) => {
    const rows = Math.max(1, Math.ceil(count / perRow));
    return (rows - 1) * rowStep + cardHeightPx;
  };
  const getMinHeightFor = (count: number, cols: number) => {
    const rows = Math.max(1, Math.ceil(count / Math.max(1, cols)));
    return (rows - 1) * rowStep + cardHeightPx;
  };
  useEffect(() => {
    const calc = () => {
      const w = window.innerWidth;
      if (w >= 1280) return 4;
      if (w >= 1024) return 3;
      if (w >= 640) return 2;
      return 1;
    };
    const update = () => setPerRow(calc());
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);
  const dataset = data;
  // Organize tools by folders
  // "New" = unread since last open; relies on lastOpened in localStorage
  const newTools = dataset.filter(tool => isUnread(tool));
  const watchlistTools = dataset.filter(tool => tool.isWatchlisted);
  const watchlistSorted = [...watchlistTools].sort((a, b) => {
    const sa = a.status === 'updated' ? 1 : 0;
    const sb = b.status === 'updated' ? 1 : 0;
    return sb - sa;
  });
  const perRowHalf = Math.max(1, Math.floor(perRow / 2));
  // const allCategories = useMemo(() => Array.from(new Set(dataset.flatMap(tool => tool.categories))), [dataset]);
  // For now, show a single "All Tools" folder to avoid duplicate appearances with tag-like data
  const folders = [{ name: 'All Tools', tools: dataset }];

  const markOpened = (tool: Tool) => {
    try {
      localStorage.setItem(`lastOpened:${tool.id}`, new Date().toISOString());
    } catch {}
    onToolSelect(tool);
  };
  const handleDeleted = (toolId: string) => {
    setData(prev => prev.filter(t => t.id !== toolId));
  };

  function isUnread(tool: Tool): boolean {
    try {
      const lastOpened = localStorage.getItem(`lastOpened:${tool.id}`);
      const updated = tool.onePager?.lastUpdated ? Date.parse(tool.onePager.lastUpdated) : 0;
      if (!lastOpened) return true;
      const opened = Date.parse(lastOpened);
      return updated > opened;
    } catch {
      return false;
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Knowledge Gallery</h2>

      {/* First row: New + Watchlist (conditionally rendered) */}
      {(newTools.length > 0 || watchlistSorted.length > 0) && (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {newTools.length > 0 && (
        <div id="section-new" className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="w-full px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-blue-100">
                <i className="ri-sparkling-line text-xl text-blue-600"></i>
              </div>
              <div className="text-left">
                <h3 className="font-semibold text-gray-800">New Discoveries</h3>
                <p className="text-sm text-gray-500">{newTools.length} {newTools.length === 1 ? 'tool' : 'tools'}</p>
              </div>
            </div>
          </div>
          <div className="px-6 pb-6 pt-2">
            <div className="relative" style={{ minHeight: `${getMinHeightFor(newTools.length, perRowHalf)}px` }}>
              {newTools.map((tool, index) => (
                <ToolCard
                  key={tool.id}
                  tool={tool}
                  onSelect={markOpened}
                  onDelete={handleDeleted}
                  index={index}
                  unread={true}
                  perRowOverride={perRowHalf}
                />
              ))}
            </div>
          </div>
        </div>
        )}

        {watchlistSorted.length > 0 && (
        <div id="section-watchlist" className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="w-full px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-yellow-100">
                <i className="ri-star-line text-xl text-yellow-500"></i>
              </div>
              <div className="text-left">
                <h3 className="font-semibold text-gray-800">Watchlist</h3>
                <p className="text-sm text-gray-500">{watchlistSorted.length} {watchlistSorted.length === 1 ? 'tool' : 'tools'}</p>
              </div>
            </div>
          </div>
          <div className="px-6 pb-6 pt-2">
            <div className="relative" style={{ minHeight: `${getMinHeightFor(watchlistSorted.length, perRowHalf)}px` }}>
              {watchlistSorted.map((tool, index) => (
                <ToolCard
                  key={tool.id}
                  tool={tool}
                  onSelect={markOpened}
                  onDelete={handleDeleted}
                  index={index}
                  unread={isUnread(tool)}
                  perRowOverride={perRowHalf}
                />
              ))}
            </div>
          </div>
        </div>
        )}
      </div>
      )}

      {/* All heading and grouping toggle */}
      <div className="flex items-center justify-between mt-10 mb-2">
        <h3 className="text-lg font-semibold text-gray-800">All</h3>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Group:</span>
          <button
            onClick={() => setGroupMode('category')}
            className={`px-3 py-1 rounded-full text-sm ${groupMode === 'category' ? 'bg-slate-200 text-slate-800' : 'bg-gray-100 text-gray-700'}`}
          >
            by category
          </button>
          <button
            onClick={() => setGroupMode('tag')}
            className={`px-3 py-1 rounded-full text-sm ${groupMode === 'tag' ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-700'}`}
            disabled
            title="Tags coming soon"
          >
            by tag
          </button>
        </div>
      </div>

      {/* Categories/tags two per row */}
      {folders.length <= 1 ? (
        <div className="mt-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="w-full px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-gradient-to-br from-sky-200 to-rose-100">
                  <i className="ri-folder-line text-xl text-sky-700"></i>
                </div>
                <div className="text-left">
                  <h3 className="font-semibold text-gray-800" id="section-all-tools">{folders[0]?.name ?? 'All Tools'}</h3>
                  <p className="text-sm text-gray-500">{(folders[0]?.tools ?? mockTools).length} tools</p>
                </div>
              </div>
            </div>
            <div className="px-6 pb-6 pt-2">
              <div className="relative" style={{ minHeight: `${getContainerMinHeight((folders[0]?.tools ?? mockTools).length)}px` }}>
                {(folders[0]?.tools ?? dataset).map((tool, index) => (
                  <ToolCard
                    key={tool.id}
                    tool={tool}
                    onSelect={markOpened}
                    onDelete={handleDeleted}
                    index={index}
                    unread={isUnread(tool)}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          {folders.map((folder, idx) => (
            <div key={`${folder.name}-${idx}`} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="w-full px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-gray-100">
                    <i className="ri-folder-line text-xl text-gray-600"></i>
                  </div>
                  <div className="text-left">
                    <h3 className="font-semibold text-gray-800">{folder.name}</h3>
                    <p className="text-sm text-gray-500">{folder.tools.length} {folder.tools.length === 1 ? 'tool' : 'tools'}</p>
                  </div>
                </div>
              </div>
              <div className="px-6 pb-6 pt-2">
                <div className="relative min-h-[300px]">
                  {folder.tools.map((tool, index) => (
                    <ToolCard
                      key={tool.id}
                      tool={tool}
                      onSelect={markOpened}
                      index={index}
                    />
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {newTools.length === 0 && watchlistSorted.length === 0 && folders.length === 0 && (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <i className="ri-inbox-line text-3xl text-gray-400"></i>
          </div>
          <p className="text-gray-500">No tools found. Start scouting to build your knowledge gallery!</p>
        </div>
      )}
    </div>
  );
}
