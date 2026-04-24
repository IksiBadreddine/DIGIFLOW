import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export async function analyzeDocument(file, onProgress) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/analyze', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: e => onProgress && onProgress(Math.round(e.loaded / e.total * 100)),
  })
  return data
}

export async function generateOffer(sessionId, selectedProductIds = []) {
  const { data } = await api.post('/generate-offer', {
    session_id: sessionId,
    selected_product_ids: selectedProductIds,
  })
  return data
}

export function exportDocxUrl(sessionId) {
  return `/api/export/${sessionId}`
}
