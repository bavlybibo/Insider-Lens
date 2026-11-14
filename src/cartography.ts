import type { Map as MapInstance } from 'maplibre-gl';
import type { SourceId } from './science';
type PaintKey = Parameters<MapInstance['getPaintProperty']>[1];

export type MapTheme = 'day' | 'night';
export type PaintMemory = Map<string, Record<string, unknown>>;
export const NIGHT_PALETTES:Record<SourceId,[string,string,string]>={
  AQUA_MODIS:['#293f37','#e7a04e','#ffe5a4'],
  SNPP_VIIRS:['#123d40','#2eb8be','#c7fff0'],
  TERRA_MODIS:['#33324c','#ad8dce','#eadbff'],
};
/** Presentation only: retain provider geometry, attribution, camera and eg-* data. */
export function applyCartography(map: MapInstance, theme: MapTheme, memory: PaintMemory) {
  const night = theme === 'night';
  for (const layer of map.getStyle().layers ?? []) {
    if (layer.id.startsWith('eg-')) continue;
    const colors: Record<string, unknown> = {};
    if (layer.type === 'background') colors['background-color'] = '#0b2429';
    if (layer.type === 'fill') {
      colors['fill-color'] = /water/i.test(layer.id) ? '#0b2429' : '#193532';
      if (layer.paint?.['fill-outline-color']) colors['fill-outline-color'] = '#668176';
    }
    if (layer.type === 'line') colors['line-color'] = /water/i.test(layer.id) ? '#32616a' : /boundary|border/i.test(layer.id) ? '#91a99b' : /casing|tunnel/i.test(layer.id) ? '#102c2d' : '#506d61';
    if (layer.type === 'symbol' && layer.layout?.['text-field']) {
      colors['text-color'] = '#dce7d7'; colors['text-halo-color'] = '#18342f';
    }
    if (layer.type === 'raster') {
      colors['raster-brightness-max'] = .3; colors['raster-brightness-min'] = .02; colors['raster-saturation'] = -.65;
    }
    if (!memory.has(layer.id)) memory.set(layer.id, Object.fromEntries(Object.keys(colors).map(key => [key, map.getPaintProperty(layer.id, key as PaintKey)])));
    for (const [key, color] of Object.entries(colors)) {
      const value=night?color:memory.get(layer.id)?.[key]??null;
      if((map.getPaintProperty(layer.id,key as PaintKey)??null)!==(value??null))map.setPaintProperty(layer.id,key as PaintKey,value as any);
    }
  }
  if (map.getLayer('eg-aoi-boundary')) map.setPaintProperty('eg-aoi-boundary', 'line-color', night ? '#c5d3b1' : '#34594a');
  if (map.getLayer('eg-selection-outline')) map.setPaintProperty('eg-selection-outline', 'line-color', night ? '#ffbc70' : '#a74a0a');
  if (map.getLayer('eg-grid-outline')) map.setPaintProperty('eg-grid-outline', 'line-color', night ? '#a4b2a2' : '#6f6259');
}

/** Alpha encodes the same source-relative sampled value as the color ramp. */
export function densityOpacity(maximum: number) {
  return ['interpolate', ['linear'], ['get', 'value'], 0, 0, Math.max(maximum * .08, 1e-12), .22, Math.max(maximum * .35, 2e-12), .65, Math.max(maximum, 3e-12), .9];
}
