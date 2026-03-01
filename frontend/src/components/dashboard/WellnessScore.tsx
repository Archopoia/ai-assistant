import React from 'react';
import { WELLNESS_SCORE_COLORS } from '../../utils/constants';

interface WellnessScoreProps {
  score: number;
}

export const WellnessScore: React.FC<WellnessScoreProps> = ({ score }) => {
  const getScoreColor = () => {
    if (score >= 80) return WELLNESS_SCORE_COLORS.excellent;
    if (score >= 60) return WELLNESS_SCORE_COLORS.good;
    if (score >= 40) return WELLNESS_SCORE_COLORS.fair;
    return WELLNESS_SCORE_COLORS.needs_attention;
  };

  const getScoreLabel = () => {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Good';
    if (score >= 40) return 'Fair';
    return 'Needs Attention';
  };

  const circumference = 2 * Math.PI * 60;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4 text-gray-900">Wellness Score</h3>
      <div className="flex items-center justify-center">
        <div className="relative w-32 h-32">
          <svg className="transform -rotate-90 w-32 h-32">
            <circle
              cx="64"
              cy="64"
              r="60"
              stroke="#E5E7EB"
              strokeWidth="8"
              fill="none"
            />
            <circle
              cx="64"
              cy="64"
              r="60"
              stroke={getScoreColor()}
              strokeWidth="8"
              fill="none"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              className="transition-all duration-500"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-3xl font-bold" style={{ color: getScoreColor() }}>
                {Math.round(score)}
              </div>
              <div className="text-xs text-gray-600 mt-1">{getScoreLabel()}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
