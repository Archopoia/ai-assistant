import React, { useEffect, useState } from 'react';
import { nutritionAPI } from '../../services/api';
import { CalorieTrendChart } from '../charts/CalorieTrendChart';

export const ProgressChartsPage: React.FC = () => {
  const [weekly, setWeekly] = useState<Array<{ date: string; deficit_surplus_kcal: number }>>([]);
  const [monthly, setMonthly] = useState<Array<{ date: string; deficit_surplus_kcal: number }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [weeklyData, monthlyData] = await Promise.all([
          nutritionAPI.getTrends('weekly').catch(() => ({ points: [] })),
          nutritionAPI.getTrends('monthly').catch(() => ({ points: [] })),
        ]);
        setWeekly((weeklyData.points || []).map((p: any) => ({ date: p.date, deficit_surplus_kcal: p.deficit_surplus_kcal })));
        setMonthly((monthlyData.points || []).map((p: any) => ({ date: p.date, deficit_surplus_kcal: p.deficit_surplus_kcal })));
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return <div className="text-gray-600">Loading progress charts...</div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Progress Charts</h1>
      <p className="text-sm text-gray-600">
        Historical weekly and monthly trend lines for caloric deficit/surplus.
      </p>
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <CalorieTrendChart points={weekly} title="Weekly Caloric Deficit/Surplus" />
        <CalorieTrendChart points={monthly} title="Monthly Caloric Deficit/Surplus" />
      </div>
    </div>
  );
};
