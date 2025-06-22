// src/utils/constants.ts
export const API_BASE_URL = '/api/v1';

export const ANIMATION_DURATION = {
  fast: 0.2,
  normal: 0.3,
  slow: 0.5,
} as const;

export const COLORS = {
  primary: {
    50: '#f0f9ff',
    500: '#3b82f6',
    600: '#2563eb',
    700: '#1d4ed8',
  },
  success: {
    400: '#4ade80',
    500: '#22c55e',
  },
  warning: {
    400: '#fbbf24',
    500: '#f59e0b',
  },
  error: {
    400: '#f87171',
    500: '#ef4444',
  },
} as const;

export const REACT_CATEGORIES = {
  schema_exploration: {
    color: 'blue',
    icon: '🔍',
    label: 'Schema Exploration',
  },
  data_retrieval: {
    color: 'green',
    icon: '📊',
    label: 'Data Retrieval',
  },
  validation: {
    color: 'orange',
    icon: '✅',
    label: 'Validation',
  },
  unknown: {
    color: 'gray',
    icon: '🔧',
    label: 'Other',
  },
} as const;

// src/utils/animations.ts
export const fadeInUp = {
  hidden: { 
    opacity: 0, 
    y: 20 
  },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: {
      duration: 0.3,
      ease: 'easeOut'
    }
  }
};

export const fadeIn = {
  hidden: { opacity: 0 },
  visible: { 
    opacity: 1,
    transition: {
      duration: 0.3
    }
  }
};

export const slideIn = {
  hidden: { 
    opacity: 0, 
    x: -20 
  },
  visible: { 
    opacity: 1, 
    x: 0,
    transition: {
      duration: 0.3,
      ease: 'easeOut'
    }
  }
};

export const scaleIn = {
  hidden: { 
    opacity: 0, 
    scale: 0.8 
  },
  visible: { 
    opacity: 1, 
    scale: 1,
    transition: {
      duration: 0.3,
      ease: 'easeOut'
    }
  }
};

export const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.1
    }
  }
};