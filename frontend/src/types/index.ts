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

export interface SelectionArea {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface PrepareResponse {
  image_data: string;
  image_format: string;
  image_dimensions: {
    width: number;
    height: number;
  };
  face_bbox: [number, number, number, number];
  default_selection: SelectionArea;
  target_dimensions: {
    width: number;
    height: number;
  };
  country: {
    id: number;
    name: string;
    code: string;
  };
}

export interface GenerateResponse {
  job_id: string;
  status: string;
  message: string;
  file_size: number;
  dimensions: string;
}