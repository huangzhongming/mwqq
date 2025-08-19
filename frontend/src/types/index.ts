export interface Country {
  id: number;
  name: string;
  code: string;
  photo_width: number;
  photo_height: number;
  face_height_ratio: number;
}

export interface PhotoProcessingJob {
  id: string;
  country: Country;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message?: string;
  created_at: string;
  updated_at: string;
  processed_photo_url?: string;
}

export interface UploadResponse {
  job_id: string;
  status: string;
  message: string;
}