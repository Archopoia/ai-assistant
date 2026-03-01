import { useState, useEffect } from 'react';
import { healthProfileAPI, analyticsAPI, aiInsightsAPI } from '../services/api';
import type { HealthProfile, HealthMetrics, AIInsights } from '../types';

export const useHealthProfile = () => {
  const [profile, setProfile] = useState<HealthProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const data = await healthProfileAPI.getProfile();
        setProfile(data);
      } catch (err: any) {
        if (err.response?.status !== 404) {
          setError(err.message || 'Failed to load health profile');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, []);

  const updateProfile = async (data: Partial<HealthProfile>) => {
    try {
      const updated = await healthProfileAPI.updateProfile(data);
      setProfile(updated);
      return updated;
    } catch (err: any) {
      setError(err.message || 'Failed to update profile');
      throw err;
    }
  };

  return { profile, loading, error, updateProfile };
};

export const useHealthMetrics = (limit = 30) => {
  const [metrics, setMetrics] = useState<HealthMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const data = await analyticsAPI.getMetrics(limit);
        setMetrics(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load metrics');
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, [limit]);

  const recordMetric = async (data: Partial<HealthMetrics>) => {
    try {
      const newMetric = await analyticsAPI.recordMetrics(data);
      setMetrics((prev) => [newMetric, ...prev]);
      return newMetric;
    } catch (err: any) {
      setError(err.message || 'Failed to record metric');
      throw err;
    }
  };

  return { metrics, loading, error, recordMetric };
};

export const useAIInsights = (insightType?: string) => {
  const [insights, setInsights] = useState<AIInsights[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchInsights = async () => {
      try {
        const data = await aiInsightsAPI.getInsights(insightType);
        setInsights(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load insights');
      } finally {
        setLoading(false);
      }
    };

    fetchInsights();
  }, [insightType]);

  const generateInsight = async (type: string) => {
    try {
      setError(null);
      const newInsight = await aiInsightsAPI.generateInsight(type);
      setInsights((prev) => [newInsight, ...prev]);
      return newInsight;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to generate insight';
      setError(errorMessage);
      throw err;
    }
  };

  return { insights, loading, error, generateInsight };
};
