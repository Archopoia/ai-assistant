export const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || '/api';
export const FRONTEND_URL = (import.meta as any).env?.VITE_FRONTEND_URL || 'http://localhost:3000';

export const BMI_CLASSIFICATIONS = {
  underweight: { label: 'Underweight', color: '#3B82F6', min: 0, max: 18.5 },
  normal_weight: { label: 'Normal Weight', color: '#10B981', min: 18.5, max: 25 },
  overweight: { label: 'Overweight', color: '#F59E0B', min: 25, max: 30 },
  obese: { label: 'Obese', color: '#EF4444', min: 30, max: 100 }
};

export const ACTIVITY_LEVELS = [
  { value: 'sedentary', label: 'Sedentary' },
  { value: 'moderate', label: 'Moderate' },
  { value: 'active', label: 'Active' },
  { value: 'very_active', label: 'Very Active' }
];

export const WELLNESS_SCORE_COLORS = {
  excellent: '#10B981',
  good: '#3B82F6',
  fair: '#F59E0B',
  needs_attention: '#EF4444'
};

export const DIETARY_PREFERENCES = [
  'vegetarian',
  'vegan',
  'pescatarian',
  'keto',
  'paleo',
  'mediterranean',
  'low_carb',
  'high_protein',
  'dash',
  'gluten_free',
  'dairy_free',
  'halal',
  'kosher',
  'whole30',
  'plant_based'
];

export const ALLERGIES_INTOLERANCES = [
  'gluten',
  'dairy',
  'eggs',
  'nuts',
  'peanuts',
  'soy',
  'shellfish',
  'fish',
  'sesame',
  'lactose'
];

export const SHOPPING_CATEGORIES = [
  'produce',
  'protein',
  'dairy_and_alternatives',
  'grains_and_bakery',
  'spices_and_condiments',
  'frozen'
];
