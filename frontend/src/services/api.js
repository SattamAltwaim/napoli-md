/**
 * API client for the Flask backend.
 *
 * The backend owns trajectory discovery, CSV parsing, frame concatenation, and
 * aggregation. The frontend only requests already-shaped analysis payloads.
 */
import axios from 'axios'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

const apiClient = axios.create({
  baseURL: API_BASE
})

apiClient.interceptors.response.use(
  response => response,
  error => {
    const message = error.response?.data?.error || error.response?.data?.message || error.message
    return Promise.reject(new Error(message || 'API request failed'))
  }
)

function buildUrl(path, params = {}) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const query = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    if (Array.isArray(value)) {
      value.forEach(item => {
        if (item !== undefined && item !== null && item !== '') {
          query.append(key, String(item))
        }
      })
      return
    }
    query.append(key, String(value))
  })

  const queryString = query.toString()
  return `${API_BASE}${normalizedPath}${queryString ? `?${queryString}` : ''}`
}

async function request(path, options = {}) {
  const response = await fetch(buildUrl(path, options.params), {
    method: options.method || 'GET',
    headers: options.headers,
    body: options.body
  })

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    const message = payload?.error || payload?.message || `API request failed with status ${response.status}`
    throw new Error(message)
  }

  return payload
}

async function jsonRequest(path, method, payload) {
  return request(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

function appendIfPresent(formData, key, value) {
  if (value === undefined || value === null) return
  formData.append(key, String(value))
}

function buildUploadFormData(file, options = {}) {
  const formData = new FormData()
  formData.append('file', file)
  appendIfPresent(formData, 'job_name', options.jobName)
  appendIfPresent(formData, 'email', options.email)
  appendIfPresent(formData, 'chain1', options.chain1)
  appendIfPresent(formData, 'chain2', options.chain2)
  appendIfPresent(formData, 'reduce', Boolean(options.useReduce))
  appendIfPresent(formData, 'interface_cutoff', options.interfaceCutoff)
  appendIfPresent(formData, 'water_cutoff', options.waterCutoff)
  appendIfPresent(formData, 'start_frame', options.startFrame)
  appendIfPresent(formData, 'end_frame', options.endFrame)
  appendIfPresent(formData, 'frame_step', options.frameStep)
  return formData
}

function progressPercent(event) {
  if (!event.total) return 0
  return Math.round((event.loaded * 100) / event.total)
}

export default {
  getSystems() {
    return request('/systems')
  },

  getSystem(systemId) {
    return request(`/systems/${encodeURIComponent(systemId)}`)
  },

  renameSystem() {
    return Promise.resolve({ success: true })
  },

  getInteractions(systemId) {
    return request(`/systems/${encodeURIComponent(systemId)}/interactions`)
  },

  getAreaData(systemId) {
    return request(`/systems/${encodeURIComponent(systemId)}/area`)
  },

  getTrends(systemId) {
    return request(`/systems/${encodeURIComponent(systemId)}/trends`)
  },

  getAtomPairs(systemId, params = {}) {
    return request(`/systems/${encodeURIComponent(systemId)}/atom-pairs`, { params })
  },

  getAtomPairsBatch(systemId, pairs = []) {
    return jsonRequest(`/systems/${encodeURIComponent(systemId)}/atom-pairs/batch`, 'POST', { pairs })
  },

  getInteractionDistances(systemId) {
    return request(`/systems/${encodeURIComponent(systemId)}/interaction-distances`)
  },

  getConservedIslands(systemId) {
    return request(`/systems/${encodeURIComponent(systemId)}/conserved-islands`)
  },

  getFramePdbUrl(systemId, frameNumber) {
    return buildUrl(`/systems/${encodeURIComponent(systemId)}/frame/${frameNumber}/pdb`)
  },

  async getFramePdbContent(systemId, frameNumber) {
    const response = await fetch(this.getFramePdbUrl(systemId, frameNumber))
    if (!response.ok) {
      throw new Error(`Failed to load frame ${frameNumber}`)
    }
    return response.text()
  },

  getDistanceDistributions(systemId, interactionTypes = []) {
    return request(`/systems/${encodeURIComponent(systemId)}/distance-distributions`, {
      params: { interaction_types: interactionTypes }
    })
  },

  uploadFile(file, onUploadProgress) {
    return this.uploadFileWithOptions(file, {}, onUploadProgress)
  },

  async uploadFileWithOptions(file, options = {}, onUploadProgress) {
    const formData = buildUploadFormData(file, options)
    const response = await apiClient.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: event => {
        if (onUploadProgress) onUploadProgress(progressPercent(event))
      }
    })
    return response.data
  },

  getStatus(jobId) {
    return request(`/status/${encodeURIComponent(jobId)}`)
  },

  getJobs() {
    return request('/jobs')
  }
}
