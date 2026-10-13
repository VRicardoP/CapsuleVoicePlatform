import React, { type ReactNode } from 'react';
import { useAnimatedValue } from '../../hooks/useAnimatedValue';

type MetricColor = 'blue' | 'green' | 'orange' | 'purple' | 'pink' | 'cyan';

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: string;
  changeLabel?: string;
  icon: ReactNode;
  color?: MetricColor;
}

const hoverClasses: Record<MetricColor, string> = {
  blue: 'hover:border-blue-500',
  green: 'hover:border-green-500',
  orange: 'hover:border-orange-500',
  purple: 'hover:border-purple-500',
  pink: 'hover:border-pink-500',
  cyan: 'hover:border-cyan-500',
};

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  change,
  changeLabel,
  icon,
  color = 'blue'
}) => {
  const valueFade = useAnimatedValue(value);

  const colorClasses: Record<MetricColor, string> = {
    blue: 'from-blue-600 to-cyan-600',
    green: 'from-green-600 to-emerald-600',
    orange: 'from-orange-600 to-yellow-600',
    purple: 'from-purple-600 to-pink-600',
    pink: 'from-pink-600 to-rose-600',
    cyan: 'from-cyan-600 to-blue-600',
  };

  // Determine if change is positive, negative, or neutral
  const getChangeColor = (changeStr: string) => {
    if (changeStr.startsWith('+')) return 'text-green-400';
    if (changeStr.startsWith('-')) return 'text-red-400';
    return 'text-gray-400';
  };

  return (
    <div className={`bg-gray-800 border border-gray-700 rounded-xl p-6 ${hoverClasses[color]} transition`}>
      <div className="flex items-center justify-between mb-4">
        <div className={`w-12 h-12 bg-gradient-to-br ${colorClasses[color]} rounded-lg flex items-center justify-center text-2xl`}>
          {icon}
        </div>
        {change && (
          <div className="text-right">
            <span className={`text-sm font-semibold ${getChangeColor(change)}`}>{change}</span>
            {changeLabel && (
              <p className="text-xs text-gray-500">{changeLabel}</p>
            )}
          </div>
        )}
      </div>
      <h3 className="text-gray-400 text-sm mb-1">{title}</h3>
      <p className={`text-3xl font-bold text-white ${valueFade}`}>{value}</p>
    </div>
  );
};

export default MetricCard;
