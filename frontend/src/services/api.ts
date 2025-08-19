import axios from 'axios';
import { Country, PhotoProcessingJob, UploadResponse } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiService = {
  // Get all countries
  getCountries: async (): Promise<Country[]> => {
    const response = await api.get('/countries/');
    return response.data;
  },

  // Upload photo
  uploadPhoto: async (photo: File, countryId: number): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('photo', photo);
    formData.append('country_id', countryId.toString());

    const response = await api.post('/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Get job status
  getJobStatus: async (jobId: string): Promise<PhotoProcessingJob> => {
    const response = await api.get(`/job/${jobId}/`);
    return response.data;
  },
};