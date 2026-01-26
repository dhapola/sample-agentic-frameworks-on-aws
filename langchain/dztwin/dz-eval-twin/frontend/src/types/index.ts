// Core data types matching backend models

export interface Customer {
  id: string;
  name: string;
  contactEmail: string;
  contactPhone?: string;
  configuration?: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

export interface ConnectionConfig {
  endpoint: string;
  authentication?: Record<string, any>;
  timeout?: number;
  retries?: number;
  customHeaders?: Record<string, string>;
}

export interface ApplicationProfile {
  id: string;
  customerId: string;
  name: string;
  type: string;
  connectionConfig: ConnectionConfig;
  createdAt: string;
  updatedAt: string;
}

export interface TestCase {
  id: string;
  input: string;
  expectedOutput?: string;
  metadata?: Record<string, any>;
}

export interface Dataset {
  id: string;
  customerId: string;
  name: string;
  description: string;
  testCases: TestCase[];
  createdAt: string;
  updatedAt: string;
}

export interface IndividualMetrics {
  accuracy?: number;
  relevance?: number;
}

export interface Response {
  testCaseId: string;
  input: string;
  output: string;
  latency: number;
  timestamp: string;
  error?: string;
  individualMetrics?: IndividualMetrics;
}

export interface AggregatedMetrics {
  averageAccuracy: number;
  averageRelevance: number;
  averageLatency: number;
  medianLatency: number;
  p95Latency: number;
  successRate: number;
  totalTestCases: number;
  failedTestCases: number;
}

export interface EvaluationRun {
  id: string;
  customerId: string;
  datasetId: string;
  applicationProfileId: string;
  status: string;
  startTime: string;
  endTime?: string;
  responses: Response[];
  metrics?: AggregatedMetrics;
}
