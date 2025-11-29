import { useState, useEffect } from 'react';
import DropZone from './components/DropZone';
import KnowledgeGallery from './components/KnowledgeGallery';
import DetailView from './components/DetailView';
import AIChatButton from './components/AIChatButton';
import AIChatPanel from './components/AIChatPanel';
import { Tool } from './types';
import { getTool, mapTool, listTools, mapListItem } from '../../api/client';
import AuthBar from './components/AuthBar';

export default function Home() {
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [tools, setTools] = useState<Tool[]>([]);

  // Load initial tools list
  useEffect(() => {
    (async () => {
      try {
        const items = await listTools();
        const mapped = items.map(mapListItem);
        setTools(mapped);
      } catch {
        // ignore for now
      }
    })();
  }, []);

  // If URL has ?tool=<id>, open that tool
  useEffect(() => {
    (async () => {
      try {
        const params = new URLSearchParams(window.location.search);
        const toolId = params.get('tool');
        if (toolId) {
          const info = await getTool(toolId);
          setSelectedTool(mapTool(info));
        }
      } catch {
        // ignore
      }
    })();
  }, []);
  const handleScouted = async (toolId: string) => {
    try {
      const info = await getTool(toolId);
      const tool = mapTool(info);
      setTools(prev => {
        const next = prev.filter(t => t.id !== tool.id).concat(tool);
        return next;
      });
      setSelectedTool(tool);
    } catch {
      // ignore
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50/30">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-100 sticky top-0 z-[1000]">
        <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
          <h1 className="text-4xl font-semibold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-sky-400 via-sky-600 to-rose-200" style={{ fontFamily: '"Google Sans", sans-serif' }}>
            Later.
          </h1>
          <nav className="flex items-center gap-6">
            <AuthBar />
            <button
              onClick={() => {
                const el = document.getElementById('section-all-tools');
                if (el) {
                  const rect = el.getBoundingClientRect();
                  const y = rect.top + window.scrollY - 80; // adjust for sticky header
                  window.scrollTo({ top: y, behavior: 'smooth' });
                }
              }}
              className="text-gray-600 hover:text-gray-800 transition-colors cursor-pointer font-light whitespace-nowrap"
            >
              All Tools
            </button>
            <button
              onClick={() => {
                const el = document.getElementById('section-watchlist');
                if (el) {
                  const rect = el.getBoundingClientRect();
                  const y = rect.top + window.scrollY - 80; // adjust for sticky header
                  window.scrollTo({ top: y, behavior: 'smooth' });
                }
              }}
              className="text-gray-600 hover:text-gray-800 transition-colors cursor-pointer font-light whitespace-nowrap"
            >
              Watchlist
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-12">
        <DropZone onScouted={handleScouted} />
        <KnowledgeGallery
          onToolSelect={async (t) => {
            try {
              const info = await getTool(t.id);
              setSelectedTool(mapTool(info));
            } catch {
              setSelectedTool(t);
            }
          }}
          tools={tools}
        />
      </main>

      {/* Detail View Modal */}
      {selectedTool && (
        <DetailView
          tool={selectedTool}
          onClose={() => setSelectedTool(null)}
          allTools={tools}
          onToolChange={setSelectedTool}
          isChatOpen={isChatOpen}
        />
      )}

      {/* AI Chat Button */}
      <AIChatButton 
        onToggle={() => setIsChatOpen(!isChatOpen)} 
        isOpen={isChatOpen}
      />

      {/* AI Chat Panel */}
      <AIChatPanel 
        isOpen={isChatOpen} 
        selectedTool={selectedTool}
        onClose={() => setIsChatOpen(false)}
      />
    </div>
  );
}
