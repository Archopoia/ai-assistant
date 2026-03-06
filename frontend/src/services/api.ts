import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';
import type {
  Token,
  User,
  HealthProfile,
  HealthMetrics,
  AIInsights,
  MealPlan,
  Recipe,
  ShoppingList,
  NutritionDailySummary,
} from '../types';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          
          const { access_token, refresh_token } = response.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', refresh_token);
          
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }
    }
    
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: async (email: string, password: string): Promise<User> => {
    const response = await api.post('/auth/register', { email, password });
    return response.data;
  },
  
  login: async (email: string, password: string): Promise<Token | { requires_2fa: boolean; email: string; message: string }> => {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
  },
  
  requestPasswordReset: async (email: string): Promise<void> => {
    await api.post('/auth/request-password-reset', { email });
  },
  
  resetPassword: async (token: string, newPassword: string): Promise<void> => {
    await api.post('/auth/reset-password', { token, new_password: newPassword });
  },
  
  verifyEmail: async (token: string): Promise<void> => {
    await api.get('/auth/verify-email', {
      params: { token },
    });
  },
  
  enable2FA: async (): Promise<{ secret: string; qr_code: string; message: string }> => {
    const response = await api.post('/auth/2fa/enable');
    return response.data;
  },
  
  verify2FA: async (code: string): Promise<{ message: string }> => {
    const response = await api.post('/auth/2fa/verify', { code });
    return response.data;
  },
  
  disable2FA: async (code?: string): Promise<{ message: string }> => {
    const response = await api.post('/auth/2fa/disable', { code });
    return response.data;
  },
  
  verify2FALogin: async (email: string, code: string): Promise<Token> => {
    const response = await api.post('/auth/2fa/verify-login', { email, code });
    return response.data;
  },
};

// User API
export const userAPI = {
  getCurrentUser: async (): Promise<User> => {
    const response = await api.get('/users/me');
    return response.data;
  },
  
  updateUser: async (data: Partial<User>): Promise<User> => {
    const response = await api.put('/users/me', data);
    return response.data;
  },
  
  exportData: async (): Promise<any> => {
    const response = await api.get('/users/me/export');
    return response.data;
  },
};

// Health Profile API
export const healthProfileAPI = {
  getProfile: async (): Promise<HealthProfile> => {
    const response = await api.get('/health-profile');
    return response.data;
  },
  
  createProfile: async (data: Partial<HealthProfile>): Promise<HealthProfile> => {
    const response = await api.post('/health-profile', data);
    return response.data;
  },
  
  updateProfile: async (data: Partial<HealthProfile>): Promise<HealthProfile> => {
    const response = await api.put('/health-profile', data);
    return response.data;
  },
  
  deleteProfile: async (): Promise<void> => {
    await api.delete('/health-profile');
  },
  
  getProfileHistory: async (): Promise<any> => {
    const response = await api.get('/health-profile/history');
    return response.data;
  },
};

// Analytics API
export const analyticsAPI = {
  recordMetrics: async (data: Partial<HealthMetrics>): Promise<HealthMetrics> => {
    const response = await api.post('/analytics/metrics', data);
    return response.data;
  },
  
  getMetrics: async (limit = 30): Promise<HealthMetrics[]> => {
    const response = await api.get('/analytics/metrics', {
      params: { limit },
    });
    return response.data;
  },
  
  getBMI: async (): Promise<{ bmi: number; classification: string; weight_kg: number; height_cm: number }> => {
    const response = await api.get('/analytics/bmi');
    return response.data;
  },
  
  getWellnessScore: async (): Promise<{ wellness_score: number; bmi: number; activity_level: string }> => {
    const response = await api.get('/analytics/wellness-score');
    return response.data;
  },
  
  getWeeklyProgress: async (): Promise<any> => {
    const response = await api.get('/analytics/progress/weekly');
    return response.data;
  },
  
  getMonthlyProgress: async (): Promise<any> => {
    const response = await api.get('/analytics/progress/monthly');
    return response.data;
  },
  
  getGoalProximity: async (): Promise<any> => {
    const response = await api.get('/analytics/goals/proximity');
    return response.data;
  },
};

// AI Insights API
export const aiInsightsAPI = {
  generateInsight: async (insightType: string): Promise<AIInsights> => {
    const response = await api.post(`/ai-insights/generate/${insightType}`);
    return response.data;
  },
  
  getInsights: async (insightType?: string, limit = 10): Promise<AIInsights[]> => {
    const response = await api.get('/ai-insights', {
      params: { insight_type: insightType, limit },
    });
    return response.data;
  },
  
  getLatestInsight: async (insightType?: string): Promise<AIInsights | null> => {
    const response = await api.get('/ai-insights/latest', {
      params: { insight_type: insightType },
    });
    return response.data;
  },
};

// Meal Plan API
export const mealPlanAPI = {
  generate: async (data: Record<string, any>): Promise<MealPlan> => {
    const response = await api.post('/meal-plans/generate', data);
    return response.data;
  },

  list: async (): Promise<MealPlan[]> => {
    const response = await api.get('/meal-plans');
    return response.data;
  },

  getById: async (planId: number): Promise<MealPlan> => {
    const response = await api.get(`/meal-plans/${planId}`);
    return response.data;
  },

  swapMeals: async (planId: number, sourceMealId: string, targetMealId: string): Promise<MealPlan> => {
    const response = await api.post(`/meal-plans/${planId}/swap`, {
      source_meal_id: sourceMealId,
      target_meal_id: targetMealId,
    });
    return response.data;
  },

  regenerate: async (planId: number, mealId?: string): Promise<MealPlan> => {
    const response = await api.post(`/meal-plans/${planId}/regenerate`, {
      meal_id: mealId,
      regenerate_all: !mealId,
    });
    return response.data;
  },

  manualAdd: async (planId: number, payload: Record<string, any>): Promise<MealPlan> => {
    const response = await api.post(`/meal-plans/${planId}/manual-add`, payload);
    return response.data;
  },

  replaceMeal: async (planId: number, mealId: string, replacementMeal: Record<string, any>): Promise<MealPlan> => {
    const response = await api.post(`/meal-plans/${planId}/replace`, {
      meal_id: mealId,
      replacement_meal: replacementMeal,
    });
    return response.data;
  },

  getAlternatives: async (planId: number, mealId: string): Promise<{ meal_id: string; alternatives: any[] }> => {
    const response = await api.get(`/meal-plans/${planId}/alternatives`, { params: { meal_id: mealId } });
    return response.data;
  },

  listVersions: async (planId: number): Promise<any[]> => {
    const response = await api.get(`/meal-plans/${planId}/versions`);
    return response.data;
  },

  restoreVersion: async (planId: number, versionId: number): Promise<MealPlan> => {
    const response = await api.post(`/meal-plans/${planId}/restore/${versionId}`);
    return response.data;
  },
};

// Recipes API
export const recipesAPI = {
  search: async (params: Record<string, any>): Promise<Recipe[]> => {
    const response = await api.get('/recipes', { params });
    return response.data;
  },

  getById: async (recipeId: string): Promise<Recipe> => {
    const response = await api.get(`/recipes/${recipeId}`);
    return response.data;
  },

  generate: async (payload: Record<string, any>): Promise<Recipe> => {
    const response = await api.post('/recipes/generate', payload);
    return response.data;
  },

  substitute: async (payload: Record<string, any>): Promise<any> => {
    const response = await api.post('/recipes/substitute', payload);
    return response.data;
  },

  adjustPortion: async (payload: Record<string, any>): Promise<any> => {
    const response = await api.post('/recipes/portion', payload);
    return response.data;
  },

  rate: async (recipeId: string, rating: number): Promise<any> => {
    const response = await api.post(`/recipes/${recipeId}/rate`, null, { params: { rating } });
    return response.data;
  },

  getVerifiedRecommendations: async (limit = 6): Promise<Recipe[]> => {
    const response = await api.get('/recipes/recommendations/verified', { params: { limit } });
    return response.data;
  },

  getModerationQueue: async (limit = 10): Promise<Recipe[]> => {
    const response = await api.get('/recipes/moderation/queue', { params: { limit } });
    return response.data;
  },

  moderate: async (recipeId: string, action: 'approve' | 'reject' | 'flag', note?: string): Promise<any> => {
    const response = await api.post(`/recipes/${recipeId}/moderate`, null, { params: { action, note } });
    return response.data;
  },
};

// Shopping List API
export const shoppingListAPI = {
  generate: async (planId: number, mealId?: string): Promise<ShoppingList> => {
    const response = await api.get('/shopping-list', { params: { plan_id: planId, meal_id: mealId } });
    return response.data;
  },

  update: async (source: string, items: Array<{ name: string; quantity: number; excluded: boolean }>): Promise<ShoppingList> => {
    const response = await api.put('/shopping-list', { items }, { params: { source } });
    return response.data;
  },
};

// Nutrition API
export const nutritionAPI = {
  createLog: async (payload: Record<string, any>): Promise<any> => {
    const response = await api.post('/nutrition/logs', payload);
    return response.data;
  },

  getLogs: async (days = 30): Promise<any[]> => {
    const response = await api.get('/nutrition/logs', { params: { days } });
    return response.data;
  },

  getDailySummary: async (targetDate: string): Promise<NutritionDailySummary> => {
    const response = await api.get('/nutrition/summary/daily', { params: { target_date: targetDate } });
    return response.data;
  },

  getWeeklySummary: async (endDate: string): Promise<any> => {
    const response = await api.get('/nutrition/summary/weekly', { params: { end_date: endDate } });
    return response.data;
  },

  getTrends: async (period: 'weekly' | 'monthly' = 'weekly'): Promise<any> => {
    const response = await api.get('/nutrition/trends', { params: { period } });
    return response.data;
  },

  getInsights: async (): Promise<any> => {
    const response = await api.get('/nutrition/insights');
    return response.data;
  },
};

export default api;
