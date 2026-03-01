import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import { useHealthMetrics, useHealthProfile } from '../../hooks/useHealthData';
import { format } from 'date-fns';
import { LoadingSpinner } from '../common/LoadingSpinner';

export const WeightChart: React.FC = () => {
  const { metrics, loading } = useHealthMetrics(30);
  const { profile } = useHealthProfile();

  if (loading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4">Weight Tracking</h3>
        <LoadingSpinner />
      </div>
    );
  }

  const chartData = metrics
    .filter((m) => m.weight_kg)
    .map((m) => ({
      date: format(new Date(m.recorded_at), 'MMM dd'),
      weight: m.weight_kg,
    }))
    .reverse();

  if (chartData.length === 0) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4">Weight Tracking</h3>
        <p className="text-gray-600">No weight data available yet.</p>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Weight Tracking</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="weight"
            stroke="#3B82F6"
            strokeWidth={2}
            name="Weight (kg)"
          />
          {profile?.fitness_goals?.target_weight && (
            <ReferenceLine
              y={profile.fitness_goals.target_weight}
              stroke="#EF4444"
              strokeDasharray="6 4"
              label="Goal Weight"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
