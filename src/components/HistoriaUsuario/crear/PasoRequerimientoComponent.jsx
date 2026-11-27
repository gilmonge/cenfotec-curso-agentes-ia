import React from 'react';
import { useAsistenteHistoria } from './AsistenteHistoriaContext';
import { AlertaComponent } from '../../Comun/AlertaComponent';
import { AreaTextoComponent } from '../../Comun/AreaTextoComponent';
import { BotonComponent } from '../../Comun/BotonComponent';
import { CampoTextoComponent } from '../../Comun/CampoTextoComponent';
import { MAX_AGENT_MESSAGE_CODEPOINTS } from '../../../utils/wizardAgent';
import { OPCION_AREA_SOLICITANTE, OPCION_SISTEMA, armarOpcion } from '../../../data/catalogos';
import { RotateCcw, Save, Sparkles } from 'lucide-react';
import { SelectorComponent } from '../../Comun/SelectorComponent';
import { TIPOS_SOLICITUD } from '../../../utils/plantillaHu';
import { TarjetaComponent } from '../../Comun/TarjetaComponent';
import { INFO_TYPE_OPTIONS } from './constantesAsistente';

// Vista de un paso del asistente. El estado y las acciones vienen del controlador (useCrearHistoria).
export const PasoRequerimientoComponent = () => {
  const {
    agentResponse,
    codigoHu,
    description,
    formError,
    handleAnalyzeRequirement,
    handleRestartAnalysis,
    handleSaveDraft,
    infoType,
    requestType,
    requester,
    requirementName,
    setCodigoHu,
    setDescription,
    setFormError,
    setInfoType,
    setRequestType,
    setRequester,
    setRequirementName,
    setSystem,
    system,
  } = useAsistenteHistoria();

  return (
    <TarjetaComponent title="Paso 1 — Definición del Requerimiento" subtitle="Ingrese la minuta, el correo o el incidente recibido de Negocio. El Agente Analista lo clasificará y generará preguntas.">
      <AlertaComponent type="info" title="Antes del grooming">
        Esta etapa corresponde al Agente Analista. No ingrese datos personales reales (nombres de clientes, identificaciones, números de póliza): anonimícelos antes de pegar la información.
      </AlertaComponent>
      <form onSubmit={handleAnalyzeRequirement}>
        <CampoTextoComponent
          label="Nombre del requerimiento"
          id="req-name"
          required
          placeholder="Ej. Modificación de coberturas en pólizas vigentes"
          value={requirementName}
          onChange={(e) => setRequirementName(e.target.value)}
        />

        <SelectorComponent
          label="Tipo de información"
          id="info-type"
          required
          options={INFO_TYPE_OPTIONS}
          value={infoType}
          onChange={(e) => setInfoType(e.target.value)}
        />

        <div className="grid-2">
          <SelectorComponent
            label="Tipo de solicitud"
            id="request-type"
            required
            options={TIPOS_SOLICITUD.map((tipo) => ({ value: tipo, label: tipo }))}
            value={requestType}
            onChange={(e) => setRequestType(e.target.value)}
          />
          <SelectorComponent
            label="Sistema"
            id="req-system"
            required
            options={armarOpcion(OPCION_SISTEMA, system, 'Seleccione un sistema')}
            value={system}
            onChange={(e) => setSystem(e.target.value)}
          />
        </div>
        <div className="grid-2">
          <CampoTextoComponent
            label="Código de HU"
            id="req-codigo-hu"
            required
            placeholder="Ej. POL-OF"
            value={codigoHu}
            onChange={(e) => setCodigoHu(e.target.value)}
            hint="Prefijo del número de la HU; por ejemplo POL-OF genera HU-POL-OF-001."
          />
          <SelectorComponent
            label="Área solicitante"
            id="req-requester"
            options={armarOpcion(OPCION_AREA_SOLICITANTE, requester, 'Seleccione un área')}
            value={requester}
            onChange={(e) => setRequester(e.target.value)}
          />
        </div>

        <AreaTextoComponent
          label="Descripción o información de negocio"
          id="req-desc"
          required
          rows={6}
          placeholder="Describa el requerimiento tal como lo expresó el cliente o equipo de negocio..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          hint={`Puede copiar y pegar notas desestructuradas, correos o minutas (máximo ${MAX_AGENT_MESSAGE_CODEPOINTS} caracteres en total).`}
        />

        {formError && <AlertaComponent type="danger" title="Revise el formulario">{formError}</AlertaComponent>}

        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', marginTop: '1.5rem', flexWrap: 'wrap' }}>
          {agentResponse ? (
            <BotonComponent type="button" variant="secondary" icon={RotateCcw} onClick={handleRestartAnalysis}>
              Empezar de nuevo
            </BotonComponent>
          ) : (
            <BotonComponent
              type="button"
              variant="secondary"
              icon={Save}
              onClick={() => {
                if (!requirementName.trim()) {
                  setFormError('Escriba al menos el nombre del requerimiento para guardarlo.');
                  return;
                }
                handleSaveDraft();
              }}
            >
              Guardar y continuar después
            </BotonComponent>
          )}
          <BotonComponent type="submit" variant="primary" icon={Sparkles} size="lg">
            {agentResponse ? 'Volver a analizar' : 'Analizar Requerimiento'}
          </BotonComponent>
        </div>
      </form>
    </TarjetaComponent>
  );
};
