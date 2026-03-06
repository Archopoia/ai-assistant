import React from 'react';
import type { NutritionDailySummary } from '../../types';

interface NutritionSummaryCardProps {
  summary: NutritionDailySummary | null;
}

const getStatusColor = (deficitSurplus: number) => {
  if (deficitSurplus < -500) return 'bg-red-100 text-red-700';
  if (deficitSurplus > 200) return 'bg-yellow-100 text-yellow-700';
  return 'bg-green-100 text-green-700';
};

const getProgressBarColor = (deficitSurplus: number) => {
  if (deficitSurplus > 200) return 'bg-yellow-500';
  if (deficitSurplus < -500) return 'bg-red-500';
  return 'bg-green-600';
};

export const NutritionSummaryCard: React.FC<NutritionSummaryCardProps> = ({ summary }) => {
  if (!summary) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">Daily Nutrition</h3>
        <p className="text-sm text-gray-600">No nutrition logs yet.</p>
      </div>
    );
  }

  const progress = Math.min(100, Math.max(0, (summary.calories_kcal / summary.calorie_target_kcal) * 100));
  const statusClass = getStatusColor(summary.deficit_surplus_kcal);
  const progressBarClass = getProgressBarColor(summary.deficit_surplus_kcal);
  const micronutrientEntries = Object.entries(summary.micronutrient_target_pct || {});

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4 text-gray-900">Daily Nutrition</h3>
      <div className="space-y-2 text-sm text-gray-700">
        <div>Calories: {summary.calories_kcal.toFixed(1)} / {summary.calorie_target_kcal.toFixed(1)} kcal</div>
        <div>Protein: {summary.protein_g.toFixed(1)}g ({summary.protein_target_pct.toFixed(0)}%)</div>
        <div>Carbs: {summary.carbs_g.toFixed(1)}g ({summary.carbs_target_pct.toFixed(0)}%)</div>
        <div>Fats: {summary.fats_g.toFixed(1)}g ({summary.fats_target_pct.toFixed(0)}%)</div>
      </div>
      <div className="mt-4">
        <div className="h-3 bg-gray-200 rounded">
          <div className={`h-3 rounded ${progressBarClass}`} style={{ width: `${progress}%` }} />
        </div>
      </div>
      <div className={`mt-3 px-2 py-1 rounded text-xs inline-block ${statusClass}`}>
        Deficit/Surplus: {summary.deficit_surplus_kcal.toFixed(1)} kcal
      </div>
      {micronutrientEntries.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Micronutrients vs recommended</h4>
          <div className="space-y-2">
            {micronutrientEntries.map(([key, pct]) => {
              const intake = Number(summary.micronutrients?.[key] || 0);
              const recommended = Number(summary.micronutrient_recommended?.[key] || 0);
              const width = Math.max(0, Math.min(100, Number(pct)));
              return (
                <div key={key} className="text-xs text-gray-700">
                  <div className="flex justify-between">
                    <span>{key.replace(/_/g, ' ')}</span>
                    <span>{intake.toFixed(2)} / {recommended.toFixed(2)}</span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded mt-1">
                    <div className="h-2 rounded bg-blue-500" style={{ width: `${width}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
