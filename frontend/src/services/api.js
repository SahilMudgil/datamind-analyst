const API_BASE_URL = import.meta.env.VITE_API_URL || '';

class ApiService {
  constructor() {
    this.token = localStorage.getItem('token') || sessionStorage.getItem('token');
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('token', token);
      sessionStorage.setItem('token', token);
    } else {
      localStorage.removeItem('token');
      sessionStorage.removeItem('token');
    }
  }

  getHeaders(customHeaders = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...customHeaders
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = this.getHeaders(options.headers);

    try {
      const response = await fetch(url, {
        ...options,
        headers
      });

      if (response.status === 401) {
        // Clear invalid token
        this.setToken(null);
        window.dispatchEvent(new Event('auth:unauthorized'));
      }

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || `Request failed with status ${response.status}`);
      }

      return data;
    } catch (err) {
      throw err;
    }
  }

  // Auth endpoints
  async register(email, password, name) {
    const data = await this.request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name })
    });
    this.setToken(data.access_token);
    return data;
  }

  async login(email, password) {
    const data = await this.request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    this.setToken(data.access_token);
    return data;
  }

  async getMe() {
    return this.request('/api/auth/me');
  }

  async checkHealth() {
    return this.request('/api/health');
  }

  // Database Connection endpoints
  async testConnection(data) {
    return this.request('/api/connections/test', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async createConnection(data) {
    return this.request('/api/connections', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async getConnections() {
    return this.request('/api/connections');
  }

  async getConnectionSchema(connectionId) {
    return this.request(`/api/connections/${connectionId}/schema`);
  }

  async refreshSchema(connectionId) {
    return this.request(`/api/connections/${connectionId}/refresh-schema`, {
      method: 'POST'
    });
  }

  async deleteConnection(connectionId) {
    return this.request(`/api/connections/${connectionId}`, {
      method: 'DELETE'
    });
  }

  // CSV Upload endpoint
  async uploadCSV(file, customTableName = '') {
    const formData = new FormData();
    formData.append('file', file);
    if (customTableName) {
      formData.append('table_name', customTableName);
      formData.append('custom_table_name', customTableName);
    }

    const headers = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const API_BASE_URL = import.meta.env.VITE_API_URL || '';
    const res = await fetch(`${API_BASE_URL}/api/csv/upload`, {
      method: 'POST',
      headers,
      body: formData
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || 'CSV upload failed');
    }
    return data;
  }

  // Chat & Conversation endpoints
  async createConversation(connectionId, title = 'New Analysis') {
    return this.request('/api/chat/conversations', {
      method: 'POST',
      body: JSON.stringify({ connection_id: connectionId, title })
    });
  }

  async getConversations(connectionId = null) {
    const url = connectionId ? `/api/chat/conversations?connection_id=${connectionId}` : '/api/chat/conversations';
    return this.request(url);
  }

  async getConversationMessages(conversationId) {
    return this.request(`/api/chat/conversations/${conversationId}/messages`);
  }

  async deleteConversation(conversationId) {
    return this.request(`/api/chat/conversations/${conversationId}`, {
      method: 'DELETE'
    });
  }

  async sendQueryRest(connectionId, query, conversationId = null) {
    return this.request('/api/chat/query', {
      method: 'POST',
      body: JSON.stringify({ connection_id: connectionId, query, conversation_id: conversationId })
    });
  }

  // Dashboard & Bookmarks endpoints
  async createDashboardWidget(data) {
    return this.request('/api/dashboard/widgets', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async getDashboardWidgets() {
    return this.request('/api/dashboard/widgets');
  }

  async getDashboardWidgetsLive() {
    return this.request('/api/dashboard/widgets/live');
  }

  async refreshDashboardWidget(widgetId) {
    return this.request(`/api/dashboard/widgets/${widgetId}/refresh`, {
      method: 'POST'
    });
  }

  async deleteDashboardWidget(widgetId) {
    return this.request(`/api/dashboard/widgets/${widgetId}`, {
      method: 'DELETE'
    });
  }

  async createBookmark(data) {
    return this.request('/api/bookmarks', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async getBookmarks() {
    return this.request('/api/bookmarks');
  }

  async deleteBookmark(bookmarkId) {
    return this.request(`/api/bookmarks/${bookmarkId}`, {
      method: 'DELETE'
    });
  }
}

export const api = new ApiService();
