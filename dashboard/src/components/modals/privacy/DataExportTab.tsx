import React from 'react';

/** Static legal information tab content */
const DataExportTab: React.FC = () => (
  <div className="space-y-4">
    <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
      <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
        <span>{'\ud83d\udcdc'}</span>
        <span>Informacion sobre el Tratamiento de Datos</span>
      </h3>

      <div className="space-y-4 text-sm text-gray-300">
        <div>
          <p className="font-semibold text-white mb-1">Responsable del Tratamiento:</p>
          <p>Capsule Corp - Asistente Virtual Inteligente</p>
          <p className="text-gray-500 text-xs">NIF: X0000000X</p>
        </div>

        <div>
          <p className="font-semibold text-white mb-1">Delegado de Proteccion de Datos (DPO):</p>
          <p>dpo@capsulecorp.example.com</p>
        </div>

        <div>
          <p className="font-semibold text-white mb-1">Finalidad del Tratamiento:</p>
          <ul className="list-disc list-inside space-y-1 text-gray-400">
            <li>Gestion de llamadas telefonicas automatizadas</li>
            <li>Transcripcion y analisis de conversaciones</li>
            <li>Generacion de estadisticas y metricas de rendimiento</li>
            <li>Mejora del servicio mediante analisis de sentimiento</li>
          </ul>
        </div>

        <div>
          <p className="font-semibold text-white mb-1">Base Legal:</p>
          <p className="text-gray-400">
            Consentimiento del interesado (Art. 6.1.a RGPD) y ejecucion de contrato (Art. 6.1.b RGPD)
          </p>
        </div>

        <div>
          <p className="font-semibold text-white mb-1">Plazo de Conservacion:</p>
          <p className="text-gray-400">
            Los datos se conservaran durante el tiempo necesario para cumplir con la finalidad para la que se recabaron
            y para determinar las posibles responsabilidades que se pudieran derivar de dicha finalidad y del tratamiento
            de los datos, ademas de los periodos establecidos en la normativa de archivos y documentacion.
          </p>
        </div>

        <div>
          <p className="font-semibold text-white mb-1">Derechos del Interesado:</p>
          <ul className="list-disc list-inside space-y-1 text-gray-400">
            <li>Derecho de acceso a tus datos personales</li>
            <li>Derecho de rectificacion de datos inexactos</li>
            <li>Derecho de supresion (&ldquo;derecho al olvido&rdquo;)</li>
            <li>Derecho de limitacion del tratamiento</li>
            <li>Derecho a la portabilidad de los datos</li>
            <li>Derecho de oposicion al tratamiento</li>
            <li>Derecho a no ser objeto de decisiones individuales automatizadas</li>
          </ul>
        </div>

        <div>
          <p className="font-semibold text-white mb-1">Reclamaciones:</p>
          <p className="text-gray-400">
            Tienes derecho a presentar una reclamacion ante la Agencia Espanola de Proteccion de Datos (www.aepd.es)
            si consideras que el tratamiento de tus datos personales no se ajusta a la normativa vigente.
          </p>
        </div>
      </div>
    </div>

    <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4 text-sm text-blue-300">
      <strong>Politica de Privacidad completa:</strong> Para mas informacion, consulta nuestra
      <a href="#" className="underline ml-1">Politica de Privacidad</a> y
      <a href="#" className="underline ml-1">Politica de Cookies</a>.
    </div>
  </div>
);

export default DataExportTab;
