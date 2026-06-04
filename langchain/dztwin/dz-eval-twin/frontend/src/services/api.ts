import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import { Customer, ApplicationProfile, Dataset, TestCase, EvaluationRun } from '../types';

// Get API base URL from environment or use default
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Error response type
interface ErrorResponse {
  detail?: string;
  message?: string;
}

class APIClient {
  private client: AxiosInstance;
  private requestCount: number = 0;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000, // 30 second timeout
    });

    this.setupInterceptors();
  }

  // Setup request and response interceptors
  private setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        this.requestCount++;
        
        // Add timestamp to request
        config.headers['X-Request-Time'] = new Date().toISOString();
        
        // Log request in development
        console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, {
          headers: config.headers,
          customerId: config.headers['X-Customer-ID']
        });
        
        return config;
      },
      (error: AxiosError) => {
        console.error('[API Request Error]', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        this.requestCount--;
        
        // Log response in development
        console.log(`[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, response.status);
        
        return response;
      },
      (error: AxiosError<ErrorResponse>) => {
        this.requestCount--;
        
        // Handle different error types
        if (error.response) {
          // Server responded with error status
          const errorMessage = error.response.data?.detail || error.response.data?.message || 'An error occurred';
          console.error(`[API Error] ${error.response.status}:`, errorMessage);
          
          // Handle specific status codes
          switch (error.response.status) {
            case 401:
              console.error('Unauthorized - Please log in');
              break;
            case 403:
              console.error('Forbidden - You do not have permission');
              break;
            case 404:
              console.error('Not found');
              break;
            case 500:
              console.error('Server error - Please try again later');
              break;
          }
        } else if (error.request) {
          // Request made but no response received
          console.error('[API Error] No response received:', error.message);
        } else {
          // Error setting up request
          console.error('[API Error] Request setup failed:', error.message);
        }
        
        return Promise.reject(error);
      }
    );
  }

  // Get current loading state
  isLoading(): boolean {
    return this.requestCount > 0;
  }

  // Set customer context for tenant-scoped requests
  setCustomerContext(customerId: string) {
    this.client.defaults.headers.common['X-Customer-ID'] = customerId;
  }

  // Clear customer context
  clearCustomerContext() {
    delete this.client.defaults.headers.common['X-Customer-ID'];
  }

  // Customer operations (admin only)
  async createCustomer(data: {
    name: string;
    contactEmail: string;
    contactPhone?: string;
    configuration?: Record<string, any>;
  }): Promise<Customer> {
    const response = await this.client.post<Customer>('/api/customers', data);
    return response.data;
  }

  async getCustomers(): Promise<Customer[]> {
    const response = await this.client.get<Customer[]>('/api/customers');
    return response.data;
  }

  async getCustomer(id: string): Promise<Customer> {
    const response = await this.client.get<Customer>(`/api/customers/${id}`);
    return response.data;
  }

  async updateCustomer(id: string, updates: Partial<Customer>): Promise<Customer> {
    const response = await this.client.put<Customer>(`/api/customers/${id}`, updates);
    return response.data;
  }

  async deleteCustomer(id: string): Promise<void> {
    await this.client.delete(`/api/customers/${id}`);
  }

  // Application profile operations (admin only)
  async createApplicationProfile(
    customerId: string,
    data: {
      name: string;
      type: string;
      connectionConfig: {
        endpoint: string;
        authentication?: Record<string, any>;
        timeout?: number;
        retries?: number;
        customHeaders?: Record<string, string>;
      };
    }
  ): Promise<ApplicationProfile> {
    // Flatten connectionConfig for backend API, only include defined values
    const requestData: any = {
      name: data.name,
      type: data.type,
      endpoint: data.connectionConfig.endpoint,
    };
    
    // Only add optional fields if they are defined
    if (data.connectionConfig.timeout !== undefined) {
      requestData.timeout = data.connectionConfig.timeout;
    }
    if (data.connectionConfig.retries !== undefined) {
      requestData.retries = data.connectionConfig.retries;
    }
    if (data.connectionConfig.authentication !== undefined) {
      requestData.authentication = data.connectionConfig.authentication;
    }
    if (data.connectionConfig.customHeaders !== undefined) {
      requestData.customHeaders = data.connectionConfig.customHeaders;
    }
    
    const response = await this.client.post<ApplicationProfile>(
      `/api/customers/${customerId}/application-profiles`,
      requestData
    );
    return response.data;
  }

  async getApplicationProfiles(customerId?: string): Promise<ApplicationProfile[]> {
    const url = customerId
      ? `/api/customers/${customerId}/application-profiles`
      : '/api/application-profiles';
    const response = await this.client.get<ApplicationProfile[]>(url);
    return response.data;
  }

  async getApplicationProfile(id: string): Promise<ApplicationProfile> {
    const response = await this.client.get<ApplicationProfile>(`/api/application-profiles/${id}`);
    return response.data;
  }

  async updateApplicationProfile(
    id: string,
    updates: Partial<ApplicationProfile>
  ): Promise<ApplicationProfile> {
    // Flatten connectionConfig if present, only include defined values
    let requestData: any = {};
    
    // Copy non-connectionConfig fields
    Object.keys(updates).forEach(key => {
      if (key !== 'connectionConfig') {
        requestData[key] = (updates as any)[key];
      }
    });
    
    // Flatten connectionConfig if present
    if (updates.connectionConfig) {
      requestData.endpoint = updates.connectionConfig.endpoint;
      
      if (updates.connectionConfig.timeout !== undefined) {
        requestData.timeout = updates.connectionConfig.timeout;
      }
      if (updates.connectionConfig.retries !== undefined) {
        requestData.retries = updates.connectionConfig.retries;
      }
      if (updates.connectionConfig.authentication !== undefined) {
        requestData.authentication = updates.connectionConfig.authentication;
      }
      if (updates.connectionConfig.customHeaders !== undefined) {
        requestData.customHeaders = updates.connectionConfig.customHeaders;
      }
    }
    
    const response = await this.client.put<ApplicationProfile>(
      `/api/application-profiles/${id}`,
      requestData
    );
    return response.data;
  }

  async deleteApplicationProfile(id: string): Promise<void> {
    await this.client.delete(`/api/application-profiles/${id}`);
  }

  // Dataset operations (tenant-scoped)
  async createDataset(data: { name: string; description: string }): Promise<Dataset> {
    const response = await this.client.post<Dataset>('/api/datasets', data);
    return response.data;
  }

  async createDatasetWithFile(formData: FormData): Promise<Dataset> {
    const response = await this.client.post<Dataset>('/api/datasets', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async getDatasets(): Promise<Dataset[]> {
    const response = await this.client.get<Dataset[]>('/api/datasets');
    return response.data;
  }

  async getDataset(id: string): Promise<Dataset> {
    const response = await this.client.get<Dataset>(`/api/datasets/${id}`);
    return response.data;
  }

  async downloadDatasetFile(id: string): Promise<Blob> {
    const response = await this.client.get(`/api/datasets/${id}/file`, {
      responseType: 'blob',
    });
    return response.data;
  }

  async updateDataset(id: string, updates: Partial<Dataset>): Promise<Dataset> {
    const response = await this.client.put<Dataset>(`/api/datasets/${id}`, updates);
    return response.data;
  }

  async deleteDataset(id: string): Promise<void> {
    await this.client.delete(`/api/datasets/${id}`);
  }

  // Test case operations
  async addTestCase(datasetId: string, testCase: Omit<TestCase, 'id'>): Promise<TestCase> {
    const response = await this.client.post<TestCase>(
      `/api/datasets/${datasetId}/test-cases`,
      testCase
    );
    return response.data;
  }

  async updateTestCase(
    datasetId: string,
    testCaseId: string,
    updates: Partial<TestCase>
  ): Promise<TestCase> {
    const response = await this.client.put<TestCase>(
      `/api/datasets/${datasetId}/test-cases/${testCaseId}`,
      updates
    );
    return response.data;
  }

  async deleteTestCase(datasetId: string, testCaseId: string): Promise<void> {
    await this.client.delete(`/api/datasets/${datasetId}/test-cases/${testCaseId}`);
  }

  // Evaluation operations (tenant-scoped)
  async startEvaluationRun(data: {
    datasetId: string;
    applicationProfileId: string;
  }): Promise<EvaluationRun> {
    const response = await this.client.post<EvaluationRun>('/api/evaluations', data);
    return response.data;
  }

  async getEvaluationRuns(): Promise<EvaluationRun[]> {
    const response = await this.client.get<EvaluationRun[]>('/api/evaluations');
    return response.data;
  }

  async getEvaluationRun(id: string): Promise<EvaluationRun> {
    const response = await this.client.get<EvaluationRun>(`/api/evaluations/${id}`);
    return response.data;
  }

  async compareRuns(runIds: string[]): Promise<any> {
    const response = await this.client.post('/api/evaluations/compare', { runIds });
    return response.data;
  }

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get<{ status: string }>('/api/health');
    return response.data;
  }
}

export const apiClient = new APIClient();
export default apiClient;
