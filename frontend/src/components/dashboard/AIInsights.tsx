import React, { useState } from 'react';
import { useAIInsights } from '../../hooks/useHealthData';
import { LoadingSpinner } from '../common/LoadingSpinner';

export const AIInsights: React.FC = () => {
  const { insights, loading, error, generateInsight } = useAIInsights();
  const [generating, setGenerating] = useState(false);
  const [selectedType, setSelectedType] = useState('recommendations');

  const handleGenerate = async (type: string) => {
    setGenerating(true);
    try {
      await generateInsight(type);
    } catch (err) {
      // Error handled by hook
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <LoadingSpinner />
      </div>
    );
  }

  const latestInsight = insights[0];

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">AI Insights</h3>
        <div className="flex items-center gap-2">
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="text-sm border border-gray-300 rounded px-2 py-1 text-gray-700"
          >
            <option value="recommendations">Recommendations</option>
            <option value="health_status">Health Status</option>
            <option value="progress_evaluation">Progress Evaluation</option>
            <option value="weekly_summary">Weekly Summary</option>
          </select>
          <button
            onClick={() => handleGenerate(selectedType)}
            disabled={generating}
            className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded disabled:opacity-50"
          >
            {generating ? 'Generating...' : 'Generate'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-400 text-yellow-800 rounded text-sm">
          <div className="font-semibold mb-1">AI Insights Unavailable</div>
          <div className="text-xs">
            {error.includes('quota') || error.includes('billing')
              ? "OpenAI API quota exceeded. Please check your billing at https://platform.openai.com/account/billing. The platform works normally for all other features."
              : error.includes('503') || error.includes('unavailable')
              ? "AI service is currently unavailable. Please try again later or check your OpenAI API key configuration."
              : error}
          </div>
        </div>
      )}

      {latestInsight ? (
        <div className="space-y-3">
          <div className="text-sm text-gray-600">
            {new Date(latestInsight.generated_at).toLocaleDateString()}
          </div>
          {latestInsight.content.recommendations && (
            <div className="space-y-2">
              {[...latestInsight.content.recommendations]
                .sort((a: any, b: any) => {
                  const priorities: Record<string, number> = { high: 0, medium: 1, low: 2 };
                  return (priorities[a.priority] ?? 3) - (priorities[b.priority] ?? 3);
                })
                .slice(0, 3)
                .map((rec: any, idx: number) => (
                <div key={idx} className="border-l-4 border-blue-500 pl-3">
                  <div className="flex items-center justify-between">
                    <div className="font-medium text-sm text-gray-900">{rec.title}</div>
                    {rec.priority && (
                      <span className="text-[10px] uppercase px-2 py-1 rounded bg-gray-100 text-gray-700">
                        {rec.priority}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-gray-600 mt-1">{rec.description}</div>
                  {Array.isArray(rec.actionable_steps) && rec.actionable_steps.length > 0 && (
                    <details className="mt-2">
                      <summary className="text-xs text-blue-700 cursor-pointer">View details</summary>
                      <ul className="mt-1 text-xs text-gray-600 list-disc list-inside">
                        {rec.actionable_steps.map((step: string, stepIdx: number) => (
                          <li key={stepIdx}>{step}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              ))}
            </div>
          )}
          {latestInsight.content.summary && (
            <p className="text-sm text-gray-700">{latestInsight.content.summary}</p>
          )}
        </div>
      ) : (
        <p className="text-gray-600 text-sm">
          No insights yet. Click "Generate" to get personalized recommendations.
        </p>
      )}
    </div>
  );
};
