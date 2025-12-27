import { useState, useEffect } from 'react';

const PRESETS = [
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 60 days', days: 60 },
  { label: 'Last 90 days', days: 90 },
  { label: 'This Month', days: 'thisMonth' },
  { label: 'Last Month', days: 'lastMonth' },
  { label: 'All Time', days: 0 },
];

export default function DateFilter({ onDateChange, defaultDays = 0 }) {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [activePreset, setActivePreset] = useState(defaultDays);

  useEffect(() => {
    // Initialize with default
    if (defaultDays === 0) {
      onDateChange({ startDate: null, endDate: null });
    } else {
      applyPreset(defaultDays);
    }
  }, []);

  const applyPreset = (days) => {
    setActivePreset(days);
    if (days === 0) {
      setStartDate('');
      setEndDate('');
      onDateChange({ startDate: null, endDate: null });
    } else if (days === 'thisMonth') {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth(), 1);
      const end = new Date();
      const startStr = start.toISOString().split('T')[0];
      const endStr = end.toISOString().split('T')[0];
      setStartDate(startStr);
      setEndDate(endStr);
      onDateChange({ startDate: startStr, endDate: endStr });
    } else if (days === 'lastMonth') {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      const end = new Date(now.getFullYear(), now.getMonth(), 0); // Last day of previous month
      const startStr = start.toISOString().split('T')[0];
      const endStr = end.toISOString().split('T')[0];
      setStartDate(startStr);
      setEndDate(endStr);
      onDateChange({ startDate: startStr, endDate: endStr });
    } else {
      const end = new Date();
      const start = new Date(end);
      start.setDate(start.getDate() - days);

      const startStr = start.toISOString().split('T')[0];
      const endStr = end.toISOString().split('T')[0];

      setStartDate(startStr);
      setEndDate(endStr);
      onDateChange({ startDate: startStr, endDate: endStr });
    }
  };

  const handleCustomDate = () => {
    setActivePreset(null);
    if (startDate && endDate) {
      onDateChange({ startDate, endDate });
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Preset buttons */}
      <div className="flex flex-wrap gap-1">
        {PRESETS.map((preset) => (
          <button
            key={preset.days}
            onClick={() => applyPreset(preset.days)}
            className={`px-3 py-1 text-xs rounded-full transition ${
              activePreset === preset.days
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* Custom date range */}
      <div className="flex items-center gap-2 ml-2">
        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          className="px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-indigo-500"
        />
        <span className="text-gray-400">to</span>
        <input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          className="px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-indigo-500"
        />
        <button
          onClick={handleCustomDate}
          className="px-3 py-1 text-xs bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200"
        >
          Apply
        </button>
      </div>
    </div>
  );
}
