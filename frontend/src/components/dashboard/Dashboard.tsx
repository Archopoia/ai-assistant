import React, { useEffect, useState } from 'react';
import { useHealthProfile } from '../../hooks/useHealthData';
import { analyticsAPI } from '../../services/api';
import { BMIDisplay } from './BMIDisplay';
import { WellnessScore } from './WellnessScore';
import { GoalProgress } from './GoalProgress';
import { AIInsights } from './AIInsights';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { WeightChart } from '../charts/WeightChart';
import { WellnessScoreChart } from '../charts/WellnessScoreChart';
import { ActivityHeatmap } from '../charts/ActivityHeatmap';
import { GoalProgressChart } from '../charts/GoalProgressChart';
import { NutritionSummaryCard } from './NutritionSummaryCard';
import { CalorieTrendChart } from '../charts/CalorieTrendChart';
import { MacroBreakdownChart } from '../charts/MacroBreakdownChart';
import { useNutritionSummary } from '../../hooks/useMealPlanning';

export const Dashboard: React.FC = () => {
  const { profile, loading: profileLoading } = useHealthProfile();
  const { daily: nutritionDaily, trends: nutritionTrends, insights: nutritionInsights } = useNutritionSummary();
  const [bmiData, setBmiData] = useState<any>(null);
  const [wellnessData, setWellnessData] = useState<any>(null);
  const [goalProximity, setGoalProximity] = useState<any>(null);
  const [weeklyProgress, setWeeklyProgress] = useState<any>(null);
  const [monthlyProgress, setMonthlyProgress] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [bmi, wellness, proximity, weekly, monthly] = await Promise.all([
          analyticsAPI.getBMI().catch(() => null),
          analyticsAPI.getWellnessScore().catch(() => null),
          analyticsAPI.getGoalProximity().catch(() => null),
          analyticsAPI.getWeeklyProgress().catch(() => null),
          analyticsAPI.getMonthlyProgress().catch(() => null),
        ]);
        setBmiData(bmi);
        setWellnessData(wellness);
        setGoalProximity(proximity);
        setWeeklyProgress(weekly);
        setMonthlyProgress(monthly);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    if (!profileLoading) {
      fetchDashboardData();
    }
  }, [profileLoading]);

  if (loading || profileLoading) {
    return <LoadingSpinner />;
  }

  if (!profile) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4 text-gray-900">Welcome!</h2>
        <p className="text-gray-600 mb-6">Please create your health profile to get started.</p>
        <a
          href="/profile"
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        >
          Create Profile
        </a>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {bmiData && (
          <BMIDisplay
            bmi={bmiData.bmi}
            classification={bmiData.classification}
            weightKg={bmiData.weight_kg}
            heightCm={bmiData.height_cm}
          />
        )}

        {wellnessData && (
          <WellnessScore score={wellnessData.wellness_score} />
        )}

        <GoalProgress
          goals={profile.fitness_goals}
          goalProximity={goalProximity}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <WeightChart />
        <WellnessScoreChart />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <NutritionSummaryCard summary={nutritionDaily} />
        <MacroBreakdownChart
          protein={Number(nutritionDaily?.protein_g || 0)}
          carbs={Number(nutritionDaily?.carbs_g || 0)}
          fats={Number(nutritionDaily?.fats_g || 0)}
        />
      </div>

      <CalorieTrendChart
        points={nutritionTrends.map((point: any) => ({
          date: String(point.date).slice(5),
          deficit_surplus_kcal: Number(point.deficit_surplus_kcal || 0),
        }))}
        title="Weekly Caloric Deficit/Surplus"
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <GoalProgressChart />
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h3 className="text-lg font-semibold mb-4 text-gray-900">Weekly Progress</h3>
          {weeklyProgress ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Weight Change</span>
                <span className="font-medium text-gray-900">{weeklyProgress.weight_change_kg ?? 0} kg</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Wellness Change</span>
                <span className="font-medium text-gray-900">{weeklyProgress.wellness_change ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Trend</span>
                <span className="font-medium text-gray-900 capitalize">{weeklyProgress.trend || 'no_data'}</span>
              </div>
            </div>
          ) : (
            <p className="text-gray-600 text-sm">No weekly progress data yet.</p>
          )}
        </div>
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h3 className="text-lg font-semibold mb-4 text-gray-900">Monthly Progress</h3>
          {monthlyProgress ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Weight Change</span>
                <span className="font-medium text-gray-900">{monthlyProgress.weight_change_kg ?? 0} kg</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Wellness Change</span>
                <span className="font-medium text-gray-900">{monthlyProgress.wellness_change ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Trend</span>
                <span className="font-medium text-gray-900 capitalize">{monthlyProgress.trend || 'no_data'}</span>
              </div>
            </div>
          ) : (
            <p className="text-gray-600 text-sm">No monthly progress data yet.</p>
          )}
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">Current vs Target</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="p-3 border rounded">
            <div className="text-gray-600">Current Weight</div>
            <div className="text-xl font-semibold text-gray-900">{profile.weight_kg ?? '-'} kg</div>
          </div>
          <div className="p-3 border rounded">
            <div className="text-gray-600">Target Weight</div>
            <div className="text-xl font-semibold text-gray-900">{profile.fitness_goals?.target_weight ?? '-'} kg</div>
          </div>
          <div className="p-3 border rounded">
            <div className="text-gray-600">Current Activity</div>
            <div className="text-xl font-semibold text-gray-900">{profile.activity_level ?? '-'}</div>
          </div>
          <div className="p-3 border rounded">
            <div className="text-gray-600">Target Activity</div>
            <div className="text-xl font-semibold text-gray-900">{profile.fitness_goals?.target_activity_level ?? '-'}</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ActivityHeatmap />
        <AIInsights />
      </div>

      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">AI Nutrition Insights</h3>
        {nutritionInsights ? (
          <div className="space-y-3 text-sm text-gray-700">
            <div>
              <strong>Highlights:</strong> {(nutritionInsights.highlights || []).join(' ')}
            </div>
            <div>
              <strong>Concerns:</strong> {(nutritionInsights.concerns || []).join(' ')}
            </div>
            <div>
              <strong>Macro balance:</strong> {nutritionInsights.macronutrient_balance_analysis}
            </div>
          </div>
        ) : (
          <p className="text-gray-600 text-sm">Nutrition insights will appear once logs are available.</p>
        )}
      </div>
    </div>
  );
};
