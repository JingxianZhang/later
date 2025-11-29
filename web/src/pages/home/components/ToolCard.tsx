
import { useEffect, useState, useRef } from 'react';
import type { Tool } from '../types';
import { setWatchlist, deleteLatestVersion } from '../../../api/client';

interface ToolCardProps {
  tool: Tool;
  onSelect: (tool: Tool) => void;
  onDelete?: (toolId: string) => void;
  index: number;
  unread?: boolean;
  layout?: 'stacked' | 'grid';
  perRowOverride?: number;
}

export default function ToolCard({ tool, onSelect, onDelete, index, unread, layout = 'stacked', perRowOverride }: ToolCardProps) {
  const [isWatchlisted, setIsWatchlisted] = useState(tool.isWatchlisted);
  const [hovered, setHovered] = useState(false);
  const [perRow, setPerRow] = useState<number>(4);
  const [menuOpen, setMenuOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const menuRootRef = useRef<HTMLDivElement | null>(null);

  // Simple user id for demo: persist in localStorage
  const getUserId = (): string | undefined => {
    try {
      const key = 'user_id';
      let val = localStorage.getItem(key);
      if (!val) {
        // naive uuid-ish
        val = 'u-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
        localStorage.setItem(key, val);
      }
      return val;
    } catch {
      return undefined;
    }
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

  const handleWatchlistToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    const next = !isWatchlisted;
    setIsWatchlisted(next);
    setWatchlist(tool.id, next).catch(() => {
      // revert on failure
      setIsWatchlisted(!next);
      alert('Failed to update watchlist');
    });
  };

  // Calculate staggered/scattered position and rotation with hover layering
  const getCardStyle = () => {
    if (layout === 'grid') return undefined as any;
    const cols = Math.max(1, perRowOverride ?? perRow);
    const row = Math.floor(index / cols);
    const col = index % cols;
    const rotations = [2, -1, 1.5, -2, 0.5, -1.5, 1, -0.5, 2];
    const rotation = rotations[index % rotations.length];
    // Pixel-based spacing for precise control
    const cardWidthPx = 280; // matches class
    const edgeOverlapPx = 5; // small edge overlap within a row
    const horizStepPx = cardWidthPx - edgeOverlapPx;
    // odd rows start at 25% of a card width (relative to first row card width)
    const rowShiftPx = row % 2 === 1 && perRow > 1 ? Math.floor(cardWidthPx * 0.25) : 0;
    const leftPx = rowShiftPx + col * horizStepPx;
    const cardHeightPx = 260; // approx height incl. margins (taller description)
    const topStep = Math.floor(cardHeightPx * 0.6); // 60% overlap between rows
    return {
      position: 'absolute' as const,
      left: `${leftPx}px`,
      top: `${row * topStep}px`,
      transform: `rotate(${rotation}deg)`,
      zIndex: hovered ? 999 : 100 + row * 10 + col,
    };
  };

  // statusConfig no longer needed since we removed the status dot/label

  // Close dropdown on outside click
  useEffect(() => {
    const handleDocClick = (e: MouseEvent) => {
      if (!menuOpen) return;
      const root = menuRootRef.current;
      const container = containerRef.current;
      const target = e.target as Node | null;
      if (root && target && root.contains(target)) return;
      if (container && target && container.contains(target)) {
        // Inside the card but outside the menu; still close
        setMenuOpen(false);
        return;
      }
      setMenuOpen(false);
    };
    document.addEventListener('click', handleDocClick);
    return () => document.removeEventListener('click', handleDocClick);
  }, [menuOpen]);

  const handleCardClick = () => {
    if (isDeletedOrBusy()) return;
    onSelect(tool);
  };

  const isDeletedOrBusy = () => isDeleting;

  const onDeleteClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setMenuOpen(false);
    if (!confirm('Delete this tool summary version and its related data?')) return;
    try {
      setIsDeleting(true);
      const userId = getUserId();
      await deleteLatestVersion(tool.id, userId ? { userId } : undefined);
      onDelete?.(tool.id);
    } catch (err) {
      alert('Failed to delete. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div
      ref={containerRef}
      style={getCardStyle()}
      className={`${layout === 'grid' ? 'w-full' : 'w-[280px]'} group cursor-pointer`}
      onClick={handleCardClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div className="bg-white rounded-xl p-5 shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105 hover:rotate-0 border border-gray-200 relative">
        {/* Header */}
        <div className="flex items-start gap-3 mb-3 relative z-20">
          <div className="w-12 h-12 bg-gradient-to-br from-blue-100 to-purple-100 rounded-xl flex items-center justify-center flex-shrink-0 overflow-hidden">
            {tool.icon.startsWith('http') ? (
              <img src={tool.icon} alt="" className="w-8 h-8 object-contain" />
            ) : (
              <i className={`${tool.icon} text-2xl text-blue-600`}></i>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-base font-semibold text-gray-800 truncate">{tool.name}</h3>
              <button
                onClick={handleWatchlistToggle}
                className="flex-shrink-0 w-7 h-7 flex items-center justify-center hover:bg-gray-100 rounded-lg transition-colors cursor-pointer"
              >
                <i className={`${isWatchlisted ? 'ri-star-fill text-yellow-500' : 'ri-star-line text-gray-400'} text-base`}></i>
              </button>
            </div>
          </div>
          {unread && (
            <span className="absolute -left-1 -top-1 w-3 h-3 bg-red-500 rounded-full ring-2 ring-white" aria-hidden="true"></span>
          )}
        </div>

        {/* Description */}
        <p className="text-sm text-gray-600 line-clamp-4 mb-3">{tool.description}</p>

        {/* Categories */}
        <div className="flex flex-wrap gap-1.5 mb-3">
          {tool.categories.slice(0, 3).map(category => (
            <span
              key={category}
              className="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs rounded-md"
            >
              #{category}
            </span>
          ))}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between text-xs text-gray-500 pt-3 border-t border-gray-100 relative z-10">
          <span>
            Updated {(() => {
              try {
                const raw = tool.onePager?.lastUpdated;
                if (!raw) return '';
                const d = new Date(raw);
                const now = new Date();
                const isSameDay = d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
                const timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                return isSameDay
                  ? `Today ${timeStr}`
                  : d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
              } catch {
                return tool.onePager?.lastUpdated ?? '';
              }
            })()}
          </span>
        </div>

        {/* Three-dot menu (bottom-right) */}
        <div className="absolute bottom-2 right-2 z-30">
          <button
            onClick={(e) => { e.stopPropagation(); setMenuOpen(o => !o); }}
            className="w-8 h-8 flex items-center justify-center rounded-md hover:bg-gray-100 transition-colors cursor-pointer"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            disabled={isDeleting}
            title="More actions"
          >
            <i className="ri-more-2-fill text-lg text-gray-500"></i>
          </button>
          {menuOpen && (
            <div
              ref={menuRootRef}
              className="absolute bottom-10 right-0 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[140px]"
              role="menu"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 cursor-pointer disabled:opacity-50"
                onClick={onDeleteClick}
                disabled={isDeleting}
                role="menuitem"
              >
                {isDeleting ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
