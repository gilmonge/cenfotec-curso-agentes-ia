import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { CampoTextoComponent } from '../Comun/CampoTextoComponent';
import { AreaTextoComponent } from '../Comun/AreaTextoComponent';
import { BotonComponent } from '../Comun/BotonComponent';
import { ROLES_FIRMA } from '../../utils/plantillaHu';

// Campos de la plantilla que se completan al redactar la historia:
// número, beneficios esperados y personas que firman.
export const CamposPlantillaComponent = ({ valor, alCambiar, prefijoId = 'plantilla' }) => {
  const listaBeneficio = valor.benefits.length > 0 ? valor.benefits : [''];

  const cambiarBeneficio = (indice, texto) => {
    alCambiar({ benefits: listaBeneficio.map((beneficio, posicion) => (posicion === indice ? texto : beneficio)) });
  };

  const agregarBeneficio = () => alCambiar({ benefits: [...listaBeneficio, ''] });

  const quitarBeneficio = (indice) => {
    alCambiar({ benefits: listaBeneficio.filter((_, posicion) => posicion !== indice) });
  };

  const cambiarFirmante = (clave, nombre) => {
    alCambiar({ signers: { ...valor.signers, [clave]: nombre } });
  };

  return (
    <div className="plantilla-campos">
      <CampoTextoComponent
        label="Número de la HU"
        id={`${prefijoId}-numero`}
        required
        placeholder="Ej. HU-GEN-COM-001"
        value={valor.number}
        onChange={(evento) => alCambiar({ number: evento.target.value })}
        hint="Se propone según el código de HU y el último número usado; puede corregirlo."
      />

      <fieldset className="plantilla-campos__grupo">
        <legend>Beneficios esperados</legend>
        {listaBeneficio.map((beneficio, indice) => (
          <div key={indice} className="plantilla-campos__beneficio">
            <AreaTextoComponent
              label={`Beneficio ${indice + 1}`}
              id={`${prefijoId}-beneficio-${indice}`}
              rows={2}
              value={beneficio}
              onChange={(evento) => cambiarBeneficio(indice, evento.target.value)}
            />
            {listaBeneficio.length > 1 && (
              <BotonComponent
                type="button"
                variant="secondary"
                icon={Trash2}
                onClick={() => quitarBeneficio(indice)}
                aria-label={`Quitar beneficio ${indice + 1}`}
              >
                Quitar
              </BotonComponent>
            )}
          </div>
        ))}
        <BotonComponent type="button" variant="secondary" icon={Plus} onClick={agregarBeneficio}>
          Agregar beneficio
        </BotonComponent>
      </fieldset>

      <fieldset className="plantilla-campos__grupo">
        <legend>Personas que firman</legend>
        <p className="form-hint">Opcional. Si deja un nombre vacío, el Word lo mostrará como pendiente de completar.</p>
        {ROLES_FIRMA.map((rol) => (
          <CampoTextoComponent
            key={rol.clave}
            label={rol.rotulo}
            id={`${prefijoId}-firma-${rol.clave}`}
            value={valor.signers[rol.clave] ?? ''}
            onChange={(evento) => cambiarFirmante(rol.clave, evento.target.value)}
          />
        ))}
      </fieldset>
    </div>
  );
};
