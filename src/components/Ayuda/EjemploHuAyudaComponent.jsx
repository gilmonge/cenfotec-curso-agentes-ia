import React from 'react';
import { TarjetaComponent } from '../Comun/TarjetaComponent';
import ejemploHu from '../../assets/ejemplo-hu.png';

export const EjemploHuAyudaComponent = () => (
  <TarjetaComponent
    title="Cómo se ve una HU generada"
    subtitle="Primera página del PDF con la plantilla de documento (el Word tiene el mismo formato). Datos de ejemplo."
  >
    <img
      className="ayuda-ejemplo"
      src={ejemploHu}
      alt="Primera página de una historia de usuario generada: referencias con declaración de valor, priorización del negocio, revisión de desarrollo, beneficios esperados y firmas de aprobación"
    />
    <p className="ayuda-item__texto">
      Incluye Referencias con la Declaración de valor (Como / Quiero / Para), Priorización del negocio, Revisión de Desarrollo,
      Beneficios esperados y Firmas de Aprobación; luego los Criterios de Aceptación y, en una página final, las Observaciones adicionales.
    </p>
  </TarjetaComponent>
);
