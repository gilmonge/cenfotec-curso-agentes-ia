import React from 'react';
import { TarjetaComponent } from '../Comun/TarjetaComponent';

// Tarjeta de la Ayuda con una lista de elementos { titulo, texto, puntos? }.
export const TarjetaItemsAyudaComponent = ({ title, subtitle, items, children }) => (
  <TarjetaComponent title={title} subtitle={subtitle}>
    <div className="ayuda-lista">
      {items.map((item) => (
        <div key={item.titulo} className="ayuda-item">
          <h5 className="ayuda-item__titulo">{item.titulo}</h5>
          <p className="ayuda-item__texto">{item.texto}</p>
          {item.puntos && (
            <ul className="ayuda-item__puntos">
              {item.puntos.map((punto) => <li key={punto}>{punto}</li>)}
            </ul>
          )}
        </div>
      ))}
    </div>
    {children}
  </TarjetaComponent>
);
