import { useState, useEffect, useCallback } from 'react';
import { getImports } from '../services/api';

const API_URL = 'http://localhost:8001/api';

export default function Imports() {
  const [imports, setImports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    fetchImports();
  }, []);

  async function fetchImports() {
    try {
      const data = await getImports();
      setImports(data.results || data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith('.csv')) {
        setFile(droppedFile);
        setError(null);
      } else {
        setError('Please upload a CSV file');
      }
    }
  }, []);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setUploading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_URL}/import/csv/`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        setResult(data);
        setFile(null);
        fetchImports(); // Refresh imports list
      } else {
        setError(data.error || 'Upload failed');
      }
    } catch (err) {
      setError(`Upload error: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const formatDate = (date) => {
    if (!date) return 'N/A';
    return new Date(date).toLocaleString();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Import Data</h1>
        <p className="text-sm text-gray-500 mt-1">
          Upload CSV exports from Meta Business Suite to update analytics data
        </p>
      </div>

      {/* Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-medium text-blue-800 mb-2">How to export from Meta Business Suite:</h3>
        <ol className="list-decimal list-inside text-sm text-blue-700 space-y-1">
          <li>Go to Meta Business Suite → Content → Posts</li>
          <li>Select date range and filter by page (if needed)</li>
          <li>Click "Export" button → Download CSV</li>
          <li>Upload the CSV file below</li>
        </ol>
      </div>

      {/* Upload Area */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragActive
            ? 'border-indigo-500 bg-indigo-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <div className="space-y-4">
          <div className="text-4xl">📊</div>
          <div>
            <p className="text-lg font-medium text-gray-700">
              {file ? file.name : 'Drop CSV file here or click to browse'}
            </p>
            {file && (
              <p className="text-sm text-gray-500 mt-1">
                Size: {(file.size / 1024).toFixed(1)} KB
              </p>
            )}
          </div>
          <input
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            className="hidden"
            id="csv-upload"
          />
          <label
            htmlFor="csv-upload"
            className="inline-block px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg cursor-pointer text-sm font-medium text-gray-700 transition-colors"
          >
            Choose File
          </label>
        </div>
      </div>

      {/* Upload Button */}
      <div className="flex justify-center">
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className={`px-6 py-3 rounded-lg font-medium text-white transition-colors ${
            !file || uploading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-indigo-600 hover:bg-indigo-700'
          }`}
        >
          {uploading ? (
            <span className="flex items-center gap-2">
              <span className="animate-spin">⏳</span>
              Importing...
            </span>
          ) : (
            'Import CSV Data'
          )}
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {/* Success Result */}
      {result && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <h3 className="font-medium text-green-800 mb-2">Import Successful!</h3>
          <div className="text-sm text-green-700 space-y-1">
            <p>Posts imported: <strong>{result.posts_imported}</strong></p>
            <p>Pages found: <strong>{result.pages_count}</strong></p>
            {result.pages && (
              <p>Pages: {result.pages.join(', ')}</p>
            )}
          </div>
        </div>
      )}

      {/* Import History */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">Import History</h2>
        </div>

        {loading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          </div>
        ) : imports.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No imports found. Upload a CSV file to get started.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left font-medium text-gray-500">Filename</th>
                <th className="px-6 py-3 text-left font-medium text-gray-500">Date</th>
                <th className="px-6 py-3 text-right font-medium text-gray-500">Imported</th>
                <th className="px-6 py-3 text-right font-medium text-gray-500">Updated</th>
                <th className="px-6 py-3 text-center font-medium text-gray-500">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {imports.map((imp) => (
                <tr key={imp.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <span className="font-medium">{imp.filename}</span>
                    {imp.date_range_start && (
                      <p className="text-xs text-gray-500">
                        {imp.date_range_start} - {imp.date_range_end}
                      </p>
                    )}
                  </td>
                  <td className="px-6 py-4 text-gray-500">
                    {formatDate(imp.import_date)}
                  </td>
                  <td className="px-6 py-4 text-right text-green-600 font-medium">
                    {imp.rows_imported}
                  </td>
                  <td className="px-6 py-4 text-right text-blue-600 font-medium">
                    {imp.rows_updated}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        imp.status === 'completed'
                          ? 'bg-green-100 text-green-700'
                          : imp.status === 'failed'
                          ? 'bg-red-100 text-red-700'
                          : 'bg-yellow-100 text-yellow-700'
                      }`}
                    >
                      {imp.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
