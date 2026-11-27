import React from 'react';
import { TarjetaComponent } from '../Comun/TarjetaComponent';
import { TarjetaItemsAyudaComponent } from './TarjetaItemsAyudaComponent';
import {
  CAMBIO_ARQUITECTURA, CAPA_ARQUITECTURA, DISPOSITIVO_DISENO, IA_ARQUITECTURA, PALETA_COLOR, PRINCIPIO_ARQUITECTURA,
  PRODUCCION_ARQUITECTURA, REPOSITORIO_PRUEBAS, RESUMEN_ARQUITECTURA, STACK_ARQUITECTURA, TIPOGRAFIA_DISENO,
} from '../../data/ayudaDocumentacion';

const ListaPunto = ({ lista }) => (
  <ul className="ayuda-item__puntos">
    {lista.map((texto) => <li key={texto}>{texto}</li>)}
  </ul>
);

// Paleta de colores: la muestra usa la variable del tema, así se ve bien en modo claro y oscuro.
const PaletaComponent = () => (
  <TarjetaComponent title="Paleta de colores" subtitle="Cada color es una variable del tema (src/styles/_theme.scss) con su valor en modo claro y oscuro">
    <ul className="ayuda-paleta">
      {PALETA_COLOR.map(({ nombre, variable, claro, oscuro, uso }) => (
        <li key={variable} className="ayuda-paleta__color">
          <span className="ayuda-paleta__muestra" style={{ backgroundColor: `var(${variable})` }} aria-hidden="true" />
          <div>
            <p className="ayuda-paleta__nombre">{nombre}</p>
            <p className="ayuda-paleta__valor"><code>{variable}</code> · claro {claro} · oscuro {oscuro}</p>
            <p className="ayuda-paleta__uso">{uso}</p>
          </div>
        </li>
      ))}
    </ul>
  </TarjetaComponent>
);

// Todo lo que hace falta para ponerse al día con el proyecto: qué es, con qué está hecho, cómo se cambia y cómo se ve.
export const ArquitecturaAyudaComponent = () => (
  <>
    <TarjetaComponent title="Para ponerse al día" subtitle="Lo esencial del proyecto en un minuto">
      <ListaPunto lista={RESUMEN_ARQUITECTURA} />
    </TarjetaComponent>
    <TarjetaItemsAyudaComponent title="Con qué está hecho" subtitle="Tecnologías y para qué se usa cada una" items={STACK_ARQUITECTURA} />
    <TarjetaComponent title="Repositorio de pruebas del Asesor Técnico" subtitle="El código que el Asesor revisa para encontrar el impacto de un cambio">
      <ListaPunto lista={REPOSITORIO_PRUEBAS} />
    </TarjetaComponent>
    <TarjetaItemsAyudaComponent
      title="Cómo está construido"
      subtitle="Es un prototipo, pero su estructura está pensada para crecer y llegar a producción"
      items={PRINCIPIO_ARQUITECTURA}
    />
    <TarjetaItemsAyudaComponent title="Capas del sistema" subtitle="Cada capa tiene una responsabilidad" items={CAPA_ARQUITECTURA} />
    <TarjetaItemsAyudaComponent
      title="Cómo se hace un cambio"
      subtitle="Los cambios frecuentes se resuelven en un solo lugar"
      items={CAMBIO_ARQUITECTURA}
    />
    <PaletaComponent />
    <TarjetaItemsAyudaComponent title="Tipografía" subtitle="Dos familias, cargadas desde Google Fonts" items={TIPOGRAFIA_DISENO} />
    <TarjetaItemsAyudaComponent title="Web, tablet y móvil" subtitle="La estructura se adapta sola; las pantallas no hacen nada especial" items={DISPOSITIVO_DISENO} />
    <TarjetaComponent title="Pensado para producción" subtitle="Lo que ya está resuelto aunque sea un prototipo">
      <ListaPunto lista={PRODUCCION_ARQUITECTURA} />
    </TarjetaComponent>
    <TarjetaComponent title="Preparado para programar con IA" subtitle="Para que otra persona o herramienta de IA mantenga la estructura y el diseño">
      <ListaPunto lista={IA_ARQUITECTURA} />
    </TarjetaComponent>
  </>
);
