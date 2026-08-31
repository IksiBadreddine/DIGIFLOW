// frontend/src/services/api.js

import axios from 'axios';

const API_URL = '/api';

const api = axios.create({
  baseURL: API_URL,
  timeout: 1800000,  // ✅ 10 minutes

});

export const analyzeDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/analyze', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 1800000,  // ✅ 10 minutes
  });

  return response.data;
};

export const analyzeBatch = async (files) => {
  const formData = new FormData();
  files.forEach(file => {
    formData.append('files', file);
  });

  const response = await api.post('/analyze/batch', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

export const searchKnowledge = async (query, limit = 5) => {
  const response = await api.get('/search', {
    params: { q: query, limit }
  });
  return response.data;
};

// ✅ CORRECTION : Format de la requête
export const generateOffer = async (sessionId, selectedProductIds) => {
  // ✅ Vérifier que sessionId est une chaîne
  // ✅ Vérifier que selectedProductIds est un tableau
  const payload = {
    session_id: sessionId,
    selected_product_ids: selectedProductIds || []
  };
  
  console.log('📤 Génération offre payload:', payload);
  
  const response = await api.post('/generate-offer', payload, {
    headers: {
      'Content-Type': 'application/json',
    },
  });

  return response.data;
};

export const exportDocxUrl = (sessionId) => {
  return `/api/export/${sessionId}`;
};

export default api;