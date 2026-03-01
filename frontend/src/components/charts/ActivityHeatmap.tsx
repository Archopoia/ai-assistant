import React from 'react';
import { useHealthMetrics } from '../../hooks/useHealthData';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { format, startOfWeek, getDay } from 'date-fns';

export const ActivityHeatmap: React.FC = () => {
  const { metrics, loading } = useHealthMetrics(30);

  if (loading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4">Activity Heatmap</h3>
        <LoadingSpinner />
      </div>
    );
  }

  // Group metrics by week
  const weeks: Record<string, number[]> = {};
  const today = new Date();
  const weekStart = startOfWeek(today, { weekStartsOn: 1 });

  for (let i = 0; i < 4; i++) {
    const weekDate = new Date(weekStart);
    weekDate.setDate(weekDate.getDate() - i * 7);
    const weekKey = format(weekDate, 'yyyy-MM-dd');
    weeks[weekKey] = [0, 0, 0, 0, 0, 0, 0];
  }

  metrics.forEach((metric) => {
    if (metric.activity_frequency) {
      const date = new Date(metric.recorded_at);
      const weekDate = startOfWeek(date, { weekStartsOn: 1 });
      const weekKey = format(weekDate, 'yyyy-MM-dd');
      const dayOfWeek = getDay(date) === 0 ? 6 : getDay(date) - 1;
      
      if (weeks[weekKey]) {
        weeks[weekKey][dayOfWeek] = Math.max(weeks[weekKey][dayOfWeek], metric.activity_frequency);
      }
    }
  });

  const getIntensityColor = (value: number) => {
    if (value === 0) return 'bg-gray-100';
    if (value <= 2) return 'bg-green-200';
    if (value <= 4) return 'bg-green-400';
    return 'bg-green-600';
  };

  const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Activity Heatmap</h3>
      <div className="space-y-2">
        {Object.entries(weeks).map(([weekKey, days]) => (
          <div key={weekKey} className="flex items-center space-x-2">
            <div className="text-xs text-gray-600 w-20">
              {format(new Date(weekKey), 'MMM dd')}
            </div>
            <div className="flex space-x-1">
              {days.map((value, dayIdx) => (
                <div
                  key={dayIdx}
                  className={`w-8 h-8 rounded ${getIntensityColor(value)} flex items-center justify-center text-xs`}
                  title={`${dayLabels[dayIdx]}: ${value} days`}
                >
                  {value > 0 ? value : ''}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex items-center space-x-4 text-xs text-gray-600">
        <div className="flex items-center space-x-1">
          <div className="w-4 h-4 bg-gray-100 rounded"></div>
          <span>Less</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-4 h-4 bg-green-600 rounded"></div>
          <span>More</span>
        </div>
      </div>
    </div>
  );
};
