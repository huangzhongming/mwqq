import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { apiService } from './services/api';
import { Country, PhotoProcessingJob } from './types';
import FileUpload from './components/FileUpload';
import CountrySelector from './components/CountrySelector';
import ProcessingStatus from './components/ProcessingStatus';
import LanguageSwitch from './components/LanguageSwitch';

const App: React.FC = () => {
  const { t } = useTranslation();
  const [countries, setCountries] = useState<Country[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedCountry, setSelectedCountry] = useState<Country | null>(null);
  const [currentJob, setCurrentJob] = useState<PhotoProcessingJob | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [, setIsPolling] = useState(false);

  const loadCountries = useCallback(async () => {
    try {
      const countriesData = await apiService.getCountries();
      setCountries(countriesData);
    } catch (error) {
      console.error('Error loading countries:', error);
      setError(t('errors.loadCountriesFailed'));
    }
  }, [t]);

  useEffect(() => {
    loadCountries();
  }, [loadCountries]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (currentJob && (currentJob.status === 'pending' || currentJob.status === 'processing')) {
      setIsPolling(true);
      interval = setInterval(async () => {
        try {
          const updatedJob = await apiService.getJobStatus(currentJob.id);
          setCurrentJob(updatedJob);
          
          if (updatedJob.status === 'completed' || updatedJob.status === 'failed') {
            setIsPolling(false);
          }
        } catch (error) {
          console.error('Error polling job status:', error);
          setIsPolling(false);
        }
      }, 2000);
    }

    return () => {
      if (interval) clearInterval(interval);
      setIsPolling(false);
    };
  }, [currentJob]);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setError(null);
  };

  const handleCountrySelect = (country: Country) => {
    setSelectedCountry(country);
    setError(null);
  };

  const handleUpload = async () => {
    if (!selectedFile || !selectedCountry) {
      setError(t('errors.selectBoth'));
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const response = await apiService.uploadPhoto(selectedFile, selectedCountry.id);
      
      const job = await apiService.getJobStatus(response.job_id);
      setCurrentJob(job);
      
    } catch (error: any) {
      console.error('Upload error:', error);
      setError(error.response?.data?.error || t('errors.uploadFailed'));
    } finally {
      setIsUploading(false);
    }
  };

  const handleStartOver = () => {
    setCurrentJob(null);
    setSelectedFile(null);
    setSelectedCountry(null);
    setError(null);
  };

  const canUpload = selectedFile && selectedCountry && !isUploading && !currentJob;

  if (currentJob) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="container mx-auto px-4">
          <div className="text-center mb-8">
            <div className="flex justify-between items-center mb-4">
              <h1 className="text-3xl font-bold text-gray-900">{t('app.title')}</h1>
              <LanguageSwitch />
            </div>
          </div>
          <ProcessingStatus
            job={currentJob}
            onStartOver={handleStartOver}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4 max-w-2xl">
        <div className="text-center mb-8">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                {t('app.title')}
              </h1>
              <p className="text-gray-600">
                {t('app.subtitle')}
              </p>
            </div>
            <LanguageSwitch />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              </div>
            </div>
          )}

          <FileUpload
            onFileSelect={handleFileSelect}
            selectedFile={selectedFile}
            disabled={isUploading}
          />

          <CountrySelector
            countries={countries}
            selectedCountry={selectedCountry}
            onCountrySelect={handleCountrySelect}
            disabled={isUploading}
          />

          <button
            onClick={handleUpload}
            disabled={!canUpload}
            className="w-full bg-blue-600 text-white py-3 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {isUploading ? t('button.uploading') : t('button.generatePhoto')}
          </button>

          <div className="text-center text-sm text-gray-500">
            <p>{t('features.backgroundRemoval')}</p>
            <p>{t('features.faceDetection')}</p>
            <p>{t('features.countrySizing')}</p>
            <p>{t('features.highQuality')}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;