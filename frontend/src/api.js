import axios from 'axios';

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE,
  timeout: 15000,
});

// Wrapper around backend digest endpoints.
export const digestApi = {
  generate: (topicId = null) => {
    const params = topicId ? { topic_id: topicId } : {};
    return api.post('/digest/generate', null, { params });
  },

  status: (taskId) => api.get(`/digest/status/${taskId}`),

  latest: () => api.get('/digest/latest'),

  byId: (id) => api.get(`/digest/${id}`),

  list: () => api.get('/digests'),

  topics: () => api.get('/config/topics'),
};

export default api;