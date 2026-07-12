import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'X-API-Key': import.meta.env.VITE_API_KEY || 'casegraph-dev-key'
  }
})

export default api