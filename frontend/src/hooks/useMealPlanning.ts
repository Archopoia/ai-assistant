import { useEffect, useState } from 'react';
import { mealPlanAPI, nutritionAPI, recipesAPI, shoppingListAPI } from '../services/api';
import type { MealPlan, NutritionDailySummary, Recipe, ShoppingList } from '../types';

export const useMealPlans = () => {
  const [plans, setPlans] = useState<MealPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await mealPlanAPI.list();
      setPlans(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load meal plans');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  return { plans, loading, error, refresh };
};

export const useRecipes = (query: Record<string, any>) => {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await recipesAPI.search(query);
        setRecipes(data);
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message || 'Failed to load recipes');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [JSON.stringify(query)]);

  return { recipes, loading, error, setRecipes };
};

export const useShoppingList = (planId?: number, mealId?: string) => {
  const [list, setList] = useState<ShoppingList | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    if (!planId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await shoppingListAPI.generate(planId, mealId);
      setList(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to generate shopping list');
    } finally {
      setLoading(false);
    }
  };

  const updateItem = async (name: string, quantity: number, excluded: boolean) => {
    if (!list) return;
    const updated = await shoppingListAPI.update(list.source, [{ name, quantity, excluded }]);
    setList(updated);
  };

  return { list, loading, error, generate, updateItem };
};

export const useNutritionSummary = () => {
  const [daily, setDaily] = useState<NutritionDailySummary | null>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [insights, setInsights] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      setLoading(true);
      const today = new Date().toISOString().slice(0, 10);
      const [dailyData, trendData, insightData] = await Promise.all([
        nutritionAPI.getDailySummary(today).catch(() => null),
        nutritionAPI.getTrends('weekly').catch(() => ({ points: [] })),
        nutritionAPI.getInsights().catch(() => null),
      ]);
      setDaily(dailyData);
      setTrends(trendData?.points || []);
      setInsights(insightData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  return { daily, trends, insights, loading, refresh };
};
