import axios from 'axios';
import { Country, PhotoProcessingJob, UploadResponse, PrepareResponse, GenerateResponse, SelectionArea } from '../types';

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

  // Upload photo (original auto mode)
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

  // Prepare photo for manual selection (semi-auto mode)
  preparePhoto: async (photo: File, countryId: number): Promise<PrepareResponse> => {
    const formData = new FormData();
    formData.append('photo', photo);
    formData.append('country_id', countryId.toString());

    const response = await api.post('/prepare/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Generate final photo from selection
  generatePhoto: async (imageData: string, selection: SelectionArea, countryId: number): Promise<GenerateResponse> => {
    const response = await api.post('/generate/', {
      image_data: imageData,
      selection,
      country_id: countryId,
    });
    return response.data;
  },

  // Get job status
  getJobStatus: async (jobId: string): Promise<PhotoProcessingJob> => {
    const response = await api.get(`/job/${jobId}/`);
    return response.data;
  },
};