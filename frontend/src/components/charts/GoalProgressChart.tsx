import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useHealthProfile } from '../../hooks/useHealthData';
import { analyticsAPI } from '../../services/api';
import { useEffect, useState } from 'react';
import { LoadingSpinner } from '../common/LoadingSpinner';

export const GoalProgressChart: React.FC = () => {
  const { profile } = useHealthProfile();
  const [proximity, setProximity] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProximity = async () => {
      try {
        const data = await analyticsAPI.getGoalProximity();
        setProximity(data);
      } catch (error) {
        console.error('Failed to load goal proximity:', error);
      } finally {
        setLoading(false);
      }
    };

    if (profile) {
      fetchProximity();
    }
  }, [profile]);

  if (loading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <LoadingSpinner />
      </div>
    );
  }

  if (!proximity || Object.keys(proximity).length === 0) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4">Goal Progress</h3>
        <p className="text-gray-600">No goals set yet.</p>
      </div>
    );
  }

  const chartData = Object.entries(proximity).map(([key, value]: [string, any]) => ({
    goal: key.charAt(0).toUpperCase() + key.slice(1),
    progress: value.progress_percentage || 0,
  }));

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Goal Progress</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="goal" />
          <YAxis domain={[0, 100]} />
          <Tooltip />
          <Legend />
          <Bar dataKey="progress" fill="#3B82F6" name="Progress %" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
