import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useHealthProfile } from '../../hooks/useHealthData';
import { healthProfileAPI } from '../../services/api';
import { useNavigate } from 'react-router-dom';
import { ACTIVITY_LEVELS, DIETARY_PREFERENCES, ALLERGIES_INTOLERANCES } from '../../utils/constants';

export const HealthProfileForm: React.FC = () => {
  const { profile, updateProfile } = useHealthProfile();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { register, handleSubmit, setValue } = useForm();

  useEffect(() => {
    if (profile) {
      Object.entries(profile).forEach(([key, value]) => {
        if (value !== null && value !== undefined) {
          setValue(key, value);
        }
      });
      if (profile.macronutrient_targets) {
        setValue('macro_protein', profile.macronutrient_targets.protein);
        setValue('macro_carbs', profile.macronutrient_targets.carbs);
        setValue('macro_fats', profile.macronutrient_targets.fats);
      }
      if (Array.isArray(profile.disliked_ingredients)) {
        setValue('disliked_ingredients', profile.disliked_ingredients.join(', '));
      }
      if (Array.isArray(profile.cuisine_preferences)) {
        setValue('cuisine_preferences', profile.cuisine_preferences.join(', '));
      }
      if (profile.privacy_settings?.data_collection_consent !== undefined) {
        setValue('privacy_settings.data_collection_consent', profile.privacy_settings.data_collection_consent);
      }
    }
  }, [profile, setValue]);

  const onSubmit = async (data: any) => {
    setError(null);
    setLoading(true);
    try {
      // Collect checkbox values properly
      const dietaryPrefs = Array.isArray(data.dietary_preferences) 
        ? data.dietary_preferences 
        : data.dietary_preferences 
          ? [data.dietary_preferences] 
          : [];
      
      const dietaryRestricts = Array.isArray(data.dietary_restrictions) 
        ? data.dietary_restrictions 
        : data.dietary_restrictions 
          ? [data.dietary_restrictions] 
          : [];
      const allergies = Array.isArray(data.allergies_intolerances)
        ? data.allergies_intolerances
        : data.allergies_intolerances
          ? [data.allergies_intolerances]
          : [];
      
      const initialAssessmentInput = data.initial_assessment ?? {};
      const fitnessGoalsInput = data.fitness_goals ?? {};
      const privacySettingsInput = data.privacy_settings ?? {};

      const exerciseTypes = Array.isArray(initialAssessmentInput.exercise_types)
        ? initialAssessmentInput.exercise_types
        : initialAssessmentInput.exercise_types
          ? [initialAssessmentInput.exercise_types]
          : [];
      
      // Structure nested data properly - only include non-empty values
      const formData: any = {};
      
      if (data.age) formData.age = data.age;
      if (data.gender) formData.gender = data.gender;
      if (data.height_cm) formData.height_cm = data.height_cm;
      if (data.weight_kg) formData.weight_kg = data.weight_kg;
      if (data.occupation_type) formData.occupation_type = data.occupation_type;
      if (data.activity_level) formData.activity_level = data.activity_level;
      
      // Build fitness_goals object only if it has values
      const fitnessGoals: any = {};
      if (fitnessGoalsInput.target_weight) fitnessGoals.target_weight = fitnessGoalsInput.target_weight;
      if (fitnessGoalsInput.target_activity_level) fitnessGoals.target_activity_level = fitnessGoalsInput.target_activity_level;
      if (Object.keys(fitnessGoals).length > 0) formData.fitness_goals = fitnessGoals;
      
      // Dietary preferences and restrictions as arrays (will be stored as JSON)
      if (dietaryPrefs.length > 0) formData.dietary_preferences = dietaryPrefs;
      if (dietaryRestricts.length > 0) formData.dietary_restrictions = dietaryRestricts;
      if (allergies.length > 0) formData.allergies_intolerances = allergies;
      if (data.disliked_ingredients) {
        formData.disliked_ingredients = String(data.disliked_ingredients).split(',').map((x) => x.trim().toLowerCase()).filter(Boolean);
      }
      if (data.cuisine_preferences) {
        formData.cuisine_preferences = String(data.cuisine_preferences).split(',').map((x) => x.trim()).filter(Boolean);
      }
      if (data.calorie_target_kcal !== undefined && data.calorie_target_kcal !== '') {
        formData.calorie_target_kcal = Number(data.calorie_target_kcal);
      }
      if (
        data.macro_protein !== undefined || data.macro_carbs !== undefined || data.macro_fats !== undefined
      ) {
        formData.macronutrient_targets = {
          protein: Number(data.macro_protein || 120),
          carbs: Number(data.macro_carbs || 220),
          fats: Number(data.macro_fats || 70),
        };
      }
      if (data.meals_per_day) formData.meals_per_day = Number(data.meals_per_day);
      if (data.timezone) formData.timezone = data.timezone;
      
      // Build initial_assessment object only if it has values
      const initialAssessment: any = {};
      if (initialAssessmentInput.weekly_activity_frequency !== undefined && initialAssessmentInput.weekly_activity_frequency !== '') {
        initialAssessment.weekly_activity_frequency = initialAssessmentInput.weekly_activity_frequency;
      }
      if (exerciseTypes.length > 0) initialAssessment.exercise_types = exerciseTypes;
      if (initialAssessmentInput.session_duration) initialAssessment.session_duration = initialAssessmentInput.session_duration;
      if (initialAssessmentInput.fitness_level) initialAssessment.fitness_level = initialAssessmentInput.fitness_level;
      if (initialAssessmentInput.exercise_environment) initialAssessment.exercise_environment = initialAssessmentInput.exercise_environment;
      if (initialAssessmentInput.time_preference) initialAssessment.time_preference = initialAssessmentInput.time_preference;
      if (initialAssessmentInput.endurance_minutes) initialAssessment.endurance_minutes = initialAssessmentInput.endurance_minutes;
      if (initialAssessmentInput.pushups_count) initialAssessment.pushups_count = initialAssessmentInput.pushups_count;
      if (initialAssessmentInput.squats_count) initialAssessment.squats_count = initialAssessmentInput.squats_count;
      if (Object.keys(initialAssessment).length > 0) formData.initial_assessment = initialAssessment;

      const privacySettings: any = {};
      if (privacySettingsInput.data_collection_consent !== undefined) {
        privacySettings.data_collection_consent = Boolean(privacySettingsInput.data_collection_consent);
      }
      if (profile?.privacy_settings?.data_sharing !== undefined) {
        privacySettings.data_sharing = profile.privacy_settings.data_sharing;
      }
      if (profile?.privacy_settings?.public_profile !== undefined) {
        privacySettings.public_profile = profile.privacy_settings.public_profile;
      }
      if (profile?.privacy_settings?.email_notifications !== undefined) {
        privacySettings.email_notifications = profile.privacy_settings.email_notifications;
      }
      if (Object.keys(privacySettings).length > 0) {
        formData.privacy_settings = privacySettings;
      }
      
      if (profile) {
        await updateProfile(formData);
      } else {
        await healthProfileAPI.createProfile(formData);
      }
      navigate('/dashboard');
    } catch (err: any) {
      console.error('Profile save error:', err);
      const errorDetail = err.response?.data?.detail;
      if (Array.isArray(errorDetail)) {
        // Pydantic validation errors
        setError(errorDetail.map((e: any) => `${e.loc?.join('.')}: ${e.msg}`).join(', '));
      } else {
        setError(errorDetail || err.message || 'Failed to save profile');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto mt-8 bg-white p-8 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6 text-gray-900">Health Profile</h2>

      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Basic Info */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Basic Information</h3>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Age</label>
              <input
                {...register('age', { valueAsNumber: true })}
                type="number"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white placeholder-gray-400"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Gender</label>
              <select {...register('gender')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white">
                <option value="">Select...</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Height (cm)</label>
              <input
                {...register('height_cm', { valueAsNumber: true })}
                type="number"
                step="0.1"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white placeholder-gray-400"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Weight (kg)</label>
              <input
                {...register('weight_kg', { valueAsNumber: true })}
                type="number"
                step="0.1"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white placeholder-gray-400"
              />
            </div>
          </div>
        </div>

        {/* Lifestyle */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Lifestyle</h3>
          
          <div>
            <label className="block text-sm font-medium text-gray-700">Activity Level</label>
            <select {...register('activity_level')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white">
              <option value="">Select...</option>
              {ACTIVITY_LEVELS.map((level) => (
                <option key={level.value} value={level.value}>
                  {level.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Occupation Type</label>
            <input
              {...register('occupation_type')}
              type="text"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white placeholder-gray-400"
            />
          </div>
        </div>

        {/* Dietary Preferences & Restrictions */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Dietary Preferences & Restrictions</h3>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Dietary Preferences</label>
            <div className="space-y-2">
              {DIETARY_PREFERENCES.map((pref) => (
                <label key={pref} className="flex items-center">
                  <input
                    type="checkbox"
                    {...register('dietary_preferences')}
                    value={pref}
                    className="mr-2"
                  />
                  <span className="capitalize text-gray-700">{pref.replace('_', ' ')}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Dietary Restrictions</label>
            <div className="space-y-2">
              {DIETARY_PREFERENCES.map((rest) => (
                <label key={rest} className="flex items-center">
                  <input
                    type="checkbox"
                    {...register('dietary_restrictions')}
                    value={rest}
                    className="mr-2"
                  />
                  <span className="capitalize text-gray-700">{rest.replace('_', ' ')}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Allergies and Intolerances</label>
            <div className="grid grid-cols-2 gap-2">
              {ALLERGIES_INTOLERANCES.map((item) => (
                <label key={item} className="flex items-center">
                  <input type="checkbox" {...register('allergies_intolerances')} value={item} className="mr-2" />
                  <span className="capitalize text-gray-700">{item.replace('_', ' ')}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Disliked Ingredients (comma separated)</label>
              <input {...register('disliked_ingredients')} type="text" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Cuisine Preferences (comma separated)</label>
              <input {...register('cuisine_preferences')} type="text" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white" />
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Calorie Target (kcal)</label>
              <input {...register('calorie_target_kcal', { valueAsNumber: true })} type="number" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Protein (g)</label>
              <input {...register('macro_protein', { valueAsNumber: true })} type="number" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Carbs (g)</label>
              <input {...register('macro_carbs', { valueAsNumber: true })} type="number" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Fats (g)</label>
              <input {...register('macro_fats', { valueAsNumber: true })} type="number" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Meals per Day</label>
              <input {...register('meals_per_day', { valueAsNumber: true })} type="number" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Timezone</label>
              <input {...register('timezone')} type="text" placeholder="Europe/Helsinki" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white" />
            </div>
          </div>
        </div>

        {/* Fitness Goals */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Fitness Goals</h3>
          
          <div>
            <label className="block text-sm font-medium text-gray-700">Target Weight (kg)</label>
            <input
              {...register('fitness_goals.target_weight', { valueAsNumber: true })}
              type="number"
              step="0.1"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white placeholder-gray-400"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Target Activity Level</label>
            <select {...register('fitness_goals.target_activity_level')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white">
              <option value="">Select...</option>
              {ACTIVITY_LEVELS.map((level) => (
                <option key={level.value} value={level.value}>
                  {level.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Initial Fitness Assessment */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Initial Fitness Assessment</h3>
          
          <div>
            <label className="block text-sm font-medium text-gray-700">Weekly Activity Frequency (days per week, 0-7)</label>
            <input
              {...register('initial_assessment.weekly_activity_frequency', { valueAsNumber: true, min: 0, max: 7 })}
              type="number"
              min="0"
              max="7"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white placeholder-gray-400"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Exercise Types</label>
            <div className="space-y-2">
              {['cardio', 'strength', 'flexibility', 'sports'].map((type) => (
                <label key={type} className="flex items-center">
                  <input
                    type="checkbox"
                    {...register('initial_assessment.exercise_types')}
                    value={type}
                    className="mr-2"
                  />
                  <span className="capitalize text-gray-700">{type}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Average Session Duration</label>
            <select {...register('initial_assessment.session_duration')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white">
              <option value="">Select...</option>
              <option value="15-30min">15-30 minutes</option>
              <option value="30-60min">30-60 minutes</option>
              <option value="60+min">60+ minutes</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Self-Assessed Fitness Level</label>
            <select {...register('initial_assessment.fitness_level')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white">
              <option value="">Select...</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Preferred Exercise Environment</label>
            <select {...register('initial_assessment.exercise_environment')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white">
              <option value="">Select...</option>
              <option value="home">Home</option>
              <option value="gym">Gym</option>
              <option value="outdoors">Outdoors</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Time of Day Preference</label>
            <select {...register('initial_assessment.time_preference')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white">
              <option value="">Select...</option>
              <option value="morning">Morning</option>
              <option value="afternoon">Afternoon</option>
              <option value="evening">Evening</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Current Endurance Level (minutes you can run/walk)</label>
            <input
              {...register('initial_assessment.endurance_minutes', { valueAsNumber: true })}
              type="number"
              min="0"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white placeholder-gray-400"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Pushups Count</label>
              <input
                {...register('initial_assessment.pushups_count', { valueAsNumber: true })}
                type="number"
                min="0"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white placeholder-gray-400"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Squats Count</label>
              <input
                {...register('initial_assessment.squats_count', { valueAsNumber: true })}
                type="number"
                min="0"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm text-gray-900 bg-white placeholder-gray-400"
              />
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Data Usage Consent</h3>
          <p className="text-sm text-gray-600">
            We collect health profile data (demographics, physical metrics, lifestyle, activity and goals) to
            calculate BMI, wellness scores, progress trends, and generate AI recommendations.
          </p>
          <label className="flex items-start">
            <input
              type="checkbox"
              {...register('privacy_settings.data_collection_consent', { required: true })}
              className="mr-2 mt-1"
            />
            <span className="text-sm text-gray-700">
              I explicitly approve collection and use of this health data for analytics and personalized insights.
            </span>
          </label>
        </div>

        <div className="flex justify-end space-x-4">
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md disabled:opacity-50"
          >
            {loading ? 'Saving...' : 'Save Profile'}
          </button>
        </div>
      </form>
    </div>
  );
};
