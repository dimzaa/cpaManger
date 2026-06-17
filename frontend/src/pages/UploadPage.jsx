import React, { useState } from 'react';
import PageWrapper from '../components/layout/PageWrapper';
import { uploadAPI } from '../services/api';
import { Upload, Check, AlertCircle } from 'lucide-react';

export default function UploadPage() {
  const [month, setMonth] = useState(new Date().getFullYear() + '-' + String(new Date().getMonth() + 1).padStart(2, '0'));
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const handleDrag = (e) => {
    e.preventDefault();
    setDragActive(e.type.includes('enter'));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file?.name.endsWith('.zip')) {
      processFile(file);
    } else {
      setError('אנא בחר קבץ ZIP בלבד');
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file?.name.endsWith('.zip')) {
      processFile(file);
    } else {
      setError('אנא בחר קבץ ZIP בלבד');
    }
  };

  const processFile = async (file) => {
    setUploading(true);
    setError(null);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('month', month);

    try {
      const res = await uploadAPI.uploadFile(file, formData);
      setResults(res.data);
    } catch (err) {
      setError(err.response?.data?.message || 'שגיאה בהעלאה');
    } finally {
      setUploading(false);
    }
  };

  return (
    <PageWrapper title="העלאת קבצים">
      <div className="max-w-2xl space-y-6">
        {/* Month Selector */}
        <div className="bg-white p-6 rounded-lg border border-neutral-200">
          <label className="block text-sm font-medium text-neutral-700 mb-2">בחר חודש</label>
          <input 
            type="month" 
            value={month} 
            onChange={(e) => setMonth(e.target.value)}
            className="w-full border border-neutral-300 rounded px-4 py-2"
          />
        </div>

        {/* DropZone */}
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition ${
            dragActive ? 'border-primary-500 bg-primary-50' : 'border-neutral-300'
          }`}
        >
          {uploading ? (
            <>
              <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent mx-auto mb-4 rounded-full"></div>
              <p className="text-neutral-700 font-medium">מעלה קבץ...</p>
            </>
          ) : (
            <>
              <Upload className="w-12 h-12 text-neutral-400 mx-auto mb-4" />
              <p className="font-medium text-neutral-900 mb-1">גרור קבץ ZIP או לחץ כאן</p>
              <p className="text-sm text-neutral-500 mb-4">קבצי Excel בתוך תיקייה משרדית</p>
              <input
                type="file"
                accept=".zip"
                onChange={handleFileSelect}
                className="hidden"
                id="file-input"
              />
              <label htmlFor="file-input" className="inline-block bg-primary-500 text-white px-6 py-2 rounded font-medium cursor-pointer">
                בחר קבץ
              </label>
            </>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="p-4 bg-danger/10 border border-danger text-danger rounded-lg flex gap-3">
            <AlertCircle className="flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Results */}
        {results && (
          <div className="bg-white p-6 rounded-lg border border-neutral-200 space-y-4">
            <h3 className="font-hebrew font-bold text-lg">תוצאות העלאה</h3>
            {results.results?.map((result, i) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-neutral-50 rounded">
                {result.success ? (
                  <Check className="text-success flex-shrink-0 mt-1" />
                ) : (
                  <AlertCircle className="text-danger flex-shrink-0 mt-1" />
                )}
                <div>
                  <p className="font-medium">{result.municipality_name}</p>
                  {result.message && <p className="text-sm text-neutral-600">{result.message}</p>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </PageWrapper>
  );
}
