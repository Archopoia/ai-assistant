import React from 'react';

interface GoalProgressProps {
  goals?: Record<string, any>;
  goalProximity?: Record<string, any>;
}

export const GoalProgress: React.FC<GoalProgressProps> = ({ goals, goalProximity }) => {
  if (!goals && !goalProximity) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">Goal Progress</h3>
        <p className="text-gray-600">No goals set yet. Set your fitness goals in your profile.</p>
      </div>
    );
  }

  const weightGoal = goalProximity?.weight;
  const activityGoal = goalProximity?.activity;

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Goal Progress</h3>
      <div className="space-y-4">
        {weightGoal && (
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-sm font-medium text-gray-900">Weight Goal</span>
              <span className="text-sm text-gray-600">
                {weightGoal.progress_percentage.toFixed(0)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{ width: `${weightGoal.progress_percentage}%` }}
              ></div>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {weightGoal.difference_kg > 0 ? '+' : ''}
              {weightGoal.difference_kg.toFixed(1)} kg to target
            </div>
            {weightGoal.milestone && (
              <div className="text-xs text-blue-700 mt-1">
                Milestone: {weightGoal.milestone.current_percent}% (next {weightGoal.milestone.next_percent}%)
              </div>
            )}
          </div>
        )}

        {activityGoal && (
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-sm font-medium text-gray-900">Activity Goal</span>
              <span className="text-sm text-gray-600">
                {activityGoal.progress_percentage.toFixed(0)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-green-600 h-2 rounded-full transition-all"
                style={{ width: `${activityGoal.progress_percentage}%` }}
              ></div>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Current: {activityGoal.current_level} → Target: {activityGoal.target_level}
            </div>
            {activityGoal.milestone && (
              <div className="text-xs text-green-700 mt-1">
                Milestone step: {activityGoal.milestone.current_step} (next {activityGoal.milestone.next_step})
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
