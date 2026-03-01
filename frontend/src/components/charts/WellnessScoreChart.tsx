import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useHealthMetrics } from '../../hooks/useHealthData';
import { format } from 'date-fns';
import { LoadingSpinner } from '../common/LoadingSpinner';

export const WellnessScoreChart: React.FC = () => {
  const { metrics, loading } = useHealthMetrics(30);

  if (loading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4">Wellness Score Evolution</h3>
        <LoadingSpinner />
      </div>
    );
  }

  const chartData = metrics
    .filter((m) => m.wellness_score)
    .map((m) => ({
      date: format(new Date(m.recorded_at), 'MMM dd'),
      score: m.wellness_score,
    }))
    .reverse();

  if (chartData.length === 0) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4">Wellness Score Evolution</h3>
        <p className="text-gray-600">No wellness score data available yet.</p>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Wellness Score Evolution</h3>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis domain={[0, 100]} />
          <Tooltip />
          <Legend />
          <Area
            type="monotone"
            dataKey="score"
            stroke="#10B981"
            fill="#10B981"
            fillOpacity={0.3}
            name="Wellness Score"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
