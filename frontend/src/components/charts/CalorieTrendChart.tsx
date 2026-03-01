import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

interface CalorieTrendChartProps {
  points: Array<{ date: string; deficit_surplus_kcal: number }>;
  title?: string;
}

export const CalorieTrendChart: React.FC<CalorieTrendChartProps> = ({ points, title = 'Calorie Deficit/Surplus Trend' }) => {
  return (
    <div className="bg-white p-6 rounded-lg shadow-md h-[320px]">
      <h3 className="text-lg font-semibold mb-4 text-gray-900">{title}</h3>
      <ResponsiveContainer width="100%" height="85%">
        <LineChart data={points}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="deficit_surplus_kcal" stroke="#2563EB" strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
