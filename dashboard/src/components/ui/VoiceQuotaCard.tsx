import React from 'react';
import type { VoiceDirectionStatus } from '../../services/api/voiceQuotaApi';

interface VoiceQuotaCardProps {
  direction: 'inbound' | 'outbound';
  status: VoiceDirectionStatus | null | undefined;
  loading?: boolean;
  accentColor?: string;
}

const DIRECTION_LABELS = {
  inbound: { title: 'Voz entrante', subtitle: 'Minutos usados este mes (llamadas AI)' },
  outbound: { title: 'Voz saliente', subtitle: 'Minutos usados este mes (campañas)' },
};

export const VoiceQuotaCard: React.FC<VoiceQuotaCardProps> = ({
  direction,
  status,
  loading = false,
  accentColor = 'orange',
}) => {
  const { title, subtitle } = DIRECTION_LABELS[direction];

  const accent = {
    bar: accentColor === 'orange' ? 'bg-orange-500' : 'bg-blue-500',
    barWarn: 'bg-yellow-500',
    barDanger: 'bg-red-500',
    text: accentColor === 'orange' ? 'text-orange-400' : 'text-blue-400',
    border: accentColor === 'orange' ? 'border-orange-500/30' : 'border-blue-500/30',
  };

  if (loading && !status) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 animate-pulse">
        <div className="h-3 bg-gray-700 rounded w-1/2 mb-3" />
        <div className="h-6 bg-gray-700 rounded w-1/3 mb-3" />
        <div className="h-2 bg-gray-700 rounded w-full" />
      </div>
    );
  }

  if (!status) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
        <p className="text-xs text-gray-400">{title}</p>
        <p className="text-sm text-gray-500 mt-2">Sin cuota configurada</p>
      </div>
    );
  }

  const hasLimit = status.limit_minutes !== null;
  const pct = hasLimit && status.limit_minutes! > 0
    ? Math.min(100, Math.round(((status.used_minutes + status.reserved_minutes) / status.limit_minutes!) * 100))
    : null;

  const barColor = pct === null
    ? accent.bar
    : pct >= 90 ? accent.barDanger
    : pct >= 70 ? accent.barWarn
    : accent.bar;

  return (
    <div className={`bg-gray-800 border border-gray-700 rounded-xl p-4 ${status.is_exceeded ? 'border-red-500/50' : ''}`}>
      <div className="flex items-start justify-between mb-1">
        <div>
          <p className="text-xs text-gray-400">{title}</p>
          <p className="text-[10px] text-gray-600 mt-0.5">{subtitle}</p>
        </div>
        {status.is_exceeded && (
          <span className="text-[10px] font-semibold bg-red-900/40 text-red-400 border border-red-500/30 px-2 py-0.5 rounded-full">
            LÍMITE
          </span>
        )}
      </div>

      <div className="mt-3 flex items-end gap-1">
        <span className={`text-2xl font-bold ${status.is_exceeded ? 'text-red-400' : accent.text}`}>
          {status.used_minutes.toLocaleString('es-ES')}
        </span>
        {hasLimit && (
          <span className="text-sm text-gray-500 mb-0.5">
            / {status.limit_minutes!.toLocaleString('es-ES')} min
          </span>
        )}
        {!hasLimit && (
          <span className="text-sm text-gray-500 mb-0.5">min</span>
        )}
      </div>

      {hasLimit && pct !== null && (
        <>
          <div className="mt-3 h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${barColor}`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-[10px] text-gray-500">{pct}% usado</span>
            <span className="text-[10px] text-gray-500">
              {status.remaining_minutes !== null
                ? `${status.remaining_minutes.toLocaleString('es-ES')} min restantes`
                : ''}
            </span>
          </div>
        </>
      )}

      {!hasLimit && (
        <p className="text-[10px] text-gray-600 mt-2">Sin límite mensual</p>
      )}

      {status.reserved_minutes > 0 && (
        <p className="text-[10px] text-gray-600 mt-1">
          {status.reserved_minutes} min en reserva (llamadas activas)
        </p>
      )}
    </div>
  );
};

export default VoiceQuotaCard;
