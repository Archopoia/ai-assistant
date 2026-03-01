import React, { useMemo, useState } from 'react';
import { useHealthProfile } from '../../hooks/useHealthData';
import { useMealPlans } from '../../hooks/useMealPlanning';
import { mealPlanAPI, nutritionAPI } from '../../services/api';
import { LoadingSpinner } from '../common/LoadingSpinner';
import type { MealPlan } from '../../types';

const nowIso = () => new Date().toISOString();
const todayIsoDate = () => new Date().toISOString().slice(0, 10);

export const MealPlanPage: React.FC = () => {
  const { profile, loading: profileLoading } = useHealthProfile();
  const { plans, loading: plansLoading, refresh } = useMealPlans();
  const [duration, setDuration] = useState<'daily' | 'weekly'>('weekly');
  const [selectedPlan, setSelectedPlan] = useState<MealPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const [regeneratingId, setRegeneratingId] = useState<string | 'all' | null>(null);
  const [swappingMealId, setSwappingMealId] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(false);

  const prefilledPreferences = useMemo(() => ({
    dietary_restrictions: (Array.isArray(profile?.dietary_restrictions) ? profile?.dietary_restrictions : []) || [],
    allergies_intolerances: profile?.allergies_intolerances || [],
    cuisine_preferences: profile?.cuisine_preferences || ['Mediterranean'],
    disliked_ingredients: profile?.disliked_ingredients || [],
    calorie_target: profile?.calorie_target_kcal || 2000,
    macronutrient_targets: profile?.macronutrient_targets || { protein: 120, carbs: 220, fats: 70 },
    meals_per_day: profile?.meals_per_day || 3,
    preferred_meal_times: profile?.meal_schedule || {
      breakfast: `${todayIsoDate()}T08:00:00Z`,
      lunch: `${todayIsoDate()}T12:30:00Z`,
      dinner: `${todayIsoDate()}T19:00:00Z`,
    },
    timezone: profile?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
  }), [profile]);

  const generatePlan = async () => {
    try {
      setWorking(true);
      setError(null);
      setSuccess(null);
      const generated = await mealPlanAPI.generate({
        user_preferences: prefilledPreferences,
        meal_plan_request: {
          duration,
          date: todayIsoDate(),
          version: '1.0',
          created_at: nowIso(),
        },
      });
      setSelectedPlan(generated);
      await refresh();
      setSuccess('Meal plan generated successfully.');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to generate meal plan');
    } finally {
      setWorking(false);
    }
  };

  const regenerate = async (mealId?: string) => {
    if (!selectedPlan) return;
    try {
      setError(null);
      setSuccess(null);
      setRegeneratingId(mealId || 'all');
      const updated = await mealPlanAPI.regenerate(selectedPlan.id, mealId);
      setSelectedPlan(updated);
      await refresh();
      setSuccess(mealId ? 'Meal regenerated successfully.' : 'Entire plan regenerated successfully.');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to regenerate plan');
    } finally {
      setRegeneratingId(null);
    }
  };

  const swap = async (sourceId: string, targetId: string) => {
    if (!selectedPlan) return;
    try {
      setError(null);
      setSuccess(null);
      setSwappingMealId(sourceId);
      const updated = await mealPlanAPI.swapMeals(selectedPlan.id, sourceId, targetId);
      setSelectedPlan(updated);
      await refresh();
      setSuccess('Meals reordered successfully.');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to reorder meals');
    } finally {
      setSwappingMealId(null);
    }
  };

  const restoreLatestVersion = async () => {
    if (!selectedPlan) return;
    try {
      setError(null);
      setSuccess(null);
      setRestoring(true);
      const versions = await mealPlanAPI.listVersions(selectedPlan.id);
      if (versions.length < 2) {
        setSuccess('No previous version available to restore.');
        return;
      }
      const restored = await mealPlanAPI.restoreVersion(selectedPlan.id, versions[1].id);
      setSelectedPlan(restored);
      await refresh();
      setSuccess('Previous meal plan version restored.');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to restore previous version');
    } finally {
      setRestoring(false);
    }
  };

  if (profileLoading || plansLoading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Meal Planner</h1>
      <div className="bg-white rounded-lg shadow-md p-6 space-y-4">
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-700">Duration</label>
          <select
            value={duration}
            onChange={(e) => setDuration(e.target.value as 'daily' | 'weekly')}
            className="border rounded p-2"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
          </select>
          <button
            onClick={generatePlan}
            disabled={working}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-70"
          >
            {working ? 'Generating...' : 'Generate Meal Plan'}
          </button>
        </div>
        <div className="text-sm text-gray-700">
          <strong>Calorie target:</strong> {prefilledPreferences.calorie_target} kcal &nbsp;|&nbsp;
          <strong>Meals/day:</strong> {prefilledPreferences.meals_per_day} &nbsp;|&nbsp;
          <strong>Timezone:</strong> {prefilledPreferences.timezone}
        </div>
        {error && <p className="text-red-600 text-sm">{error}</p>}
        {success && <p className="text-green-700 text-sm">{success}</p>}
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">Saved Meal Plans</h2>
        <div className="space-y-2">
          {plans.map((plan) => (
            <button
              key={plan.id}
              onClick={() => setSelectedPlan(plan)}
              className="w-full text-left p-3 border rounded hover:bg-gray-50"
            >
              {plan.duration.toUpperCase()} plan for {plan.target_date} (v{plan.version})
            </button>
          ))}
          {plans.length === 0 && <p className="text-sm text-gray-600">No plans yet.</p>}
        </div>
      </div>

      {selectedPlan && (
        <div className="bg-white rounded-lg shadow-md p-6 space-y-4">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => regenerate()}
              disabled={regeneratingId === 'all'}
              className="px-3 py-2 rounded bg-indigo-600 text-white disabled:opacity-70"
            >
              {regeneratingId === 'all' ? 'Regenerating...' : 'Regenerate Entire Plan'}
            </button>
            <button
              onClick={restoreLatestVersion}
              disabled={restoring}
              className="px-3 py-2 rounded bg-amber-600 text-white disabled:opacity-70"
            >
              {restoring ? 'Restoring...' : 'Restore Previous Version'}
            </button>
          </div>
          <p className="text-xs text-gray-600">
            Regenerate replaces suggestions with new options. Restore brings back the previous saved version.
          </p>
          <h2 className="text-xl font-semibold text-gray-900">
            Selected Plan #{selectedPlan.id} - v{selectedPlan.version}
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {selectedPlan.meals.map((meal) => (
              <div key={meal.id} className="border rounded p-4 space-y-2">
                <div className="flex justify-between">
                  <strong className="text-gray-900">{meal.name}</strong>
                  <span className="text-xs text-gray-600">{meal.meal_type}</span>
                </div>
                <p className="text-xs text-gray-500">{meal.scheduled_at}</p>
                <p className="text-sm text-gray-700">
                  {meal.nutrition?.calories ?? 0} kcal | P {meal.nutrition?.protein ?? 0}g | C {meal.nutrition?.carbs ?? 0}g | F {meal.nutrition?.fats ?? 0}g
                </p>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => regenerate(meal.id)}
                    disabled={regeneratingId === meal.id}
                    className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-700 disabled:opacity-70"
                  >
                    {regeneratingId === meal.id ? 'Regenerating...' : 'Replace This Meal'}
                  </button>
                  {selectedPlan.meals.length > 1 && (
                    <button
                      onClick={() => {
                        const currentIndex = selectedPlan.meals.findIndex((m) => m.id === meal.id);
                        const nextMeal = selectedPlan.meals[(currentIndex + 1) % selectedPlan.meals.length];
                        swap(meal.id, nextMeal.id);
                      }}
                      disabled={swappingMealId === meal.id}
                      className="text-xs px-2 py-1 rounded bg-green-50 text-green-700 disabled:opacity-70"
                    >
                      {swappingMealId === meal.id ? 'Swapping...' : 'Swap with Next Slot'}
                    </button>
                  )}
                  <button
                    onClick={async () => {
                      try {
                        setError(null);
                        setSuccess(null);
                        await nutritionAPI.createLog({
                          meal_plan_id: selectedPlan.id,
                          meal_label: meal.name,
                          logged_at: new Date().toISOString(),
                          calories_kcal: Number(meal.nutrition?.calories || 0),
                          protein_g: Number(meal.nutrition?.protein || 0),
                          carbs_g: Number(meal.nutrition?.carbs || 0),
                          fats_g: Number(meal.nutrition?.fats || 0),
                          micronutrients: meal.nutrition?.micronutrients || {},
                        });
                        setSuccess(`Logged nutrition for "${meal.name}".`);
                      } catch (err: any) {
                        setError(err.response?.data?.detail || err.message || 'Failed to log nutrition');
                      }
                    }}
                    className="text-xs px-2 py-1 rounded bg-purple-50 text-purple-700"
                  >
                    Log Nutrition
                  </button>
                </div>
                <p className="text-xs text-gray-500">Replace This Meal picks a new recipe for this slot. Swap only changes meal order.</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
