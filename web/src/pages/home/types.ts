export interface Tool {
  id: string;
  name: string;
  icon: string;
  canonicalUrl?: string;
  description: string;
  categories: string[];
  status: 'new' | 'updated' | 'verified' | 'default';
  isWatchlisted: boolean;
  onePager: {
    overview: string;
    pricing: {
      tier: string;
      price: string;
      details?: string;
      verified: boolean;
    }[];
    techStack: {
      name: string;
      verified: boolean;
    }[];
    keyFeatures: string[];
    howToUse?: string[];
    useCases?: string[];
    userFeedback?: string[];
    integrations?: string[];
    recentUpdates?: string[];
    competitors?: string[];
    lastUpdated: string;
    sources: string[];
  };
  chatHistory: {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
  }[];
  highlights?: {
    platform: string;
    url: string;
    title?: string;
    author?: string;
    thumbnailUrl?: string;
    metrics?: Record<string, any>;
  }[];
}
