import React from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface MacroBreakdownChartProps {
  protein: number;
  carbs: number;
  fats: number;
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B'];

export const MacroBreakdownChart: React.FC<MacroBreakdownChartProps> = ({ protein, carbs, fats }) => {
  const total = protein + carbs + fats;
  const data = [
    { name: 'Protein (g)', value: protein },
    { name: 'Carbs (g)', value: carbs },
    { name: 'Fats (g)', value: fats },
  ];

  return (
    <div className="bg-white p-6 rounded-lg shadow-md h-[320px]">
      <h3 className="text-lg font-semibold mb-4 text-gray-900">Macronutrient Breakdown</h3>
      {total <= 0 ? (
        <div className="h-[85%] flex items-center justify-center text-sm text-gray-600">
          Log meal nutrition from the Meal Planner ("Log Nutrition") to see the chart.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="85%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" outerRadius={95} innerRadius={45} label>
              {data.map((_, index) => (
                <Cell key={`macro-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};
