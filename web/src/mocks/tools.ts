import { Tool } from '../pages/home/types';

export const mockTools: Tool[] = [
  {
    id: '1',
    name: 'LangChain',
    icon: 'ri-links-line',
    description: 'Framework for developing applications powered by language models',
    categories: ['RAG', 'LLM', 'Framework'],
    status: 'verified',
    isWatchlisted: true,
    onePager: {
      overview: 'LangChain is a comprehensive framework designed to simplify the creation of applications using large language models. It provides modular components for building LLM-powered applications, including chains, agents, and memory systems. The framework supports multiple LLM providers and offers extensive integration capabilities with vector databases, APIs, and other tools.',
      pricing: [
        { tier: 'Open Source', price: 'Free', verified: true },
        { tier: 'LangSmith Pro', price: '$39/month', verified: true },
        { tier: 'Enterprise', price: 'Custom', verified: false }
      ],
      techStack: [
        { name: 'Python', verified: true },
        { name: 'TypeScript', verified: true },
        { name: 'OpenAI', verified: true },
        { name: 'Vector DBs', verified: true }
      ],
      keyFeatures: [
        'Modular components for LLM application development',
        'Support for multiple LLM providers (OpenAI, Anthropic, etc.)',
        'Built-in memory and context management',
        'Agent framework for autonomous task execution',
        'Integration with 100+ vector databases and tools',
        'LangSmith for debugging and monitoring'
      ],
      lastUpdated: '2 days ago',
      sources: [
        'https://python.langchain.com/docs/get_started/introduction',
        'https://github.com/langchain-ai/langchain',
        'https://www.langchain.com/pricing'
      ]
    },
    chatHistory: [
      {
        id: '1',
        role: 'user',
        content: 'What makes LangChain different from other LLM frameworks?',
        timestamp: '10:30 AM'
      },
      {
        id: '2',
        role: 'assistant',
        content: 'LangChain stands out with its modular architecture and extensive integration ecosystem. Unlike simpler frameworks, it offers built-in memory management, agent capabilities, and supports 100+ integrations. The LangSmith debugging tool is also unique for production monitoring.',
        timestamp: '10:31 AM'
      }
    ]
  },
  {
    id: '2',
    name: 'Supabase',
    icon: 'ri-database-2-line',
    description: 'Open source Firebase alternative with PostgreSQL database',
    categories: ['Database', 'Backend', 'Auth'],
    status: 'updated',
    isWatchlisted: true,
    onePager: {
      overview: 'Supabase is an open-source Backend-as-a-Service (BaaS) platform that provides a complete backend solution including PostgreSQL database, authentication, real-time subscriptions, storage, and edge functions. It offers a developer-friendly alternative to Firebase with the power of PostgreSQL and full SQL capabilities.',
      pricing: [
        { tier: 'Free', price: '$0/month', verified: true },
        { tier: 'Pro', price: '$25/month', verified: true },
        { tier: 'Team', price: '$599/month', verified: true },
        { tier: 'Enterprise', price: 'Custom', verified: false }
      ],
      techStack: [
        { name: 'PostgreSQL', verified: true },
        { name: 'PostgREST', verified: true },
        { name: 'GoTrue', verified: true },
        { name: 'Deno', verified: true }
      ],
      keyFeatures: [
        'Full PostgreSQL database with pgvector support',
        'Built-in authentication and authorization',
        'Real-time database subscriptions',
        'File storage with CDN',
        'Edge Functions powered by Deno',
        'Auto-generated REST and GraphQL APIs',
        'Row Level Security (RLS) policies'
      ],
      lastUpdated: '1 day ago',
      sources: [
        'https://supabase.com/docs',
        'https://github.com/supabase/supabase',
        'https://supabase.com/pricing'
      ]
    },
    chatHistory: []
  },
  {
    id: '3',
    name: 'Vercel AI SDK',
    icon: 'ri-terminal-box-line',
    description: 'TypeScript toolkit for building AI-powered applications',
    categories: ['AI', 'SDK', 'Streaming'],
    status: 'new',
    isWatchlisted: false,
    onePager: {
      overview: 'The Vercel AI SDK is a TypeScript toolkit designed to help developers build AI-powered streaming text and chat UIs. It provides React hooks, streaming utilities, and integrations with major AI providers, making it easy to add conversational AI features to web applications.',
      pricing: [
        { tier: 'Open Source', price: 'Free', verified: true },
        { tier: 'Vercel Pro', price: '$20/month', verified: true },
        { tier: 'Enterprise', price: 'Custom', verified: false }
      ],
      techStack: [
        { name: 'TypeScript', verified: true },
        { name: 'React', verified: true },
        { name: 'Next.js', verified: true },
        { name: 'Streaming', verified: true }
      ],
      keyFeatures: [
        'React hooks for AI chat interfaces (useChat, useCompletion)',
        'Streaming responses with automatic UI updates',
        'Support for OpenAI, Anthropic, Cohere, and more',
        'Edge runtime compatible',
        'Built-in token counting and rate limiting',
        'Function calling and tool integration'
      ],
      lastUpdated: '3 hours ago',
      sources: [
        'https://sdk.vercel.ai/docs',
        'https://github.com/vercel/ai',
        'https://vercel.com/docs/ai-sdk'
      ]
    },
    chatHistory: []
  },
  {
    id: '4',
    name: 'Pinecone',
    icon: 'ri-stack-line',
    description: 'Managed vector database for AI applications',
    categories: ['Vector DB', 'Search', 'AI'],
    status: 'verified',
    isWatchlisted: false,
    onePager: {
      overview: 'Pinecone is a fully managed vector database designed for machine learning applications. It enables developers to build semantic search, recommendation systems, and RAG applications with high-performance vector similarity search at scale.',
      pricing: [
        { tier: 'Starter', price: 'Free', verified: true },
        { tier: 'Standard', price: '$70/month', verified: true },
        { tier: 'Enterprise', price: 'Custom', verified: true }
      ],
      techStack: [
        { name: 'Vector Search', verified: true },
        { name: 'REST API', verified: true },
        { name: 'gRPC', verified: true },
        { name: 'Python SDK', verified: true }
      ],
      keyFeatures: [
        'Managed vector database with automatic scaling',
        'Sub-100ms query latency at any scale',
        'Metadata filtering for hybrid search',
        'Namespaces for multi-tenancy',
        'Real-time index updates',
        'Built-in sparse-dense hybrid search'
      ],
      lastUpdated: '5 days ago',
      sources: [
        'https://docs.pinecone.io/',
        'https://www.pinecone.io/pricing/',
        'https://github.com/pinecone-io/pinecone-python-client'
      ]
    },
    chatHistory: []
  },
  {
    id: '5',
    name: 'Anthropic Claude',
    icon: 'ri-brain-line',
    description: 'Advanced AI assistant with extended context window',
    categories: ['LLM', 'AI', 'Chat'],
    status: 'updated',
    isWatchlisted: true,
    onePager: {
      overview: 'Claude is a family of large language models developed by Anthropic, designed to be helpful, harmless, and honest. Claude 3 offers industry-leading performance with extended context windows up to 200K tokens, making it ideal for complex reasoning tasks and document analysis.',
      pricing: [
        { tier: 'Claude 3 Haiku', price: '$0.25/MTok', verified: true },
        { tier: 'Claude 3 Sonnet', price: '$3/MTok', verified: true },
        { tier: 'Claude 3 Opus', price: '$15/MTok', verified: true }
      ],
      techStack: [
        { name: 'REST API', verified: true },
        { name: 'Python SDK', verified: true },
        { name: 'TypeScript SDK', verified: true },
        { name: 'Streaming', verified: true }
      ],
      keyFeatures: [
        '200K token context window (500K in extended)',
        'Vision capabilities for image analysis',
        'Function calling and tool use',
        'Strong reasoning and analysis capabilities',
        'Constitutional AI for safety',
        'Multilingual support'
      ],
      lastUpdated: '1 week ago',
      sources: [
        'https://docs.anthropic.com/claude/docs',
        'https://www.anthropic.com/pricing',
        'https://www.anthropic.com/claude'
      ]
    },
    chatHistory: []
  },
  {
    id: '6',
    name: 'Replicate',
    icon: 'ri-rocket-line',
    description: 'Run machine learning models in the cloud',
    categories: ['ML', 'API', 'Deployment'],
    status: 'default',
    isWatchlisted: false,
    onePager: {
      overview: 'Replicate makes it easy to run machine learning models in the cloud. Deploy custom models or use thousands of pre-trained models for image generation, video processing, speech recognition, and more. Pay only for the compute you use with automatic scaling.',
      pricing: [
        { tier: 'Pay-as-you-go', price: 'From $0.0002/sec', verified: true },
        { tier: 'Pro', price: '$29/month + usage', verified: true },
        { tier: 'Enterprise', price: 'Custom', verified: false }
      ],
      techStack: [
        { name: 'Docker', verified: true },
        { name: 'Python', verified: true },
        { name: 'REST API', verified: true },
        { name: 'Webhooks', verified: true }
      ],
      keyFeatures: [
        'Run any ML model with a simple API',
        'Automatic scaling and GPU provisioning',
        'Version control for models',
        'Webhook support for async processing',
        'Custom model deployment with Cog',
        'Pre-trained model marketplace'
      ],
      lastUpdated: '2 weeks ago',
      sources: [
        'https://replicate.com/docs',
        'https://replicate.com/pricing',
        'https://github.com/replicate/cog'
      ]
    },
    chatHistory: []
  }
];
