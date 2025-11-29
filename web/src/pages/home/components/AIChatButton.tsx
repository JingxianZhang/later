import { useState } from 'react';

interface AIChatButtonProps {
  onToggle: () => void;
  isOpen: boolean;
}

export default function AIChatButton({ onToggle, isOpen }: AIChatButtonProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <button
      onClick={onToggle}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="fixed bottom-8 right-8 w-12 h-12 bg-gradient-to-br from-sky-400 to-rose-200 hover:from-sky-500 hover:to-rose-300 rounded-full shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center cursor-pointer z-[3000] group"
      style={{ transform: isOpen ? 'rotate(45deg)' : 'rotate(0deg)' }}
    >
      {isOpen ? (
        <i className="ri-close-line text-2xl text-white"></i>
      ) : (
        <i className="ri-sparkling-2-fill text-2xl text-white"></i>
      )}
      
      {/* Tooltip */}
      {isHovered && !isOpen && (
        <div className="absolute right-full mr-4 px-4 py-2 bg-gray-800 text-white text-sm rounded-lg whitespace-nowrap font-light">
          Ask AI about my gallery
        </div>
      )}
    </button>
  );
}
