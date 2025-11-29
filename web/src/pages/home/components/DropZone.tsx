
import { useState, useRef } from 'react';
import { ingest, ingestImage } from '../../../api/client';
const API_BASE = (localStorage.getItem('API_URL') || 'http://127.0.0.1:8000') + '/v1';

type DropZoneState = 'idle' | 'scouting' | 'captured';

export default function DropZone({ onScouted }: { onScouted?: (toolId: string) => void }) {
  const [state, setState] = useState<DropZoneState>('idle');
  const [progress, setProgress] = useState(0);
  const [inputValue, setInputValue] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [stepText, setStepText] = useState<string>('Preparing…');
  const [isDragging, setIsDragging] = useState<boolean>(false);

  const handleSubmit = async () => {
    if (!inputValue.trim()) return;
    setState('scouting');
    setProgress(10);
    setStepText('Resolving official site…');
    const payload = inputValue.startsWith('http') ? { url: inputValue } : { name: inputValue };
    // Prefer SSE for real-time progress; fallback to POST on error.
    try {
      const params = new URLSearchParams();
      if (payload.url) params.set('url', payload.url);
      if (payload.name) params.set('name', payload.name);
      // Do not force by default; backend will skip if a fresh version exists
      const userId = localStorage.getItem('USER_ID');
      if (userId) params.set('user_id', userId);
      const es = new EventSource(`${API_BASE}/ingest/stream?${params.toString()}`);
      let toolId: string | null = null;
      es.addEventListener('progress', (evt: MessageEvent) => {
        try {
          const data = JSON.parse(evt.data);
          const node = data.node as string;
          const status = data.status as string;
          if (status === 'start') {
            if (node === 'resolve_tool') { setProgress(15); setStepText('Resolving official site…'); }
            if (node === 'ingest') { setProgress(30); setStepText('Fetching & chunking…'); }
            if (node === 'augment_sources') { setProgress(50); setStepText('Augmenting sources…'); }
            if (node === 'research') { setProgress(70); setStepText('Synthesizing summary…'); }
            if (node === 'juror') { setProgress(82); setStepText('Verifying claims…'); }
            if (node === 'dbwrite') { setProgress(90); setStepText('Saving to knowledge base…'); }
          } else if (status === 'finish') {
            if (data.state?.tool_id) toolId = data.state.tool_id;
          }
        } catch {}
      });
      es.addEventListener('done', (evt: MessageEvent) => {
        try {
          const data = JSON.parse(evt.data);
          toolId = toolId || data.tool_id;
        } catch {}
        setState('captured');
        setProgress(100);
        if (toolId) onScouted?.(toolId);
        es.close();
        setTimeout(() => {
          setState('idle');
          setInputValue('');
          setProgress(0);
          setStepText('Preparing…');
        }, 800);
      });
      es.addEventListener('error', () => {
        es.close();
      });
      // Safety timeout fallback
      setTimeout(async () => {
        if (state === 'scouting') {
          try {
            const res = await ingest(payload);
            setProgress(95);
            setState('captured');
            setProgress(100);
            onScouted?.(res.tool_id);
            setTimeout(() => {
              setState('idle');
              setInputValue('');
              setProgress(0);
              setStepText('Preparing…');
            }, 800);
          } catch {
            setState('idle');
            setProgress(0);
            setStepText('Preparing…');
            alert('Ingest failed');
          }
        }
      }, 20000);
    } catch {
      // Hard fallback
      try {
        const res = await ingest(payload);
        setProgress(95);
        setState('captured');
        setProgress(100);
        onScouted?.(res.tool_id);
        setTimeout(() => {
          setState('idle');
          setInputValue('');
          setProgress(0);
          setStepText('Preparing…');
        }, 800);
      } catch {
        setState('idle');
        setProgress(0);
        setStepText('Preparing…');
        alert('Ingest failed');
      }
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file && file.type.startsWith('image/')) {
        (async () => {
          try {
            setState('scouting');
            setProgress(20);
            setStepText('Analyzing screenshot…');
            const res = await ingestImage(file);
            setProgress(100);
            setState('captured');
            onScouted?.(res.tool_id);
          } catch {
            setState('idle');
            setProgress(0);
            setStepText('Preparing…');
            alert('Image ingest failed');
          } finally {
            setTimeout(() => {
              setState('idle');
              setProgress(0);
              setStepText('Preparing…');
            }, 800);
          }
        })();
      }
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (state === 'idle' && !isDragging) setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    if (isDragging) setIsDragging(false);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file && file.type.startsWith('image/')) {
        (async () => {
          try {
            setState('scouting');
            setProgress(20);
            setStepText('Analyzing screenshot…');
            const res = await ingestImage(file);
            setProgress(100);
            setState('captured');
            onScouted?.(res.tool_id);
          } catch {
            setState('idle');
            setProgress(0);
            setStepText('Preparing…');
            alert('Image ingest failed');
          } finally {
            setTimeout(() => {
              setState('idle');
              setProgress(0);
              setStepText('Preparing…');
            }, 800);
          }
        })();
      }
    }
  };

  return (
    <div className="mb-16">
      <div
        className={`relative border rounded-3xl p-10 transition-all duration-300 ${
          state === 'idle'
            ? (isDragging ? 'border-blue-600 bg-blue-100/70 shadow-md ring-2 ring-blue-300' : 'border-gray-200 bg-white/80 hover:border-blue-300 hover:shadow-sm')
            : state === 'scouting'
            ? 'border-blue-300 bg-blue-50/30 shadow-sm'
            : 'border-green-300 bg-green-50/30 shadow-sm'
        }`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <style>
          {`
            @keyframes orbit {
              0% { transform: translate(0, 0); }
              25% { transform: translate(4px, -2px); }
              50% { transform: translate(0, -4px); }
              75% { transform: translate(-4px, -2px); }
              100% { transform: translate(0, 0); }
            }
          `}
        </style>
        <div className="flex flex-col items-center gap-6">
          {/* Icon */}
          <div className={`w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300 ${
            state === 'idle'
              ? 'bg-gray-50'
              : state === 'scouting'
              ? 'bg-blue-50 animate-pulse'
              : 'bg-green-50'
          }`}>
            {state === 'idle' && (
              <i className="ri-upload-cloud-line text-3xl text-gray-400"></i>
            )}
            {state === 'scouting' && (
              <i className="ri-search-line text-3xl text-blue-500" style={{ animation: 'orbit 1s linear infinite' }}></i>
            )}
            {state === 'captured' && (
              <i className="ri-check-line text-3xl text-green-500"></i>
            )}
          </div>

          {/* Text */}
          <div className="text-center">
            {state === 'idle' && (
              <>
                <p className="text-xl font-normal text-gray-700 mb-2">
                  {isDragging ? 'Drop your screenshot here' : 'Paste a link, drag a screenshot, or type a tool name'}
                </p>
              </>
            )}
            {state === 'scouting' && (
              <>
                <h3 className="text-xl font-normal text-blue-600 mb-2">
                  Scouting...
                </h3>
                <p className="text-gray-600 text-base font-light">
                  Analyzing and extracting knowledge
                </p>
              </>
            )}
            {state === 'captured' && (
              <>
                <h3 className="text-xl font-normal text-green-600 mb-2">
                  Knowledge Captured!
                </h3>
                <p className="text-gray-600 text-base font-light">
                  Successfully added to your gallery
                </p>
              </>
            )}
          </div>

          {/* Input Area */}
          {state === 'idle' && (
            <div className="w-full max-w-2xl">
              <div className="flex gap-3">
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                  placeholder="https://example.com or tool name..."
                  className="flex-1 px-5 py-3.5 bg-white border border-gray-200 rounded-full text-gray-800 placeholder-gray-400 focus:outline-none focus:border-blue-300 focus:ring-4 focus:ring-blue-50 transition-all text-base font-light"
                />
                <button
                  onClick={handleSubmit}
                  className="px-8 py-3.5 text-white rounded-full font-normal whitespace-nowrap cursor-pointer shadow-sm transition-colors bg-gradient-to-br from-sky-400 to-rose-200 hover:from-sky-500 hover:to-rose-300"
                >
                  Scout
                </button>
              </div>
              
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>
          )}

          {/* Progress Bar */}
          {state === 'scouting' && (
            <div className="w-full max-w-md">
              <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-400 to-blue-500 transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="mt-3 text-sm text-gray-600 text-center font-light">
                {stepText}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
