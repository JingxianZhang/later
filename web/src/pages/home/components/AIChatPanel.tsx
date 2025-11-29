import { useState, useRef, useEffect } from 'react';
import type { ChangeEvent, KeyboardEvent } from 'react';
import type { Tool } from '../types';
import { chat } from '../../../api/client';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  citations?: { source_url: string; snippet: string }[];
}

interface AIChatPanelProps {
  isOpen: boolean;
  selectedTool?: Tool | null;
  onClose: () => void;
}

export default function AIChatPanel({ isOpen, selectedTool, onClose }: AIChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: selectedTool 
        ? `Hi! I can help you learn more about ${selectedTool.name}. What would you like to know?`
        : "Hi! I'm your AI assistant. Ask me anything about the tools in your gallery, or about a specific tool.",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (selectedTool) {
      setMessages([{
        id: Date.now().toString(),
        role: 'assistant',
        content: `Hi! I can help you learn more about ${selectedTool.name}. What would you like to know?`,
        timestamp: new Date(),
      }]);
    }
  }, [selectedTool]);

  const detectCrossToolIntent = (text: string): boolean => {
    const pattern = /(other tools?|alternatives?|compare|vs\b|versus\b)/i;
    return pattern.test(text);
  };

  const handleSend = async () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev: Message[]) => [...prev, userMessage]);
    setInputValue('');

    try {
      const isCrossTool = detectCrossToolIntent(userMessage.content);
      const scope = selectedTool && !isCrossTool ? 'tool' : 'global';
      const preferOnePager = !!selectedTool;
      const res = await chat(selectedTool?.id, userMessage.content, { scope, preferOnePager });
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: res.answer,
        citations: res.citations,
        timestamp: new Date(),
      };
      setMessages((prev: Message[]) => [...prev, aiMessage]);
    } catch {
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "Sorry, I couldn't fetch an answer right now.",
        timestamp: new Date(),
      };
      setMessages((prev: Message[]) => [...prev, aiMessage]);
    }
  };

  const toggleRecording = () => {
    setIsRecording(!isRecording);
    if (!isRecording) {
      setTimeout(() => {
        setIsRecording(false);
        const voiceMessage: Message = {
          id: Date.now().toString(),
          role: 'user',
          content: '[Voice message transcribed]',
          timestamp: new Date(),
        };
        setMessages((prev: Message[]) => [...prev, voiceMessage]);
      }, 2000);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-2xl z-[3001] flex flex-col border-l border-gray-200 animate-slide-in">
      {/* Header */}
      <div className="px-6 py-5 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-purple-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
              <i className="ri-sparkling-2-fill text-xl text-white"></i>
            </div>
            <div>
              <h3 className="text-lg font-normal text-gray-800">AI Assistant</h3>
              <p className="text-xs text-gray-500 font-light">
                {selectedTool ? `About ${selectedTool.name}` : 'Ask about any tool'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-200 transition-colors cursor-pointer"
          >
            <i className="ri-close-line text-xl text-gray-600"></i>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((message: Message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              <p className="text-sm font-light leading-relaxed">{message.content}</p>
              {message.role === 'assistant' && message.citations && message.citations.length > 0 && (
                <div className="mt-2 text-xs">
                  <span className="mr-1 text-gray-500">Sources:</span>
                  {message.citations.slice(0, 8).map((c, i) => {
                    let prettyTitle = 'Source';
                    const urlForHover = c.source_url;
                    try {
                      const u = new URL(c.source_url);
                      const host = (u.hostname.split('.').slice(-2).join('.')) || u.hostname;
                      const segs = u.pathname.split('/').filter(Boolean);
                      const last = segs[segs.length - 1] || '';
                      const decoded = decodeURIComponent(last || '').replace(/[-_]+/g, ' ').trim();
                      const base = decoded || host;
                      const cap = base.split(' ').map(s => (s ? s[0].toUpperCase() + s.slice(1) : s)).join(' ');
                      prettyTitle = (cap.toLowerCase() === 'index' || cap.trim() === '') ? host : cap;
                    } catch {
                      // keep as-is
                    }
                    const label = `[${i + 1}]`;
                    const hover = `${prettyTitle}\n${urlForHover}`;
                    return (
                      <a
                        key={`${message.id}-src-${i}`}
                        href={c.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        title={hover}
                        className="inline-block mr-2 underline decoration-dotted hover:text-blue-600"
                      >
                        {label}
                      </a>
                    );
                  })}
                </div>
              )}
              <span className={`text-xs mt-1 block ${
                message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
              }`}>
                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-100 bg-white">
        {isRecording && (
          <div className="mb-3 flex items-center gap-2 px-4 py-2 bg-red-50 rounded-full">
            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
            <span className="text-sm text-red-600 font-light">Recording...</span>
          </div>
        )}
        
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setInputValue(e.target.value)}
            onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => e.key === 'Enter' && handleSend()}
            placeholder="Ask anything..."
            className="flex-1 px-4 py-3 bg-gray-50 border border-gray-200 rounded-full text-gray-800 placeholder-gray-400 focus:outline-none focus:border-blue-300 focus:ring-4 focus:ring-blue-50 transition-all text-sm font-light"
          />
          <button
            onClick={toggleRecording}
            className={`w-11 h-11 flex items-center justify-center rounded-full transition-all cursor-pointer ${
              isRecording
                ? 'bg-red-500 hover:bg-red-600 text-white'
                : 'bg-gray-100 hover:bg-gray-200 text-gray-600'
            }`}
          >
            <i className={`${isRecording ? 'ri-stop-circle-fill' : 'ri-mic-line'} text-xl`}></i>
          </button>
          <button
            onClick={handleSend}
            disabled={!inputValue.trim()}
            className="w-11 h-11 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-200 disabled:cursor-not-allowed text-white rounded-full flex items-center justify-center transition-colors cursor-pointer"
          >
            <i className="ri-send-plane-fill text-lg"></i>
          </button>
        </div>
      </div>
    </div>
  );
}
