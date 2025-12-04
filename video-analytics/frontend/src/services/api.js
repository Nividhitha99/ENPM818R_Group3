import axios from 'axios';

const API_BASE = '/api/analytics';

export const analyticsAPI = {
  // Get all videos
  getVideos: async (limit = 100, sortBy = 'timestamp') => {
    const response = await axios.get(`${API_BASE}/videos`, {
      params: { limit, sort_by: sortBy }
    });
    return response.data;
  },

  // Get single video by ID
  getVideo: async (videoId) => {
    const response = await axios.get(`${API_BASE}/video/${videoId}`);
    return response.data;
  },

  // Record a view
  recordView: async (videoId) => {
    const response = await axios.post(`${API_BASE}/view/${videoId}`);
    return response.data;
  },

  // Record a like
  recordLike: async (videoId) => {
    const response = await axios.post(`${API_BASE}/like/${videoId}`);
    return response.data;
  },

  // Get stats (existing endpoint)
  getStats: async () => {
    const response = await axios.get(`${API_BASE}/stats`);
    return response.data;
  }
};

