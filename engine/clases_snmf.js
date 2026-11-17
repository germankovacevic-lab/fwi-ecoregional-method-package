// Clases de peligro del SNMF (nombres, colores y descripciones textuales) y fuentes: comunes al Semáforo v4 por
// ecorregión (fwi_payload.js) y a la calibración v3 por subregión (fwi_clases.js, historia). Sin calibración adentro:
// este módulo no arrastra ningún JSON al bundle del worker.
export const FUENTES = {
  snmf: { nombre: 'Servicio Nacional de Manejo del Fuego — Mapas de peligro de incendios forestales',
    url: 'https://www.smn.gob.ar/sites/default/files/mapasdepeligro.pdf' },
  guia_noa: { nombre: 'Guía para el análisis del índice FWI — Regional NOA (SNMF, 2026)',
    url: 'https://mesadelfuegonoa.org/wp-content/uploads/2026/09/Guia-FWI.pdf' },
  cordoba: { nombre: 'OHMC / IDECOR (Córdoba) — Índice FWI y componentes',
    url: 'https://obs-idecor-mapas-docs.obs.sa-argentina-1.myhuaweicloud.com/m442/Indice_FWI_y_componentes.pdf' },
  mapa_oficial: { nombre: 'Mapa oficial de peligro de incendio, hoy y a 24/48/72 h (SNMF + Servicio Meteorológico Nacional)',
    url: 'https://www.smn.gob.ar/indices_peligro_fuego' },
};

// Colores en la línea del mapa del SNMF (verde, azul, amarillo, naranja, rojo), sobre fondo oscuro.
export const CLASES = [
  { key: 'bajo', nombre_es: 'Bajo', nombre_en: 'Low', color: '#2f9e6f',
    descripcion_es: 'Es poco probable que los focos que se inicien puedan mantenerse activos. Sin embargo, la ignición puede tener lugar en proximidades de fuentes de calor como fogones o quemas.',
    descripcion_en: 'Fires that start are unlikely to stay active. However, ignition can occur near heat sources such as campfires or burns.' },
  { key: 'moderado', nombre_es: 'Moderado', nombre_en: 'Moderate', color: '#3f9be8',
    descripcion_es: 'Los combustibles vegetales se consideran suficientemente secos como para sostener la ignición y la combustión. Si bien el control del fuego es relativamente fácil, puede tornarse problemático si no se atienden inmediatamente.',
    descripcion_en: 'Vegetation fuels are considered dry enough to sustain ignition and combustion. Although fire control is relatively easy, it can become problematic if fires are not attended to immediately.' },
  { key: 'alto', nombre_es: 'Alto', nombre_en: 'High', color: '#f2c230',
    descripcion_es: 'Cualquier fuego que se inicia constituye un serio problema. El control comienza a ser gradualmente más dificultoso, si no se logra en la etapa inicial de desarrollo del fuego.',
    descripcion_en: 'Any fire that starts is a serious problem. Control becomes gradually more difficult if it is not achieved in the initial stage of fire development.' },
  { key: 'muy_alto', nombre_es: 'Muy alto', nombre_en: 'Very high', color: '#f07d1a',
    descripcion_es: 'Las condiciones de quema son críticas, pueden ocurrir coronamientos y fuegos de copa intermitentes en bosques.',
    descripcion_en: 'Burning conditions are critical; torching and intermittent crown fires can occur in forests.' },
  { key: 'extremo', nombre_es: 'Extremo', nombre_en: 'Extreme', color: '#e0322b',
    descripcion_es: 'La situación debería considerarse potencialmente "explosiva" o extremadamente crítica.',
    descripcion_en: 'The situation should be considered potentially "explosive" or extremely critical.' },
];

/** Subregión de una zona (clave interna, p. ej. "Patagonia húmeda") y su ficha pública. */

/** Clase pública del nivel i (0 = Bajo … 4 = Extremo); `nivel` va de 1 a 5. */
export function clase(i, completa = false) {
  const c = CLASES[i];
  const o = { key: c.key, nombre_es: c.nombre_es, nombre_en: c.nombre_en, color: c.color, nivel: i + 1 };
  if (completa) { o.descripcion_es = c.descripcion_es; o.descripcion_en = c.descripcion_en; }
  return o;
}
