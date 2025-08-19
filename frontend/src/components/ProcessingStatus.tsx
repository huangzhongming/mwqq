import React from 'react';
import { PhotoProcessingJob } from '../types';

interface ProcessingStatusProps {
  job: PhotoProcessingJob;
  onDownload?: () => void;
  onStartOver?: () => void;
}

const ProcessingStatus: React.FC<ProcessingStatusProps> = ({ job, onDownload, onStartOver }) => {
  const getStatusIcon = () => {
    switch (job.status) {
      case 'pending':
        return (
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        );
      case 'processing':
        return (
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        );
      case 'completed':
        return (
          <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        );
      case 'failed':
        return (
          <div className="w-8 h-8 bg-red-500 rounded-full flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
        );
      default:
        return null;
    }
  };

  const getStatusMessage = () => {
    switch (job.status) {
      case 'pending':
        return 'Your photo is in the queue...';
      case 'processing':
        return 'Processing your passport photo...';
      case 'completed':
        return 'Your passport photo is ready!';
      case 'failed':
        return job.error_message || 'Processing failed. Please try again.';
      default:
        return 'Unknown status';
    }
  };

  const getStatusColor = () => {
    switch (job.status) {
      case 'pending':
      case 'processing':
        return 'text-blue-600';
      case 'completed':
        return 'text-green-600';
      case 'failed':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className="max-w-md mx-auto">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="text-center space-y-4">
          <div className="flex justify-center">
            {getStatusIcon()}
          </div>
          
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Processing Status
            </h3>
            <p className={`text-sm ${getStatusColor()}`}>
              {getStatusMessage()}
            </p>
          </div>

          {job.status === 'completed' && job.processed_photo_url && (
            <div className="space-y-4">
              <div className="border rounded-lg p-4 bg-gray-50">
                <img
                  src={job.processed_photo_url}
                  alt="Processed passport photo"
                  className="max-w-full h-auto mx-auto rounded"
                  style={{ maxHeight: '300px' }}
                />
              </div>
              
              <div className="flex space-x-3">
                <a
                  href={job.processed_photo_url}
                  download={`passport_photo_${job.country.code}.jpg`}
                  className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors text-center font-medium"
                  onClick={onDownload}
                >
                  Download Photo
                </a>
              </div>
            </div>
          )}

          <div className="pt-4 border-t border-gray-200">
            <div className="text-xs text-gray-500 space-y-1">
              <p>Country: {job.country.name}</p>
              <p>Dimensions: {job.country.photo_width} × {job.country.photo_height}px</p>
              <p>Started: {new Date(job.created_at).toLocaleString()}</p>
            </div>
          </div>

          {(job.status === 'completed' || job.status === 'failed') && (
            <button
              onClick={onStartOver}
              className="w-full bg-gray-100 text-gray-700 py-2 px-4 rounded-md hover:bg-gray-200 transition-colors font-medium"
            >
              Create Another Photo
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProcessingStatus;