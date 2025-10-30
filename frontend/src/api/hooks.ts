import { useQuery, useMutation, UseQueryOptions, UseMutationOptions } from '@tanstack/react-query';
import apiClient from './client';
import type {
  HealthResponse,
  SchemaInfo,
  NL2IRRequest,
  NL2IRResponse,
  IR2SQLRequest,
  IR2SQLResponse,
  NL2SQLRequest,
  NL2SQLResponse,
  EmbeddingUploadPayload,
  EmbeddingUploadResponse,
} from './types';

// Health
export const useHealth = (options?: UseQueryOptions<HealthResponse>) => {
  return useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: async () => {
      const { data } = await apiClient.get<HealthResponse>('/health/detailed');
      return data;
    },
    ...options,
  });
};

// Schema
export const useSchema = (database: string = 'nl2sql_target', options?: UseQueryOptions<SchemaInfo>) => {
  return useQuery<SchemaInfo>({
    queryKey: ['schema', database],
    queryFn: async () => {
      const { data } = await apiClient.get<SchemaInfo>(`/api/v1/schema?database=${database}`);
      return data;
    },
    ...options,
  });
};

export const useRefreshSchema = (options?: UseMutationOptions<any, Error, string>) => {
  return useMutation({
    mutationFn: async (database: string) => {
      const { data } = await apiClient.post(`/api/v1/schema/refresh?database=${database}`);
      return data;
    },
    ...options,
  });
};

// NL2IR
export const useNL2IR = (options?: UseMutationOptions<NL2IRResponse, Error, NL2IRRequest>) => {
  return useMutation({
    mutationFn: async (request: NL2IRRequest) => {
      const { data } = await apiClient.post<NL2IRResponse>('/api/v1/nl2ir', request);
      return data;
    },
    ...options,
  });
};

// IR2SQL
export const useIR2SQL = (options?: UseMutationOptions<IR2SQLResponse, Error, IR2SQLRequest>) => {
  return useMutation({
    mutationFn: async (request: IR2SQLRequest) => {
      const { data } = await apiClient.post<IR2SQLResponse>('/api/v1/ir2sql', request);
      return data;
    },
    ...options,
  });
};

// NL2SQL
export const useNL2SQL = (options?: UseMutationOptions<NL2SQLResponse, Error, NL2SQLRequest>) => {
  return useMutation({
    mutationFn: async (request: NL2SQLRequest) => {
      const { data } = await apiClient.post<NL2SQLResponse>('/api/v1/nl2sql', request);
      return data;
    },
    ...options,
  });
};

// Embeddings
export const useUploadEmbeddings = (options?: UseMutationOptions<EmbeddingUploadResponse, Error, EmbeddingUploadPayload>) => {
  return useMutation({
    mutationFn: async (payload: EmbeddingUploadPayload) => {
      const { data } = await apiClient.post<EmbeddingUploadResponse>('/api/v1/schema/embeddings/upload', payload);
      return data;
    },
    ...options,
  });
};
