import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'https://casegraph-api.onrender.com',
  headers: {
    'X-API-Key': import.meta.env.VITE_API_KEY || 'casegraph-dev-key'
  }
})

export default api