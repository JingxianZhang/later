
import type { Tool } from '../types';

interface DetailViewProps {
  tool: Tool;
  onClose: () => void;
  allTools: Tool[];
  onToolChange: (tool: Tool) => void;
  isChatOpen: boolean;
}

export default function DetailView({ tool, onClose, allTools, onToolChange, isChatOpen }: DetailViewProps) {
  const currentIndex = allTools.findIndex(t => t.id === tool.id);
  const prevTool = currentIndex > 0 ? allTools[currentIndex - 1] : null;
  const nextTool = currentIndex < allTools.length - 1 ? allTools[currentIndex + 1] : null;

  return (
    <div 
      className={`fixed inset-0 bg-black/20 backdrop-blur-sm z-[2000] flex items-center justify-center p-8 transition-all duration-300 ${
        isChatOpen ? 'pr-[416px]' : ''
      }`}
    >
      {/* Left Thumbnail */}
      {prevTool && (
        <button
          onClick={() => onToolChange(prevTool)}
          className={`absolute top-1/2 -translate-y-1/2 group cursor-pointer transition-all duration-300 z-30 hover:z-50 ${isChatOpen ? 'left-4' : 'left-8'}`}
          style={{ 
            transform: 'translateY(-50%) rotate(-3deg)'
          }}
        >
          <div className="w-32 h-40 bg-white rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 hover:rotate-0 hover:scale-110 border border-gray-200 p-3 flex flex-col items-center justify-center gap-2">
            <i className="ri-arrow-left-line text-2xl text-gray-400 group-hover:text-blue-500 transition-colors"></i>
            <div className="w-10 h-10 bg-gradient-to-br from-blue-100 to-purple-100 rounded-lg flex items-center justify-center">
              {prevTool.icon.startsWith('http') ? (
                <img src={prevTool.icon} alt="" className="w-6 h-6 object-contain" />
              ) : (
                <i className={`${prevTool.icon} text-xl text-blue-600`}></i>
              )}
            </div>
            <p className="text-xs text-gray-600 text-center font-light truncate w-full">{prevTool.name}</p>
          </div>
        </button>
      )}

      {/* Main Card */}
      <div 
        className={`bg-white rounded-2xl shadow-2xl overflow-hidden transition-all duration-300 max-h-[85vh] flex flex-col relative z-40 ${
          isChatOpen ? 'w-[90%]' : 'w-[75%]'
        } max-w-5xl`}
      >
        {/* Header */}
        <div className="px-8 py-6 border-b border-gray-100 bg-gradient-to-r from-blue-50/50 to-purple-50/50">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-100 to-purple-100 rounded-2xl flex items-center justify-center flex-shrink-0 overflow-hidden">
                {tool.icon.startsWith('http') ? (
                  <img src={tool.icon} alt="" className="w-10 h-10 object-contain" />
                ) : (
                  <i className={`${tool.icon} text-3xl text-blue-600`}></i>
                )}
              </div>
              <div>
                <h2 className="text-2xl font-normal text-gray-800 mb-1" style={{ fontFamily: '"Google Sans", sans-serif' }}>
                  {tool.name}
                </h2>
                <p className="text-sm text-gray-500 font-light">{tool.description}</p>
                {tool.canonicalUrl && (
                  <a
                    href={tool.canonicalUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-1 inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 font-light cursor-pointer"
                  >
                    <i className="ri-external-link-line"></i>
                    {tool.canonicalUrl}
                  </a>
                )}
                <div className="flex flex-wrap gap-2 mt-3">
                  {tool.categories.map(cat => (
                    <span key={cat} className="px-3 py-1 bg-blue-50 text-blue-600 rounded-full text-xs font-light">
                      #{cat}
                    </span>
                  ))}
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors cursor-pointer flex-shrink-0"
            >
              <i className="ri-close-line text-2xl text-gray-600"></i>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-8 py-6">
          {/* Overview */}
          <section className="mb-8">
            <h3 className="text-lg font-normal text-gray-800 mb-3" style={{ fontFamily: '"Google Sans", sans-serif' }}>
              Overview
            </h3>
            <p className="text-gray-600 leading-relaxed font-light">
              {tool.onePager.overview}
            </p>
          </section>

          {/* Key Features */}
          <section className="mb-8">
            <h3 className="text-lg font-normal text-gray-800 mb-3" style={{ fontFamily: '"Google Sans", sans-serif' }}>
              Key Features
            </h3>
            <ul className="space-y-2">
              {tool.onePager.keyFeatures.map((feature, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <i className="ri-checkbox-circle-fill text-green-500 text-lg mt-0.5 flex-shrink-0"></i>
                  <span className="text-gray-600 font-light">{feature}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* How to Use */}
          {tool.onePager.howToUse && tool.onePager.howToUse.length > 0 && (
            <section className="mb-8">
              <h3 className="text-lg font-normal text-gray-800 mb-3" style={{ fontFamily: '"Google Sans", sans-serif' }}>
                How to Use
              </h3>
              <ol className="space-y-2 list-decimal ml-5">
                {tool.onePager.howToUse.map((step, idx) => (
                  <li key={idx} className="text-gray-600 font-light">{step}</li>
                ))}
              </ol>
            </section>
          )}

          {/* Pricing */}
          <section className="mb-8">
            <h3 className="text-lg font-normal text-gray-800 mb-3" style={{ fontFamily: '"Google Sans", sans-serif' }}>
              Pricing
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {tool.onePager.pricing.map((tier, idx) => (
                <div key={idx} className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                  <h4 className="font-normal text-gray-800 mb-1">{tier.tier}</h4>
                  <p className="text-2xl font-light text-blue-600 mb-2">{tier.price}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Recent Updates */}
          {tool.onePager.recentUpdates && tool.onePager.recentUpdates.length > 0 && (
            <section className="mb-8">
              <h3 className="text-lg font-normal text-gray-800 mb-3" style={{ fontFamily: '"Google Sans", sans-serif' }}>
                Recent Updates
              </h3>
              <ul className="space-y-2">
                {tool.onePager.recentUpdates.map((u, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <i className="ri-time-line text-blue-500 text-lg mt-0.5 flex-shrink-0"></i>
                    <span className="text-gray-600 font-light">{u}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Tech Stack */}
          <section className="mb-8">
            <h3 className="text-lg font-normal text-gray-800 mb-3" style={{ fontFamily: '"Google Sans", sans-serif' }}>
              Tech Stack
            </h3>
            <div className="flex flex-wrap gap-2">
              {tool.onePager.techStack.map((tech, idx) => (
                <span key={idx} className="px-4 py-2 bg-purple-50 text-purple-600 rounded-lg text-sm font-light">
                  {tech.name}
                </span>
              ))}
            </div>
          </section>

          {/* Integrations */}
          {tool.onePager.integrations && tool.onePager.integrations.length > 0 && (
            <section className="mb-8">
              <h3 className="text-lg font-normal text-gray-800 mb-3" style={{ fontFamily: '"Google Sans", sans-serif' }}>
                Integrations
              </h3>
              <div className="flex flex-wrap gap-2">
                {tool.onePager.integrations.map((it, idx) => (
                  <span key={idx} className="px-3 py-1 bg-emerald-50 text-emerald-600 rounded-full text-xs font-light">
                    {it}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* Use Cases */}
          {tool.onePager.useCases && tool.onePager.useCases.length > 0 && (
            <section className="mb-8">
              <h3 className="text-lg font-normal text-gray-800 mb-3" style={{ fontFamily: '"Google Sans", sans-serif' }}>
                Use Cases
              </h3>
              <ul className="space-y-2">
                {tool.onePager.useCases.map((uc, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <i className="ri-lightbulb-line text-amber-500 text-lg mt-0.5 flex-shrink-0"></i>
                    <span className="text-gray-600 font-light">{uc}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* User Feedback */}
          {tool.onePager.userFeedback && tool.onePager.userFeedback.length > 0 && (
            <section className="mb-8">
              <h3 className="text-lg font-normal text-gray-800 mb-3" style={{ fontFamily: '"Google Sans", sans-serif' }}>
                User Feedback
              </h3>
              <ul className="space-y-2">
                {tool.onePager.userFeedback.map((fb, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <i className="ri-chat-3-line text-fuchsia-500 text-lg mt-0.5 flex-shrink-0"></i>
                    <span className="text-gray-600 font-light">{fb}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Competitors */}
          {tool.onePager.competitors && tool.onePager.competitors.length > 0 && (
            <section className="mb-8">
              <h3 className="text-lg font-normal text-gray-800 mb-3" style={{ fontFamily: '"Google Sans", sans-serif' }}>
                Competitors
              </h3>
              <div className="flex flex-wrap gap-2">
                {tool.onePager.competitors.map((c, idx) => (
                  <span key={idx} className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-light">
                    {c}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* Sources */}
          <section>
            <h3 className="text-lg font-normal text-gray-800 mb-3" style={{ fontFamily: '"Google Sans", sans-serif' }}>
              Sources
            </h3>
            <div className="space-y-2">
              {(tool.onePager.sources ?? []).map((source, idx) => (
                <a
                  key={idx}
                  href={source}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-blue-600 hover:text-blue-700 text-sm font-light cursor-pointer"
                >
                  <i className="ri-external-link-line"></i>
                  <span className="truncate">{source}</span>
                </a>
              ))}
            </div>
          </section>

          {/* Highlights */}
          {tool.highlights && tool.highlights.length > 0 && (
            <section className="mt-8">
              <h3 className="text-lg font-normal text-gray-800 mb-3" style={{ fontFamily: '"Google Sans", sans-serif' }}>
                Highlights
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {tool.highlights.map((h, idx) => (
                  <a
                    key={idx}
                    href={h.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex gap-3 p-3 bg-gray-50 rounded-xl border border-gray-200 hover:bg-gray-100 transition-colors cursor-pointer"
                  >
                    <div className="w-16 h-16 bg-white rounded-lg overflow-hidden flex items-center justify-center border border-gray-200">
                      {h.thumbnailUrl ? (
                        <img src={h.thumbnailUrl} alt="" className="w-full h-full object-cover" />
                      ) : (
                        <i className="ri-play-circle-line text-2xl text-gray-400"></i>
                      )}
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs text-gray-500 uppercase tracking-wide">{h.platform}</div>
                      <div className="text-sm text-gray-800 font-light truncate">{h.title || h.url}</div>
                      {h.author && <div className="text-xs text-gray-500">{h.author}</div>}
                    </div>
                  </a>
                ))}
              </div>
            </section>
          )}

          {/* Last Updated */}
          <div className="mt-6 pt-6 border-t border-gray-100">
            <p className="text-xs text-gray-400 font-light">
              Last updated: {(() => {
                try {
                  const d = new Date(tool.onePager.lastUpdated);
                  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                } catch {
                  return tool.onePager.lastUpdated;
                }
              })()}
            </p>
          </div>
        </div>
      </div>

      {/* Right Thumbnail */}
      {nextTool && (
        <button
          onClick={() => onToolChange(nextTool)}
          className={`absolute top-1/2 -translate-y-1/2 group cursor-pointer transition-all duration-300 z-30 hover:z-50 ${isChatOpen ? 'right-[400px]' : 'right-8'}`}
          style={{ 
            transform: 'translateY(-50%) rotate(3deg)'
          }}
        >
          <div className="w-32 h-40 bg-white rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 hover:rotate-0 hover:scale-110 border border-gray-200 p-3 flex flex-col items-center justify-center gap-2">
            <i className="ri-arrow-right-line text-2xl text-gray-400 group-hover:text-blue-500 transition-colors"></i>
            <div className="w-10 h-10 bg-gradient-to-br from-blue-100 to-purple-100 rounded-lg flex items-center justify-center">
              {nextTool.icon.startsWith('http') ? (
                <img src={nextTool.icon} alt="" className="w-6 h-6 object-contain" />
              ) : (
                <i className={`${nextTool.icon} text-xl text-blue-600`}></i>
              )}
            </div>
            <p className="text-xs text-gray-600 text-center font-light truncate w-full">{nextTool.name}</p>
          </div>
        </button>
      )}
    </div>
  );
}
