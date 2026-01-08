/**
 * Application configuration.
 * Single source of truth for environment-dependent values.
 */

// API base URL - use VITE_API_BASE env var for production
export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
