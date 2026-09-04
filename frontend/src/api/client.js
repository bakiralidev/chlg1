import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const API_BASE = import.meta.env.VITE_API_URL || '';

const client = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor — har so'rovga JWT token qo'shish
client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — 401 bo'lsa logout
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default client;

// ─── API funksiyalari ──────────────────────────────────────────

// Auth
export const api = {
  // Auth
  login: (data) => client.post('/api/v1/auth/login', data),
  register: (data) => client.post('/api/v1/auth/register', data),
  forgotPassword: (email) => client.post('/api/v1/auth/forgot-password', { email }),
  resetPassword: (data) => client.post('/api/v1/auth/reset-password', data),

  // Challenges
  getChallenges: () => client.get('/api/v1/challenges'),
  getMyProgress: (challengeId) => client.get(`/api/v1/challenges/${challengeId}/my-progress`),

  // Session
  enterDay: (dayId) => client.post(`/api/v1/days/${dayId}/enter`),
  typingStart: (sessionId, timestamp) =>
    client.patch(`/api/v1/sessions/${sessionId}/typing-start`, { timestamp }),
  autosave: (sessionId, code) =>
    client.patch(`/api/v1/sessions/${sessionId}/autosave`, { code }),
  reportViolation: (sessionId, type) =>
    client.post(`/api/v1/sessions/${sessionId}/violation`, { violation_type: type }),
  submitCode: (sessionId, code) =>
    client.post(`/api/v1/sessions/${sessionId}/submit`, { code }),

  // Leaderboard
  getLeaderboard: (challengeId) => client.get(`/api/v1/leaderboard/${challengeId}`),

  // Admin
  getAdminChallenges: () => client.get('/api/admin/challenges'),
  createChallenge: (data) => client.post('/api/admin/challenges', data),
  updateChallenge: (id, data) => client.put(`/api/admin/challenges/${id}`, data),
  activateChallenge: (id) => client.post(`/api/admin/challenges/${id}/activate`),
  addDay: (data) => client.post('/api/admin/days', data),
  addQuestion: (data) => client.post('/api/admin/questions', data),
  deleteQuestion: (id) => client.delete(`/api/admin/questions/${id}`),
  getChallengeStats: (id) => client.get(`/api/admin/challenges/${id}/stats`),
  finalizeChallenge: (id) => client.post(`/api/challenges/${id}/finalize`),
};
