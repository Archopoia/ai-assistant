export interface User {
  id: number;
  email: string;
  email_verified: boolean;
  two_factor_enabled: boolean;
  created_at: string;
}

export interface HealthProfile {
  id: number;
  user_id: number;
  age?: number;
  gender?: string;
  height_cm?: number;
  weight_kg?: number;
  occupation_type?: string;
  activity_level?: string;
  dietary_preferences?: Record<string, any>;
  dietary_restrictions?: Record<string, any>;
  allergies_intolerances?: string[];
  disliked_ingredients?: string[];
  cuisine_preferences?: string[];
  calorie_target_kcal?: number;
  macronutrient_targets?: { protein: number; carbs: number; fats: number };
  meals_per_day?: number;
  meal_schedule?: Record<string, string>;
  timezone?: string;
  fitness_goals?: Record<string, any>;
  initial_assessment?: Record<string, any>;
  privacy_settings?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export interface HealthMetrics {
  id: number;
  user_id: number;
  recorded_at: string;
  weight_kg?: number;
  bmi?: number;
  wellness_score?: number;
  activity_frequency?: number;
  activity_duration?: string;
  goal_progress?: Record<string, any>;
}

export interface AIInsights {
  id: number;
  user_id: number;
  generated_at: string;
  insight_type: string;
  content: Record<string, any>;
  version?: string;
  context_snapshot?: Record<string, any>;
}

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
}

export interface RecipeIngredient {
  id: string;
  name: string;
  quantity: number;
  unit?: string;
}

export interface Recipe {
  id: string;
  title: string;
  cuisine: string;
  meal: string;
  servings: number;
  ingredients: RecipeIngredient[];
  summary: string;
  time: number;
  difficulty_level: string;
  dietary_tags: string[];
  source: string;
  img?: string;
  preparation: Array<{ step: string; description: string; ingredients: string[] }>;
  nutrition?: Record<string, any>;
  rating_avg?: number;
  rating_count?: number;
  moderation_status?: string;
  is_verified?: boolean;
}

export interface Meal {
  id: string;
  name: string;
  meal_type: string;
  scheduled_at: string;
  nutrition: Record<string, any>;
  recipe_id?: string;
  ingredients?: RecipeIngredient[];
}

export interface MealPlan {
  id: number;
  user_id: number;
  duration: 'daily' | 'weekly';
  target_date: string;
  timezone: string;
  version: string;
  meals: Meal[];
  alternatives?: Record<string, Meal[]>;
  strategy?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export interface ShoppingListItem {
  name: string;
  quantity: number;
  unit: string;
  category: string;
  excluded: boolean;
  used_in?: string[];
}

export interface ShoppingList {
  source: string;
  items: ShoppingListItem[];
}

export interface NutritionDailySummary {
  date: string;
  calories_kcal: number;
  protein_g: number;
  carbs_g: number;
  fats_g: number;
  calorie_target_kcal: number;
  deficit_surplus_kcal: number;
  protein_target_pct: number;
  carbs_target_pct: number;
  fats_target_pct: number;
  micronutrients: Record<string, number>;
  micronutrient_recommended: Record<string, number>;
  micronutrient_target_pct: Record<string, number>;
}
