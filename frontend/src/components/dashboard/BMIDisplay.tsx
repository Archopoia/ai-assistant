import React from 'react';
import { BMI_CLASSIFICATIONS } from '../../utils/constants';

interface BMIDisplayProps {
  bmi: number;
  classification: string;
  weightKg: number;
  heightCm: number;
}

export const BMIDisplay: React.FC<BMIDisplayProps> = ({ bmi, classification, weightKg, heightCm }) => {
  const bmiInfo = BMI_CLASSIFICATIONS[classification as keyof typeof BMI_CLASSIFICATIONS] || BMI_CLASSIFICATIONS.normal_weight;
  
  const getBMIColor = () => {
    if (bmi < 18.5) return '#3B82F6';
    if (bmi < 25) return '#10B981';
    if (bmi < 30) return '#F59E0B';
    return '#EF4444';
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4 text-gray-900">BMI</h3>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-4xl font-bold" style={{ color: getBMIColor() }}>
            {bmi.toFixed(1)}
          </div>
          <div className="text-sm text-gray-600 mt-1">{bmiInfo.label}</div>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-600">Weight</div>
          <div className="text-lg font-semibold text-gray-900">{weightKg} kg</div>
          <div className="text-sm text-gray-600 mt-2">Height</div>
          <div className="text-lg font-semibold text-gray-900">{heightCm} cm</div>
        </div>
      </div>
      <div className="mt-4">
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="h-2 rounded-full transition-all"
            style={{
              width: `${Math.min(100, (bmi / 40) * 100)}%`,
              backgroundColor: getBMIColor(),
            }}
          ></div>
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>15</span>
          <span>25</span>
          <span>30</span>
          <span>40+</span>
        </div>
      </div>
    </div>
  );
};
