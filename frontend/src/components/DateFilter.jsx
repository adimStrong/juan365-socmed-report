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

export default function DateFilter({ onDateChange, defaultDays = 0, minDate, maxDate }) {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [activePreset, setActivePreset] = useState(defaultDays);

  // Check if a preset would have data
  const presetHasData = (days) => {
    if (!minDate || !maxDate) return true; // No boundaries, allow all
    if (days === 0) return true; // All Time always available

    const dataMinDate = new Date(minDate);
    const dataMaxDate = new Date(maxDate);
    let presetStart, presetEnd;

    if (days === 'thisMonth') {
      const now = new Date();
      presetStart = new Date(now.getFullYear(), now.getMonth(), 1);
      presetEnd = new Date();
    } else if (days === 'lastMonth') {
      const now = new Date();
      presetStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      presetEnd = new Date(now.getFullYear(), now.getMonth(), 0);
    } else {
      presetEnd = new Date();
      presetStart = new Date();
      presetStart.setDate(presetStart.getDate() - days);
    }

    // Check if preset range overlaps with data range
    return presetStart <= dataMaxDate && presetEnd >= dataMinDate;
  };

  useEffect(() => {
    // Initialize with default - only apply if not "All Time" (which is the default initial state)
    if (defaultDays !== 0) {
      applyPreset(defaultDays);
    }
    // Don't call onDateChange for defaultDays=0, parent already has null/null state
  }, []);

  const applyPreset = (days) => {
    // Don't apply if no data for this preset
    if (!presetHasData(days)) return;

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
        {PRESETS.map((preset) => {
          const hasData = presetHasData(preset.days);
          return (
            <button
              key={preset.days}
              onClick={() => hasData && applyPreset(preset.days)}
              disabled={!hasData}
              className={`px-3 py-1 text-xs rounded-full transition ${
                !hasData
                  ? 'bg-gray-100 text-gray-300 cursor-not-allowed'
                  : activePreset === preset.days
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
              title={!hasData ? 'No data for this period' : ''}
            >
              {preset.label}
            </button>
          );
        })}
      </div>

      {/* Custom date range */}
      <div className="flex items-center gap-2 ml-2">
        <input
          type="date"
          value={startDate}
          min={minDate || undefined}
          max={maxDate || undefined}
          onChange={(e) => setStartDate(e.target.value)}
          className="px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-indigo-500"
        />
        <span className="text-gray-400">to</span>
        <input
          type="date"
          value={endDate}
          min={minDate || undefined}
          max={maxDate || undefined}
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

      {/* Data range indicator */}
      {minDate && maxDate && (
        <span className="text-xs text-gray-400 ml-2">
          Data: {minDate} to {maxDate}
        </span>
      )}
    </div>
  );
}
