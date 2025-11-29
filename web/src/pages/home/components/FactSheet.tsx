import { Tool } from '../types';

interface FactSheetProps {
  tool: Tool;
}

export default function FactSheet({ tool }: FactSheetProps) {
  const { onePager } = tool;

  return (
    <div className="p-6 space-y-6">
      {/* Overview */}
      <section>
        <h3 className="text-lg font-semibold text-gray-800 mb-3">Overview</h3>
        <p className="text-gray-700 leading-relaxed">{onePager.overview}</p>
      </section>

      {/* Key Features */}
      <section>
        <h3 className="text-lg font-semibold text-gray-800 mb-3">Key Features</h3>
        <ul className="space-y-2">
          {onePager.keyFeatures.map((feature, index) => (
            <li key={index} className="flex items-start gap-2">
              <i className="ri-check-line text-green-500 text-lg mt-0.5 flex-shrink-0"></i>
              <span className="text-gray-700">{feature}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* Pricing */}
      <section>
        <h3 className="text-lg font-semibold text-gray-800 mb-3">Pricing</h3>
        <div className="space-y-3">
          {onePager.pricing.map((tier, index) => (
            <div key={index} className="bg-white rounded-lg p-4 border border-gray-200">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h4 className="font-semibold text-gray-800">{tier.tier}</h4>
                  <p className="text-2xl font-bold text-blue-600 mt-1">{tier.price}</p>
                </div>
              </div>
              {tier.details && (
                <p className="text-sm text-gray-600 mt-2">{tier.details}</p>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Tech Stack */}
      <section>
        <h3 className="text-lg font-semibold text-gray-800 mb-3">Tech Stack</h3>
        <div className="flex flex-wrap gap-2">
          {onePager.techStack.map((tech, index) => (
            <span
              key={index}
              className="px-3 py-1.5 bg-white border border-gray-200 text-gray-700 text-sm rounded-lg"
            >
              {tech.name}
            </span>
          ))}
        </div>
      </section>

      {/* Sources */}
      <section>
        <h3 className="text-lg font-semibold text-gray-800 mb-3">Sources</h3>
        <div className="space-y-2">
          {onePager.sources.map((source, index) => (
            <a
              key={index}
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-blue-600 hover:text-blue-700 text-sm cursor-pointer"
            >
              <i className="ri-external-link-line"></i>
              <span className="truncate">{source.url}</span>
            </a>
          ))}
        </div>
      </section>

      {/* Last Updated */}
      <div className="pt-4 border-t border-gray-200">
        <p className="text-sm text-gray-500">
          Last updated: {onePager.lastUpdated}
        </p>
      </div>
    </div>
  );
}
