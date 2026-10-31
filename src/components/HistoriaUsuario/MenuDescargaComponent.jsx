import React, { useEffect, useRef, useState } from 'react';
import { Download, FileText, FileType2 } from 'lucide-react';
import { BotonIconoComponent } from '../Comun/BotonIconoComponent';
import { descargarPdf } from '../../utils/exportarPdf';
import { descargarWord } from '../../utils/exportarWord';

const FORMATOS = [
  { id: 'word', texto: 'Word', icon: FileType2, descargar: descargarWord },
  { id: 'pdf', texto: 'PDF', icon: FileText, descargar: descargarPdf },
];

// Ícono de descarga que, al tocarlo, deja elegir entre Word y PDF.
export const MenuDescargaComponent = ({ story }) => {
  const [abierto, setAbierto] = useState(false);
  const raiz = useRef(null);

  useEffect(() => {
    if (!abierto) return undefined;
    const cerrarAfuera = (evento) => { if (!raiz.current?.contains(evento.target)) setAbierto(false); };
    const cerrarConTecla = (evento) => { if (evento.key === 'Escape') setAbierto(false); };
    document.addEventListener('mousedown', cerrarAfuera);
    document.addEventListener('keydown', cerrarConTecla);
    return () => {
      document.removeEventListener('mousedown', cerrarAfuera);
      document.removeEventListener('keydown', cerrarConTecla);
    };
  }, [abierto]);

  const elegir = (formato) => {
    setAbierto(false);
    Promise.resolve(formato.descargar(story)).catch((error) => console.error(`No se pudo generar el ${formato.texto}:`, error));
  };

  return (
    <div className="menu-descarga" ref={raiz}>
      <BotonIconoComponent icon={Download} etiqueta="Descargar" aria-haspopup="menu" aria-expanded={abierto} onClick={() => setAbierto((valor) => !valor)} />
      {abierto && (
        <div className="menu-descarga__lista" role="menu">
          {FORMATOS.map((formato) => (
            <button key={formato.id} type="button" role="menuitem" className="menu-descarga__item" onClick={() => elegir(formato)}>
              <formato.icon size={14} aria-hidden="true" /> {formato.texto}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
