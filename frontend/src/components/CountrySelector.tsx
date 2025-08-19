import React from 'react';
import { Country } from '../types';

interface CountrySelectorProps {
  countries: Country[];
  selectedCountry: Country | null;
  onCountrySelect: (country: Country) => void;
  disabled?: boolean;
}

const CountrySelector: React.FC<CountrySelectorProps> = ({ 
  countries, 
  selectedCountry, 
  onCountrySelect, 
  disabled = false 
}) => {
  return (
    <div className="space-y-4">
      <label className="block text-sm font-medium text-gray-700">
        Select Target Country/Document
      </label>
      
      <select
        value={selectedCountry?.id || ''}
        onChange={(e) => {
          const country = countries.find(c => c.id === parseInt(e.target.value));
          if (country) onCountrySelect(country);
        }}
        disabled={disabled}
        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <option value="">Choose a country...</option>
        {countries.map((country) => (
          <option key={country.id} value={country.id}>
            {country.name} ({country.code})
          </option>
        ))}
      </select>
      
      {selectedCountry && (
        <div className="p-4 bg-gray-50 rounded-lg">
          <h4 className="font-medium text-gray-900 mb-2">Photo Specifications:</h4>
          <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
            <div>
              <span className="font-medium">Dimensions:</span>
              <br />
              {selectedCountry.photo_width} × {selectedCountry.photo_height} pixels
            </div>
            <div>
              <span className="font-medium">Face Height Ratio:</span>
              <br />
              {(selectedCountry.face_height_ratio * 100).toFixed(0)}% of total height
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CountrySelector;