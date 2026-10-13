import React, { useState, useRef, useEffect } from 'react';
import type { CallRecord, ActionType } from '../../types';
import { useCallDetails } from '../../hooks/useCallDetails';
import { useDashboard } from '../../context/DashboardContext';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';

interface CallDetailModalProps {
  call: CallRecord | null;
  onClose: () => void;
}

// Componente de reproductor de audio funcional
const AudioPlayer: React.FC<{ src: string; duration: string; consentId: string }> = ({ src, duration, consentId }) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleLoadedMetadata = () => {
      setAudioDuration(audio.duration);
      setIsLoading(false);
    };

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };

    const handleError = () => {
      setError('Error al cargar el audio');
      setIsLoading(false);
    };

    const handleCanPlay = () => {
      setIsLoading(false);
    };

    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);
    audio.addEventListener('canplay', handleCanPlay);

    return () => {
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
      audio.removeEventListener('canplay', handleCanPlay);
    };
  }, []);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    if (!audio) return;

    const time = parseFloat(e.target.value);
    audio.currentTime = time;
    setCurrentTime(time);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    if (!audio) return;

    const vol = parseFloat(e.target.value);
    audio.volume = vol;
    setVolume(vol);
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const progress = audioDuration > 0 ? (currentTime / audioDuration) * 100 : 0;

  if (error) {
    return (
      <div className="bg-gray-900 rounded-lg p-4">
        <div className="text-red-400 text-sm text-center py-4">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-lg p-4">
      <audio ref={audioRef} src={src} preload="metadata" />

      <div className="flex items-center space-x-4 mb-3">
        {/* Play/Pause Button */}
        <button
          onClick={togglePlay}
          disabled={isLoading}
          aria-label={isPlaying ? 'Pausar' : 'Reproducir'}
          className={`w-12 h-12 rounded-full flex items-center justify-center transition ${
            isLoading
              ? 'bg-gray-600 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {isLoading ? (
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : isPlaying ? (
            <span className="text-white text-lg">⏸</span>
          ) : (
            <span className="text-white text-lg">▶</span>
          )}
        </button>

        {/* Progress Bar */}
        <div className="flex-1">
          <input
            type="range"
            min="0"
            max={audioDuration || 100}
            value={currentTime}
            onChange={handleSeek}
            className="w-full h-2 bg-gray-700 rounded-full appearance-none cursor-pointer
                     [&::-webkit-slider-thumb]:appearance-none
                     [&::-webkit-slider-thumb]:w-4
                     [&::-webkit-slider-thumb]:h-4
                     [&::-webkit-slider-thumb]:bg-blue-500
                     [&::-webkit-slider-thumb]:rounded-full
                     [&::-webkit-slider-thumb]:cursor-pointer
                     [&::-moz-range-thumb]:w-4
                     [&::-moz-range-thumb]:h-4
                     [&::-moz-range-thumb]:bg-blue-500
                     [&::-moz-range-thumb]:rounded-full
                     [&::-moz-range-thumb]:cursor-pointer
                     [&::-moz-range-thumb]:border-0"
            style={{
              background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${progress}%, #374151 ${progress}%, #374151 100%)`
            }}
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>{formatTime(currentTime)}</span>
            <span>{audioDuration > 0 ? formatTime(audioDuration) : duration}</span>
          </div>
        </div>

        {/* Volume Control */}
        <div className="flex items-center space-x-2">
          <span className="text-gray-400">{volume === 0 ? '🔇' : volume < 0.5 ? '🔉' : '🔊'}</span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={volume}
            onChange={handleVolumeChange}
            className="w-20 h-1 bg-gray-700 rounded-full appearance-none cursor-pointer
                     [&::-webkit-slider-thumb]:appearance-none
                     [&::-webkit-slider-thumb]:w-3
                     [&::-webkit-slider-thumb]:h-3
                     [&::-webkit-slider-thumb]:bg-gray-400
                     [&::-webkit-slider-thumb]:rounded-full
                     [&::-webkit-slider-thumb]:cursor-pointer
                     [&::-moz-range-thumb]:w-3
                     [&::-moz-range-thumb]:h-3
                     [&::-moz-range-thumb]:bg-gray-400
                     [&::-moz-range-thumb]:rounded-full
                     [&::-moz-range-thumb]:cursor-pointer
                     [&::-moz-range-thumb]:border-0"
          />
        </div>
      </div>

      {/* Consent Badge */}
      <div className="flex items-center gap-2 text-xs text-green-400 bg-green-900/20 border border-green-500/30 rounded px-3 py-2">
        <span>✓</span>
        <span>Consentimiento de grabacion: {consentId}</span>
      </div>
    </div>
  );
};

const CallDetailModal: React.FC<CallDetailModalProps> = ({ call: initialCall, onClose }) => {
  const { call: fetchedCall, transcriptions, actions, loading, error } = useCallDetails(initialCall?.id || null);
  const { user } = useDashboard();

  if (!initialCall) return null;

  // Use fetched call data if available (has updated hasActiveConsent), fallback to initial
  const call = fetchedCall || initialCall;
  if (!call) return null;

  // RGPD: Validacion de consentimiento para acceso a datos
  const hasActiveConsent = call.hasActiveConsent ?? false;
  const canViewPII = user.role === 'admin' || user.role === 'user';
  const canViewRecording = call.recordingAvailable ?? false;

  // Filtrar transcripciones basadas en estado de consentimiento
  // Si la llamada tiene consentimiento activo, mostramos todas las transcripciones
  // Si la transcripción tiene su propio consentimiento, usamos ese
  const visibleTranscriptions = hasActiveConsent
    ? transcriptions.filter(t => {
        // Si tiene consentimiento individual, validarlo
        if (t.consentStatus === 'revoked' || t.consentStatus === 'expired') return false;
        return true;
      })
    : transcriptions.filter(t => {
        // Sin consentimiento de llamada, solo mostrar las que tengan consentimiento individual activo
        if (!t.consentId || t.consentStatus === 'none') return false;
        if (t.consentStatus === 'revoked' || t.consentStatus === 'expired') return false;
        return true;
      });

  const actionIcons: Record<ActionType, string> = {
    email: '📧',
    crm: '📊',
    calendar: '📅',
    whatsapp: '💬',
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-800 border border-gray-700 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-700 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-white">
              {canViewPII ? call.caller : '*** DATOS PROTEGIDOS ***'}
            </h2>
            <div className="flex items-center gap-3">
              <p className="text-gray-400">{call.date} - {call.time}</p>
              {call.direction && (
                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${
                  call.direction === 'outbound'
                    ? 'bg-purple-900/30 text-purple-400 border-purple-500/30'
                    : call.direction === 'internal'
                      ? 'bg-gray-900/30 text-gray-400 border-gray-500/30'
                      : 'bg-blue-900/30 text-blue-400 border-blue-500/30'
                }`}>
                  {call.direction === 'outbound' ? 'Saliente' : call.direction === 'internal' ? 'Interna' : 'Entrante'}
                </span>
              )}
            </div>
            {call.direction === 'outbound' && call.calledNumber && (
              <p className="text-gray-500 text-sm mt-1">Numero llamado: {call.calledNumber}</p>
            )}
            {!hasActiveConsent && (
              <div className="mt-2 px-3 py-1 bg-yellow-900/30 border border-yellow-500/30 rounded-lg text-yellow-400 text-sm flex items-center gap-2">
                <span>⚠️</span>
                <span>Consentimiento no activo - Datos limitados</span>
              </div>
            )}
          </div>
          <button onClick={onClose} aria-label="Cerrar" className="text-gray-400 hover:text-white text-2xl">×</button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <LoadingSpinner message="Cargando detalles de la llamada..." />
          ) : error ? (
            <ErrorMessage message={error} />
          ) : (
            <>
              {/* Transcripcion */}
              <div>
                <h3 className="text-xl font-bold text-white mb-4">📝 Transcripcion</h3>
                {!hasActiveConsent ? (
                  <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-6 text-center">
                    <div className="text-4xl mb-3">🔒</div>
                    <h4 className="text-red-400 font-semibold mb-2">Acceso Restringido</h4>
                    <p className="text-gray-400 text-sm">
                      No se puede mostrar la transcripcion porque el consentimiento del cliente no esta activo o ha sido revocado.
                    </p>
                    <p className="text-gray-500 text-xs mt-2">
                      Art. 6 y 7 RGPD - Procesamiento requiere consentimiento valido
                    </p>
                  </div>
                ) : visibleTranscriptions.length === 0 ? (
                  <div className="bg-gray-900 rounded-xl p-6 text-center text-gray-500">
                    No hay transcripciones disponibles con consentimiento valido
                  </div>
                ) : (
                  <div className="bg-gray-900 rounded-xl p-4 space-y-3 max-h-80 overflow-y-auto">
                    {visibleTranscriptions.map((t, idx) => (
                      <div key={idx} className={`flex ${t.speaker === 'assistant' ? 'justify-start' : 'justify-end'}`}>
                        <div className={`max-w-[80%] rounded-lg p-3 ${
                          t.speaker === 'assistant'
                            ? 'bg-blue-900/30 border border-blue-500/30'
                            : 'bg-gray-700'
                        }`}>
                          <div className="text-xs text-gray-400 mb-1 flex items-center gap-2">
                            <span>{t.speaker === 'assistant' ? '🤖 Asistente' : '👤 Cliente'} - {t.timestamp}</span>
                            {t.hasPii && (
                              <span className="px-2 py-0.5 bg-yellow-900/30 border border-yellow-500/30 text-yellow-400 rounded text-[10px]">
                                PII
                              </span>
                            )}
                            {t.consentStatus === 'active' && (
                              <span className="text-green-400 text-[10px]">✓</span>
                            )}
                          </div>
                          <p className="text-sm text-gray-200">{t.text}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Acciones Automatizadas */}
              <div>
                <h3 className="text-xl font-bold text-white mb-4">⚡ Acciones Automatizadas</h3>
                {actions.length === 0 ? (
                  <div className="bg-gray-900 rounded-xl p-6 text-center text-gray-500">
                    No hay acciones automatizadas para esta llamada
                  </div>
                ) : (
                  <div className="space-y-3">
                    {actions.map((action) => (
                      <div key={action.id} className="bg-gray-900 rounded-lg p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-4">
                            <span className="text-2xl">{actionIcons[action.type]}</span>
                            <div>
                              <p className="text-white font-medium">{action.description}</p>
                              <p className="text-xs text-gray-500">{action.timestamp}</p>
                            </div>
                          </div>
                          <span className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${
                            action.status === 'success' ? 'bg-green-900/30 text-green-400' :
                            action.status === 'pending' ? 'bg-yellow-900/30 text-yellow-400' :
                            'bg-red-900/30 text-red-400'
                          }`}>
                            {action.status === 'success' ? '✓ Completado' : action.status === 'pending' ? '⏳ Pendiente' : '✗ Fallido'}
                          </span>
                        </div>
                        {/* Booking details for agendar_cita */}
                        {action.details?.booking && (
                          <div className="mt-3 ml-12 bg-gray-800 rounded-lg p-3 border border-gray-700">
                            <div className="grid grid-cols-2 gap-2 text-sm">
                              {action.details.booking.servicio_nombre && (
                                <div>
                                  <span className="text-gray-500">Servicio: </span>
                                  <span className="text-gray-200">{action.details.booking.servicio_nombre}</span>
                                </div>
                              )}
                              {action.details.booking.fecha && (
                                <div>
                                  <span className="text-gray-500">Fecha: </span>
                                  <span className="text-gray-200">{action.details.booking.fecha}</span>
                                </div>
                              )}
                              {action.details.booking.hora && (
                                <div>
                                  <span className="text-gray-500">Hora: </span>
                                  <span className="text-gray-200">{action.details.booking.hora}</span>
                                </div>
                              )}
                              {action.details.booking.cliente_nombre && (
                                <div>
                                  <span className="text-gray-500">Cliente: </span>
                                  <span className="text-gray-200">{action.details.booking.cliente_nombre}</span>
                                </div>
                              )}
                              {action.details.booking.empleado_nombre && (
                                <div>
                                  <span className="text-gray-500">Empleada: </span>
                                  <span className="text-gray-200">{action.details.booking.empleado_nombre}</span>
                                </div>
                              )}
                              {action.details.cita_id && (
                                <div>
                                  <span className="text-gray-500">ID Koibox: </span>
                                  <span className="text-gray-200">#{action.details.cita_id}</span>
                                </div>
                              )}
                            </div>
                            {action.details.booking.cliente_nuevo && (
                              <div className="mt-2 text-xs text-blue-400">
                                Nuevo cliente registrado en Koibox
                              </div>
                            )}
                          </div>
                        )}
                        {/* Search details for buscar_servicio */}
                        {action.details?.tool_name === 'buscar_servicio' && !action.details?.booking && action.details?.tool_args?.nombre_servicio && (
                          <div className="mt-2 ml-12 text-xs text-gray-500">
                            Buscado: &quot;{action.details.tool_args.nombre_servicio}&quot;
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Audio Player */}
              <div>
                <h3 className="text-xl font-bold text-white mb-4">🎧 Grabacion</h3>
                {!canViewRecording ? (
                  <div className="bg-gray-900 rounded-xl p-6 text-center">
                    <div className="text-4xl mb-3">🎙️</div>
                    <h4 className="text-gray-400 font-semibold mb-2">Grabacion No Disponible</h4>
                    <p className="text-gray-500 text-sm">
                      No hay grabacion disponible para esta llamada. La grabacion puede haber expirado o no haberse procesado.
                    </p>
                  </div>
                ) : (
                  <>
                    <AudioPlayer
                      src={`/api/v1/calls/${call.id}/recording`}
                      duration={call.duration}
                      consentId={call.recordingConsentId || 'informed'}
                    />
                    <div className="flex items-center justify-between mt-3">
                      <a
                        href={`/api/v1/calls/${call.id}/recording/download`}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition"
                        download
                      >
                        Descargar grabacion
                      </a>
                      {call.recordingExpiresAt && (
                        <span className="text-xs text-yellow-400 bg-yellow-900/20 border border-yellow-500/30 rounded px-3 py-2">
                          Expira: {new Date(call.recordingExpiresAt).toLocaleDateString('es-ES')}
                        </span>
                      )}
                    </div>
                  </>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default CallDetailModal;
