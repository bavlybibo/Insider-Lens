import { useEffect, useMemo, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import type { GeoJSONSource, Map as MapInstance } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { FeatureCollection, Point, Polygon } from 'geojson';
import type { Detection, Release, SourceId } from './science';
import { PALETTES, quantitativeCells, type Density } from './atlas';
import { activityBounds } from './investigation';
import { loadCoarseContext, type ContextCountries } from './basemap';
import { StaticContext } from './StaticContext';
import { applyCartography, densityOpacity, NIGHT_PALETTES, type MapTheme, type PaintMemory } from './cartography';

maplibregl.setWorkerUrl(workerUrl);

type Points = FeatureCollection<Point, { source: string; cell: string; id: string }>;
export type RenderMode = 'auto' | 'points' | 'grid' | 'heat';
function features(records: Detection[]): Points {
  return { type: 'FeatureCollection', features: records.map(r => ({ type: 'Feature', id: r.id, properties: { source: r.source, cell: r.cell, id: r.id }, geometry: { type: 'Point', coordinates: [r.longitude, r.latitude] } })) };
}
export function FireMap({ release, records, selectionId, mode, selectedCell, period, resetKey, camera, leftInset, onRetry, onRecord, onCell,lensSource='ALL',metric='occupied_cell_days',bandwidth=10,onMapReady,comparisonPane=false,theme='day',showCenters=false,onMethod }: {
  release: Release; records: Detection[]; selectionId: string; mode: RenderMode; selectedCell: string | null; period: string; resetKey: number;
  camera:{id:number;target:'study'|'activity'|'selection'};leftInset:number;onRetry:()=>void;onRecord:(record:Detection)=>void;onCell: (cell: string) => void;
  lensSource?:SourceId|'ALL';metric?:'records'|'occupied_cell_days';bandwidth?:5|10;onMapReady?:(map:MapInstance|null)=>void;
  comparisonPane?:boolean;
  theme?:MapTheme;showCenters?:boolean;onMethod?:()=>void;
}) {
  const element = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapInstance | null>(null);
  const paintMemory = useRef<PaintMemory>(new Map());
  const themeRef=useRef(theme);themeRef.current=theme;
  const appliedCamera=useRef<number|null>(null);
  const lensRecords=useMemo(()=>lensSource==='ALL'?records:records.filter(r=>r.source===lensSource),[records,lensSource]);
  const latest = useRef({ records:lensRecords, mode, selectedCell, onCell, onRecord, camera, leftInset,metric,lensSource,bandwidth,comparisonPane });
  latest.current = { records:lensRecords, mode, selectedCell, onCell, onRecord, camera, leftInset,metric,lensSource,bandwidth,comparisonPane };
  const [heat,setHeat]=useState<{token:string;data:Density;error?:string}|null>(null);
  const heatToken=`${selectionId}|${lensSource}|${bandwidth}`;
  const validHeat=mode==='heat'&&heat?.token===heatToken;
  const heatMaximum=validHeat?Math.max(0,...heat.data.features.map(f=>f.properties.value)):0;
  const grid=useMemo(()=>quantitativeCells(release,lensRecords,metric),[release,lensRecords,metric]);
  const gridMaximum=Math.max(0,...grid.features.map(f=>f.properties.value));
  const palettes=theme==='night'?NIGHT_PALETTES:PALETTES;
  const [styleEpoch,setStyleEpoch]=useState(0);
  const [state, setState] = useState('Loading geographic basemap…');
  const [failed, setFailed] = useState(false);
  const [ready, setReady] = useState(false);
  const [outside, setOutside] = useState(false);
  const [representation, setRepresentation] = useState('Occupied 10 km cells');
  const [hover, setHover] = useState('');
  const [cameraNote,setCameraNote]=useState('');
  const [coarse,setCoarse]=useState(false);
  const [tileWarning,setTileWarning]=useState(false);

  useEffect(()=>{
    if(mode!=='heat')return;
    const worker=new Worker(new URL('./heat.worker.ts',import.meta.url),{type:'module'});
    worker.onmessage=event=>{if(event.data.token===heatToken)setHeat(event.data);};
    worker.onerror=event=>{event.preventDefault();setHeat({token:heatToken,data:{type:'FeatureCollection',features:[]},error:'Density worker unavailable. Native evidence remains available.'});};
    worker.postMessage({token:heatToken,records:lensRecords,bandwidth,bbox:release.policy.aoi});
    return ()=>worker.terminate();
  },[mode,heatToken,lensRecords,bandwidth,release]);

  function fit(map:MapInstance,target:'study'|'activity'|'selection') {
    const data=latest.current, [w,s,e,n]=release.policy.aoi;
    let bounds:[[number,number],[number,number]]|null=[[w,s],[e,n]];
    if(target==='activity') bounds=activityBounds(data.records);
    if(target==='selection'&&data.selectedCell) {
      const ring=release.cells.features.find(f=>f.properties.cell===data.selectedCell)?.geometry.coordinates[0];
      if(ring) bounds=[[Math.min(...ring.map(p=>p[0])),Math.min(...ring.map(p=>p[1]))],[Math.max(...ring.map(p=>p[0])),Math.max(...ring.map(p=>p[1]))]];
    }
    if(!bounds){setCameraNote('No recorded activity to fit in this selection. The scientific AOI remains unchanged.');return;}
    const narrow=map.getContainer().clientWidth<700;
    const left=narrow?24:data.leftInset+24;
    const right=narrow?24:Math.min(left,Math.max(24,map.getContainer().clientWidth-left-360));
    map.fitBounds(bounds,{padding:{left,right,top:narrow?(data.comparisonPane?42:142):84,bottom:narrow&&data.comparisonPane?110:104},maxZoom:12.5,duration:0});
    setCameraNote(target==='activity'?'Camera fitted to selected reported detections; scientific AOI unchanged.':target==='selection'&&data.selectedCell?`Camera fitted to ${data.selectedCell}; scientific AOI unchanged.`:'Camera fitted to the fixed scientific study area.');
  }

  function representationFor(map: MapInstance) {
    const heat=latest.current.mode==='heat';
    const cells = latest.current.mode === 'grid' || (latest.current.mode === 'auto' && map.getZoom() < 10);
    if (map.getLayer('eg-grid-outline')) {
      map.setLayoutProperty('eg-grid-outline', 'visibility', cells ? 'visible' : 'none');
      map.setLayoutProperty('eg-grid-fill', 'visibility', cells ? 'visible' : 'none');
      map.setLayoutProperty('eg-detections', 'visibility', cells||heat ? 'none' : 'visible');
    }
    setRepresentation(heat?'Detection density · fixed-distance kernel':cells ? 'Occupied 10 km cells' : 'Reported pixel centers');
  }

  function update(map: MapInstance) {
    const data = latest.current;
    (map.getSource('eg-points') as GeoJSONSource | undefined)?.setData(features(data.records));
    (map.getSource('eg-cells') as GeoJSONSource | undefined)?.setData(quantitativeCells(release,data.records,data.metric));
    (map.getSource('eg-selected') as GeoJSONSource | undefined)?.setData({ ...release.cells, features: release.cells.features.filter(f => f.properties.cell === data.selectedCell) });
    representationFor(map);
  }
  useEffect(() => {
    if (!element.current) return;
    let map: MapInstance;
    try {
      map = new maplibregl.Map({ container: element.current, style: 'https://tiles.openfreemap.org/styles/liberty',
        center: [-7.95, 40.05], zoom: 8.7, minZoom: 2, maxZoom: 16, attributionControl: false });
      mapRef.current = map;
      (element.current as HTMLDivElement & { scientificMap?: MapInstance }).scientificMap = map;
      onMapReady?.(map);
    } catch {
      setState('Geographic map unavailable on this device. The calendar, evidence and data table remain usable.'); setFailed(true); return;
    }
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    map.addControl(new maplibregl.ScaleControl({ unit: 'metric', maxWidth: 120 }), 'bottom-left');
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');
    let degraded = false, fallbackStarted=false, handlersRegistered=false,geographyVerified=false;
    let countries:ContextCountries|null=null;
    const controller=new AbortController();
    async function fallbackContext() {
      if(fallbackStarted)return;fallbackStarted=true;degraded=true;
      try {
        const context=await loadCoarseContext(controller.signal);if(controller.signal.aborted)return;
        countries=context.countries;setCoarse(true);setTileWarning(false);map.setStyle(context.style,{diff:false});
        setState('Loading verified coarse country context…');
      } catch {
        if(controller.signal.aborted)return;
        map.setStyle({ version: 8, sources: {}, layers: [{ id: 'degraded-background', type: 'background', paint: { 'background-color': '#e8e6de' } }] });
        setState('Geographic basemap unavailable. Native coordinates, calendar and export remain available.');
      }
    }
    const fallback = setTimeout(() => {
      if (geographyVerified) return;
      void fallbackContext();
    }, 4500); // UI responsiveness policy; no change to any scientific gate.
    map.on('error', () => {if(geographyVerified)setTileWarning(true);else setState('Some geographic tiles could not load. Scientific data remain available.');if(!map.getSource('eg-points'))void fallbackContext();});
    map.on('style.load', () => {
      if (map.getSource('eg-points')) return;
      paintMemory.current.clear();
      // Quiet sea tone keeps the inland scientific evidence dominant. Geometry
      // and labels remain the provider's credited OpenMapTiles cartography.
      for(const layer of map.getStyle().layers??[]) {
        if(layer.type==='fill'&&/water/i.test(layer.id))map.setPaintProperty(layer.id,'fill-color','#e1e9e5');
        // Measured software-WebGL paint saving. These contextual layers do not
        // participate in scientific measurements; retain geography and credits.
        if(/^(landcover_|landuse_|park$|park_outline$|building-3d$|poi_)/.test(layer.id))map.setLayoutProperty(layer.id,'visibility','none');
      }
      if(countries) {
        const labels:FeatureCollection<Point,{name:string}>={type:'FeatureCollection',features:[]};
        for(const country of countries.features) {
          const label=country.properties.label;if(!label||label.length!==2||!label.every(Number.isFinite))continue;
          const canvas=document.createElement('canvas');canvas.width=160;canvas.height=36;
          const context=canvas.getContext('2d')!;context.font='600 17px Georgia';context.textAlign='center';context.fillStyle=themeRef.current==='night'?'#dce7d7':'#45604d';context.fillText(country.properties.name,80,24);
          if(!map.hasImage(`context-${country.properties.name}`))map.addImage(`context-${country.properties.name}`,context.getImageData(0,0,160,36));
          labels.features.push({type:'Feature',properties:{name:country.properties.name},geometry:{type:'Point',coordinates:label}});
        }
        map.addSource('offline-country-labels',{type:'geojson',data:labels});
        map.addLayer({id:'offline-labels',type:'symbol',source:'offline-country-labels',layout:{'icon-image':['concat','context-',['get','name']],'icon-allow-overlap':true}});
      }
      const [w, s, e, n] = release.policy.aoi;
      const boundary: FeatureCollection<Polygon> = { type: 'FeatureCollection', features: [{ type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] } }] };
      map.addSource('eg-aoi', { type: 'geojson', data: boundary });
      map.addLayer({ id: 'eg-aoi-boundary', type: 'line', source: 'eg-aoi', paint: { 'line-color': '#385a50', 'line-width': 1.5, 'line-dasharray': [5, 4] } });
      map.addSource('eg-cells', { type: 'geojson', data: release.cells });
      map.addLayer({ id: 'eg-grid-fill', type: 'fill', source: 'eg-cells', paint: { 'fill-color': '#8a7970', 'fill-opacity': 0.12 } });
      map.addLayer({ id: 'eg-grid-outline', type: 'line', source: 'eg-cells', paint: { 'line-color': '#6f6259', 'line-width': 1.2 } });
      map.addSource('eg-points', { type: 'geojson', data: features(latest.current.records) });
      map.addSource('eg-density',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
      map.addLayer({id:'eg-density-fill',type:'fill',source:'eg-density',layout:{visibility:'none'},paint:{'fill-color':'#e89937','fill-opacity':.75,'fill-antialias':false}});
      for (const source of ['AQUA_MODIS', 'SNPP_VIIRS', 'TERRA_MODIS'] as const) {
        const canvas = document.createElement('canvas'); canvas.width = canvas.height = 24;
        const ctx = canvas.getContext('2d')!; ctx.fillStyle = release.sources[source].color; ctx.strokeStyle = '#fff'; ctx.lineWidth = 2;
        ctx.beginPath();
        if (source === 'AQUA_MODIS') ctx.arc(12, 12, 8, 0, Math.PI * 2);
        else if (source === 'SNPP_VIIRS') { ctx.moveTo(12, 2); ctx.lineTo(22, 21); ctx.lineTo(2, 21); ctx.closePath(); }
        else { ctx.moveTo(12, 1); ctx.lineTo(23, 12); ctx.lineTo(12, 23); ctx.lineTo(1, 12); ctx.closePath(); }
        ctx.fill(); ctx.stroke(); map.addImage(`symbol-${source}`, ctx.getImageData(0, 0, 24, 24));
      }
      map.addLayer({ id: 'eg-detections', type: 'symbol', source: 'eg-points', layout: {
        'icon-image': ['concat', 'symbol-', ['get', 'source']], 'icon-size': ['interpolate', ['linear'], ['zoom'], 7, 0.24, 12, 0.55], 'icon-allow-overlap': true,
      }, paint: { 'icon-opacity': 0.86 } });
      map.addSource('eg-selected', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      map.addLayer({ id: 'eg-selection-outline', type: 'line', source: 'eg-selected', paint: { 'line-color': '#a74a0a', 'line-width': 3 } });
      applyCartography(map,themeRef.current,paintMemory.current);
      update(map); setReady(true);setStyleEpoch(n=>n+1);
      if(!handlersRegistered){handlersRegistered=true;
      map.on('click', 'eg-detections', event => {
        const record=latest.current.records.find(r=>r.id===event.features?.[0]?.properties?.id);
        if(record)latest.current.onRecord(record);
      });
      map.on('click', 'eg-grid-fill', event => {
        if (map.queryRenderedFeatures(event.point, { layers: ['eg-detections'] }).length) return;
        const cell = event.features?.[0]?.properties?.cell;
        if (typeof cell === 'string') latest.current.onCell(cell);
      });
      map.on('click','eg-density-fill',event=>{if(map.queryRenderedFeatures(event.point,{layers:['eg-detections']}).length)return;const id=event.features?.[0]?.properties?.nearest,record=latest.current.records.find(r=>r.id===id);if(record)latest.current.onRecord(record);});
      map.on('mousemove','eg-density-fill',event=>{const value=Number(event.features?.[0]?.properties?.value);if(Number.isFinite(value))setHover(`${latest.current.lensSource} · ${value.toFixed(5)} records/km² · ${latest.current.bandwidth} km bandwidth · selected UTC period · nearest contributing native record on click. Descriptive smoothing; support unknown; not fire probability or burned area.`);});
      map.on('mouseleave','eg-density-fill',()=>setHover(''));
      for (const layer of ['eg-detections', 'eg-grid-fill']) {
        map.on('mouseenter', layer, () => { map.getCanvas().style.cursor = 'pointer'; });
        map.on('mouseleave', layer, () => { map.getCanvas().style.cursor = ''; });
      }
      map.on('mousemove','eg-detections',event=>{
        const record=latest.current.records.find(r=>r.id===event.features?.[0]?.properties?.id);
        if(record)setHover(`${release.sources[record.source].name} · ${record.utc} · source row ${record.id} · FRP ${record.frp} MW · native confidence ${record.confidence}. Reported pixel center; observation support unknown. Click for the record.`);
      });
      map.on('mouseleave','eg-detections',()=>setHover(''));
      map.on('mousemove', 'eg-grid-fill', event => {
        const cell = event.features?.[0]?.properties?.cell;
        if (typeof cell !== 'string') return;
        const selected = latest.current.records.filter(r => r.cell === cell);
        setHover(`${cell} · selected native records: ${['AQUA_MODIS', 'SNPP_VIIRS', 'TERRA_MODIS'].filter(source=>selected.some(r=>r.source===source)).map(source => {
          const group = selected.filter(r => r.source === source);
          return `${source === 'AQUA_MODIS' ? 'Aqua' : source === 'SNPP_VIIRS' ? 'S-NPP' : 'Terra'} ${group.length} records / ${new Set(group.map(r => r.day)).size} days`;
        }).join(' · ')}`);
      });
      map.on('mouseleave', 'eg-grid-fill', () => setHover(''));
      }
      if(appliedCamera.current===null){fit(map,latest.current.camera.target);appliedCamera.current=latest.current.camera.id;}
    });
    map.on('idle', () => {
      if (!map.getSource('eg-points')) return;
      const geographicFeatures = map.queryRenderedFeatures().filter(f => !String(f.source).startsWith('eg-'));
      if(geographicFeatures.length>0){geographyVerified=true;clearTimeout(fallback);}
      setState(geographicFeatures.length > 0 ? 'Geographic basemap rendered' : degraded ? 'Geographic basemap unavailable. Native coordinates, calendar and export remain available.' : 'Geography not verified; data layers remain available');
    });
    map.on('zoomend', () => representationFor(map));
    map.on('moveend', () => {
      const b = map.getBounds(), [w, s, e, n] = release.policy.aoi;
      setOutside(b.getEast() < w || b.getWest() > e || b.getNorth() < s || b.getSouth() > n);
    });
    const resize = new ResizeObserver(() => map.resize()); resize.observe(element.current!);
    return () => { controller.abort();clearTimeout(fallback); resize.disconnect(); mapRef.current = null;onMapReady?.(null); map.remove(); };
  }, [release]);

  // Representation changes are cosmetic: do not serialize/reparse every source
  // point in the map worker just to toggle cells versus reported pixels.
  useEffect(() => { if (mapRef.current && ready) update(mapRef.current); }, [lensRecords, ready]);
  useEffect(() => { if (mapRef.current && ready) representationFor(mapRef.current); }, [mode, ready]);
  useEffect(()=>{
    const map=mapRef.current;if(!map?.getLayer('eg-density-fill'))return;
    const source=lensSource==='ALL'?'AQUA_MODIS':lensSource,palette=palettes[source];
    const color=(maximum:number)=>['interpolate',['linear'],['get','value'],0,palette[0],Math.max(maximum*.35,1e-12),palette[1],Math.max(maximum,2e-12),palette[2]] as any;
    (map.getSource('eg-cells') as GeoJSONSource).setData(grid);
    map.setPaintProperty('eg-grid-fill','fill-color',mode==='grid'?color(gridMaximum):'#8a7970');
    map.setPaintProperty('eg-grid-fill','fill-opacity',mode==='grid'?.8:.12);
    map.setLayoutProperty('eg-density-fill','visibility',mode==='heat'&&validHeat&&!heat.error?'visible':'none');
    (map.getSource('eg-density') as GeoJSONSource).setData(validHeat&&!heat.error?heat.data:{type:'FeatureCollection',features:[]});
    map.setPaintProperty('eg-density-fill','fill-color',color(heatMaximum));
    map.setPaintProperty('eg-density-fill','fill-opacity',densityOpacity(heatMaximum) as any);
  },[grid,gridMaximum,heat,validHeat,heatMaximum,mode,lensSource,styleEpoch,theme]);
  useEffect(()=>{
    const map=mapRef.current;if(!map?.getSource('eg-points'))return;
    applyCartography(map,theme,paintMemory.current);
    // Coarse labels are locally drawn, credited country names, not observations.
    for(const name of ['Portugal','Spain','France','Morocco'])if(map.hasImage(`context-${name}`)){
      const canvas=document.createElement('canvas');canvas.width=160;canvas.height=36;const ctx=canvas.getContext('2d')!;
      ctx.font='600 17px Georgia';ctx.textAlign='center';ctx.fillStyle=theme==='night'?'#dce7d7':'#45604d';ctx.fillText(name,80,24);map.updateImage(`context-${name}`,ctx.getImageData(0,0,160,36));
    }
  },[theme,styleEpoch]);
  useEffect(()=>{
    const map=mapRef.current;if(map?.getLayer('eg-detections')){
      if(mode==='heat')map.setLayoutProperty('eg-detections','visibility',showCenters?'visible':'none');
      map.setPaintProperty('eg-detections','icon-opacity',mode==='heat'&&showCenters?.65:.86);
    }
  },[mode,showCenters,styleEpoch,lensRecords]);
  useEffect(() => {
    if (mapRef.current && ready) (mapRef.current.getSource('eg-selected') as GeoJSONSource)?.setData({ ...release.cells, features: release.cells.features.filter(f => f.properties.cell === selectedCell) });
  }, [selectedCell, ready, release]);
  useEffect(() => { if (mapRef.current && resetKey) fit(mapRef.current,'study'); }, [resetKey]);
  useEffect(()=>{
    if(mapRef.current&&ready&&appliedCamera.current!==camera.id){fit(mapRef.current,camera.target);appliedCamera.current=camera.id;}
  },[camera.id,ready]);

  return <div className={`map-shell map-theme-${theme}`} data-testid="map-surface" data-release={release.releaseId} data-selection={selectionId}>
    {failed&&<StaticContext release={release}/>}
    <div ref={element} className="geographic-map" aria-label="Interactive geographic map of thermal detections in Central Portugal" tabIndex={0} data-testid="geographic-map" data-theme={theme} data-representation={representation} data-basemap={coarse?'coarse-context':'detailed-provider'} data-lens={lensSource} data-cohort-records={lensRecords.length} data-bandwidth-km={mode==='heat'?bandwidth:undefined} data-heat-ready={mode==='heat'?String(validHeat&&!heat.error):undefined}/>
    <div className="cartography-tag"><i/>{theme==='night'?'Night cartography':'Day cartography'}<span>visual treatment</span></div>
    <div className="camera-tools" aria-label="Map framing"><button onClick={()=>mapRef.current&&fit(mapRef.current,'study')}>Fit study area</button><button onClick={()=>mapRef.current&&fit(mapRef.current,'activity')} disabled={!records.length}>Fit detected activity</button><button aria-label="Reset to evidence selection" onClick={()=>mapRef.current&&fit(mapRef.current,'selection')}>Reset to evidence selection</button></div>
    <div className="sr-only" role="status">{cameraNote}</div>
    {outside && <div className="outside-scope" role="status">Outside supplied extract · scientific data not available here. Totals still refer to the selected Portugal scope.</div>}
    {hover && <div className="map-hover" role="status">{hover}</div>}
    {lensSource!=='ALL'&&!lensRecords.length&&<div className="density-pending" role="status">{release.months.includes(period.slice(0,7))?`No reported records in the ${release.sources[lensSource].name} map lens. Valid observation unknown.`:'Source extract unavailable for this map lens and period.'}</div>}
    {mode==='heat'&&!validHeat&&<div className="density-pending" role="status">Calculating fixed {bandwidth} km density…</div>}
    {mode==='heat'&&heat?.error&&<div className="density-pending" role="status">{heat.error}</div>}
    <div className={`map-status ${failed ? 'map-failed' : ''}`} role="status">{state}</div>
    {tileWarning&&!coarse&&<div className="tile-detail-warning" role="status">Some geographic detail failed to load; rendered context retained. Scientific data are unchanged.</div>}
    {coarse&&<div className="coarse-context" role="note">Coarse offline country context · Natural Earth 1:50 million · no street detail or observation QA</div>}
    {(failed||state.includes('unavailable')||state.includes('not verified')||state.includes('could not load'))&&<button className="map-retry" onClick={onRetry}>Retry basemap</button>}
    <div className={`map-legend ${mode==='heat'||mode==='grid'?'quantitative-legend':''}`}>
      {mode==='heat'||mode==='grid'?<><strong>{release.sources[lensSource==='ALL'?'AQUA_MODIS':lensSource].name}</strong><span className="atlas-ramp" style={{background:`linear-gradient(to right,${palettes[lensSource==='ALL'?'AQUA_MODIS':lensSource].join(',')})`}}/><span>{mode==='heat'&&!heatMaximum?'No samples · support unknown':mode==='grid'&&!gridMaximum?'No occupied cells · support unknown':'0 → '+(mode==='heat'?heatMaximum.toFixed(3):gridMaximum)} {mode==='heat'?'records/km²':metric==='records'?'records/cell':'cell-days/cell'}</span><span>{mode==='heat'?`${bandwidth} km kernel · 2 km sampling`:'Fixed 10 km equal-area cells'}</span><small>Relative within this source/time selection · not comparable exposure</small><small>Map lens only · main CSV retains all selected source lanes</small><small className="compact-map-limit">Relative source / D/N scale · not fire probability</small></>:representation === 'Occupied 10 km cells' ? <span><i className="cell-swatch"/>{coarse?'Occupied cell':'Cell with selected-source records'}</span> : <>{(['AQUA_MODIS','SNPP_VIIRS','TERRA_MODIS'] as const).filter(source=>lensSource==='ALL'?lensRecords.some(r=>r.source===source):lensSource===source).map(source=><span key={source}><i className={`source-shape shape-${source}`} style={{color:release.sources[source].color}}/>{source==='AQUA_MODIS'?'Aqua':source==='SNPP_VIIRS'?'S-NPP':'Terra'}</span>)}</>}
      {coarse&&<button className="coarse-key" aria-label="Retry detailed basemap" onClick={onRetry}>Coarse context · retry</button>}<span className="legend-unit">{mode==='heat'?'Detection-density visualization':representation} · not incidents or burned area</span></div>
    {mode==='heat'&&onMethod&&<button className="density-evidence" onClick={onMethod}>Density method & evidence ↗</button>}
    <div className="map-watermark">{selectedCell??'Central Portugal'} · {period} UTC · NASA FIRMS · {release.releaseId.slice(0, 15)}</div>
  </div>;
}
