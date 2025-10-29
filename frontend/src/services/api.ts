import axios from 'axios';

const API_BASE_URL = '/api';

export const api = {
  uploadPolicy: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await axios.post(`${API_BASE_URL}/policies/upload`, formData);
    return response.data;
  },

  getPolicies: async () => {
    const response = await axios.get(`${API_BASE_URL}/policies`);
    return response.data;
  },

  deletePolicy: async (id: number) => {
    const response = await axios.delete(`${API_BASE_URL}/policies/${id}`);
    return response.data;
  },

  uploadUsers: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await axios.post(`${API_BASE_URL}/users/upload`, formData);
    return response.data;
  },

  getUsers: async () => {
    const response = await axios.get(`${API_BASE_URL}/users`);
    return response.data;
  },

  deleteUser: async (id: number) => {
    const response = await axios.delete(`${API_BASE_URL}/users/${id}`);
    return response.data;
  },

  evaluate: async (usersFile: File, policiesFile: File) => {
    const formData = new FormData();
    formData.append('users_file', usersFile);
    formData.append('policies_file', policiesFile);
    const response = await axios.post(`${API_BASE_URL}/evaluate`, formData);
    return response.data;
  },

  evaluateSelection: async (userIds: number[], policyIds: number[]) => {
    const response = await axios.post(`${API_BASE_URL}/evaluate/selection`, {
      user_ids: userIds,
      policy_ids: policyIds,
    });
    return response.data;
  },

  getResults: async () => {
    const response = await axios.get(`${API_BASE_URL}/results`);
    return response.data;
  },

  clearResults: async () => {
    const response = await axios.delete(`${API_BASE_URL}/results`);
    return response.data;
  },
};
