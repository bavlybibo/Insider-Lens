import {useEffect,useMemo,useRef,useState} from 'react';
import * as ml from 'maplibre-gl';
import type {FeatureCollection,Polygon} from 'geojson';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import 'maplibre-gl/dist/maplibre-gl.css';
import {applyCartography,type PaintMemory} from './cartography';
import {areaBounds,caUnproject,cellId,CA_COLORS,CA_NAMES,CA_SOURCES,verifiedJson,type CaCatalog,type CaChunk,type CaQuery} from './canada';
import type {SourceId} from './science';
import type {BridgePoint} from './bridge';
import {aggregateObservation,type ObservationView} from './observation';
import {selectedTriangle} from './triangular';
import {TriangleMapCard} from './TriangularBridge';
import {TriangleLabels} from './TriangleLabels';
import {FallbackPlaces} from './FallbackPlaces';
import {GROUPS,GROUP_COLORS,retentionGeometry,type PositiveKey} from './evidenceRetention';
ml.setWorkerUrl(workerUrl);
const EMPTY_NATIVE:ReturnType<typeof caFeatures>={type:'FeatureCollection',features:[]};

function gridPolygon(i:number,j:number,stride=1):Polygon{const ring:number[][]=[];for(const [ax,ay,bx,by]of [[0,0,1,0],[1,0,1,1],[1,1,0,1],[0,1,0,0]])for(let k=0;k<5;k++)ring.push(caUnproject((i+stride*(ax+(bx-ax)*k/5))*10000,(j+stride*(ay+(by-ay)*k/5))*10000));ring.push(ring[0]);return {type:'Polygon',coordinates:[ring]};}

export function caFeatures(chunks:CaChunk[],query:CaQuery,lens:SourceId,metric:'records'|'cell_days',stride=1):FeatureCollection<Polygon,{cell:string;value:number;i:number;j:number;stride:number}>{
  const bins=new Map<string,{i:number;j:number;records:number;days:number}>();
  for(const c of chunks.filter(c=>c.source===lens))for(const [i,j,days] of c.cells){const bi=Math.floor(i/stride)*stride,bj=Math.floor(j/stride)*stride,key=`${bi}:${bj}`,v=bins.get(key)??{i:bi,j:bj,records:0,days:0};v.records+=days.reduce((n,d)=>n+(query.flag==='D'?d[1]:query.flag==='N'?d[2]:d[1]+d[2]),0);v.days+=days.length;bins.set(key,v);}
  return {type:'FeatureCollection',features:[...bins.values()].map(b=>{const ring:number[][]=[];for(const [ax,ay,bx,by]of [[0,0,1,0],[1,0,1,1],[1,1,0,1],[0,1,0,0]])for(let k=0;k<5;k++)ring.push(caUnproject((b.i+stride*(ax+(bx-ax)*k/5))*10000,(b.j+stride*(ay+(by-ay)*k/5))*10000));ring.push(ring[0]);return {type:'Feature',properties:{cell:cellId(b.i,b.j),i:b.i,j:b.j,stride,value:metric==='records'?b.records:b.days},geometry:{type:'Polygon',coordinates:[ring]}};})};
}

export function CanadaMap({catalog,chunks,query,lens,metric,theme,onCell,points=[],cohortId,observation,retentionMode=false,retentionKeys=[],drawing=false,onRectangle}:{catalog:CaCatalog;chunks:CaChunk[];query:CaQuery;lens:SourceId;metric:'records'|'cell_days';theme:'day'|'night';onCell:(id:string)=>void;points?:BridgePoint[];cohortId?:string;observation?:ObservationView|null;retentionMode?:boolean;retentionKeys?:PositiveKey[];drawing?:boolean;onRectangle?:(b:[number,number,number,number])=>void}){
  const ref=useRef<HTMLDivElement>(null),mapRef=useRef<ml.Map|null>(null),memory=useRef<PaintMemory>(new Map());
  const initiallyFramed=useRef(false),previousObservation=useRef(false),nativeCamera=useRef<(ml.CameraOptions & {padding:ml.PaddingOptions})|null>(null);
  const [ready,setReady]=useState(false),[status,setStatus]=useState('Loading geographic context…'),[coarse,setCoarse]=useState(false),[stride,setStride]=useState(4),[hover,setHover]=useState('');
  const mask=CA_SOURCES.reduce((n,s,i)=>n+(query.sources.includes(s)?1<<i:0),0);
  const [epoch,setEpoch]=useState(0);const latest=useRef({onCell,theme,retentionMode,drawing,onRectangle,mask});latest.current={onCell,theme,retentionMode,drawing,onRectangle,mask};
  const drawFirst=useRef<[number,number]|null>(null);
  // Policy switches change paint only: fixed scope geometry is not retessellated.
  const retainedGeometry=useMemo(()=>retentionGeometry(retentionKeys,{...query,sources:CA_SOURCES}),[retentionKeys]);
  const [drill,setDrill]=useState(false);
  const [triangleRegion,setTriangleRegion]=useState(false);
  const bins=useMemo(()=>aggregateObservation(observation?.study.phase===8?observation.points:[]),[observation?.points,observation?.study.phase]);
  const data=useMemo(()=>retentionMode?EMPTY_NATIVE:caFeatures(chunks,query,lens,metric,stride),[chunks,query,lens,metric,stride,retentionMode]);
  const rampLow=theme==='night'?'#213c37':'#fff0ce',rampHigh=theme==='night'?'#fff0cd':lens==='SNPP_VIIRS'?'#07565d':lens==='TERRA_MODIS'?'#4e346d':'#823816';
  const maximum=data.features.reduce((n,f)=>Math.max(n,f.properties.value),0);const sourceRecords=chunks.filter(c=>c.source===lens).flatMap(c=>c.cells).reduce((n,c)=>n+c[2].reduce((v,d)=>v+(query.flag==='D'?d[1]:query.flag==='N'?d[2]:d[1]+d[2]),0),0);
  useEffect(()=>{
    if(!ref.current)return;const controller=new AbortController();let geography=false,providerInstalled=false,lastGeoCheck=0,baseKind='pending';let baseLayers:string[]=[];
    let map:ml.Map;
    try{map=new ml.Map({container:ref.current,style:{version:8,sources:{},layers:[{id:'loading-water',type:'background',paint:{'background-color':'#dce7e4'}}]},center:[-100,60],zoom:2.8,minZoom:.5,maxZoom:13,attributionControl:false});}
    catch{setStatus('WebGL unavailable. Exact calendar, evidence and exports remain usable.');return;}
    mapRef.current=map;(ref.current as HTMLDivElement&{scientificMap:ml.Map}).scientificMap=map;
    map.addControl(new ml.NavigationControl({showCompass:false}),'top-right');map.addControl(new ml.ScaleControl({unit:'metric'}),'bottom-left');map.addControl(new ml.AttributionControl({compact:true}),'bottom-right');
    async function contextFirst(){try{
      const asset=catalog.artifacts['context.json'];const context=await verifiedJson<FeatureCollection>(catalog.root+'context.json',asset.sha256,controller.signal);if(controller.signal.aborted)return;
      const sources:ml.StyleSpecification['sources']={'ca-context':{type:'geojson',data:context,attribution:'Made with <a href="https://www.naturalearthdata.com/">Natural Earth</a> · 1:50 million'}};
      const layers:ml.LayerSpecification[]=[{id:'offline-water',type:'background',paint:{'background-color':'#dce7e4'}},{id:'offline-land',type:'fill',source:'ca-context',paint:{'fill-color':'#f4f0e5'}},{id:'offline-borders',type:'line',source:'ca-context',paint:{'line-color':'#8a9b91','line-width':1}}];
      // Verified geography first; provider detail is progressive, never coverage.
      setCoarse(true);map.setStyle({version:8,sources,layers},{diff:false});
      try{const r=await fetch('https://tiles.openfreemap.org/styles/liberty',{signal:controller.signal});if(!r.ok)throw Error('Provider style unavailable');const style=await r.json() as ml.StyleSpecification;if(controller.signal.aborted)return;
        // Retain local geography under tiles; remove the opaque provider background.
        providerInstalled=true;map.setStyle({...style,sources:{...sources,...style.sources},layers:[...layers,...style.layers.filter(l=>l.type!=='background')]},{diff:false});
      }catch{/* Already rendered, truthfully labeled coarse context survives. */}
    }catch{if(!controller.signal.aborted)setStatus('Geographic context unavailable; native summaries and export remain usable.');}}
    map.on('style.load',()=>{
      if(map.getSource('eg-ca'))return;memory.current.clear();
      baseLayers=(map.getStyle().layers??[]).filter(l=>'source' in l&&typeof l.source==='string'&&!l.source.startsWith('eg-')).map(l=>l.id);
      for(const layer of map.getStyle().layers??[])if(/^(landcover_|landuse_|park$|park_outline$|building-3d$|poi_)/.test(layer.id))map.setLayoutProperty(layer.id,'visibility','none');
      map.addSource('eg-ca',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
      map.addLayer({id:'eg-ca-fill',type:'fill',source:'eg-ca',paint:{'fill-color':'#b86a29','fill-opacity':.75,'fill-antialias':false}});
      map.addLayer({id:'eg-ca-border',type:'line',source:'eg-ca',paint:{'line-color':'#455b50','line-opacity':.18,'line-width':.4}});
      map.addSource('eg-ca-selection',{type:'geojson',data:{type:'FeatureCollection',features:[]}});map.addLayer({id:'eg-selection-outline',type:'line',source:'eg-ca-selection',paint:{'line-color':'#ffab5c','line-width':3}});
      map.addSource('eg-ca-support-scope',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
      map.addLayer({id:'eg-ca-support-scope',type:'fill',source:'eg-ca-support-scope',paint:{'fill-color':'#77807c','fill-opacity':.03}});
      map.addLayer({id:'eg-ca-support-boundary',type:'line',source:'eg-ca-support-scope',paint:{'line-color':'#655b6d','line-width':2,'line-dasharray':[3,2]}});
      map.addSource('eg-ca-support',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
      map.addLayer({id:'eg-ca-support',type:'circle',source:'eg-ca-support',paint:{'circle-radius':['case',['in',['get','mask'],['literal',[0,1,2,4]]],1.6,.7],'circle-opacity':['case',['==',['get','mask'],4],.95,.58],'circle-color':['match',['get','mask'],4,'#825b95',0,'#35393c',1,'#35393c',2,'#35393c','#868f8b']}});
      map.addSource('eg-ca-support-bins',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
      map.addLayer({id:'eg-ca-support-bins',type:'circle',source:'eg-ca-support-bins',paint:{'circle-radius':['interpolate',['linear'],['get','count'],0,4,100,9,1000,15],'circle-color':['case',['>', ['get','positive'],0],'#b34b19',['>', ['get','invalid'],0],'#805b92','#8a938f'],'circle-opacity':.64,'circle-stroke-width':1,'circle-stroke-color':'#f8f5ed'}});
      map.addLayer({id:'eg-ca-support-positive',type:'circle',source:'eg-ca-support',filter:['in',['get','mask'],['literal',[7,8,9]]],paint:{'circle-radius':4,'circle-color':'#b34b19','circle-stroke-color':'#fff7da','circle-stroke-width':1.2}});
      map.addSource('eg-triangle',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
      map.addLayer({id:'eg-triangle-lines',type:'line',source:'eg-triangle',filter:['==',['geometry-type'],'LineString'],paint:{'line-color':'#655e69','line-width':2,'line-dasharray':[3,2]}});
      map.addLayer({id:'eg-triangle-centers',type:'circle',source:'eg-triangle',filter:['==',['geometry-type'],'Point'],paint:{'circle-radius':['case',['==',['get','source'],'VNP14IMG'],7,5],'circle-color':['match',['get','source'],'VNP14IMG','#b34b19','VNP14','#684d7e','#0b5b5f'],'circle-stroke-color':'#fff5dc','circle-stroke-width':2}});
      map.addSource('eg-ca-centers',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
      map.addLayer({id:'eg-ca-centers',type:'circle',source:'eg-ca-centers',minzoom:6,paint:{'circle-radius':3.5,'circle-color':['get','color'],'circle-stroke-color':'#fff','circle-stroke-width':1}});
      for(const id of ['eg-retention-cells','eg-retention-marks','eg-research-aoi','eg-research-draft'])map.addSource(id,{type:'geojson',data:{type:'FeatureCollection',features:[]}});
      for(const g of GROUPS){const canvas=document.createElement('canvas');canvas.width=canvas.height=32;const ctx=canvas.getContext('2d')!;ctx.fillStyle=GROUP_COLORS[g];ctx.strokeStyle='#fff9e9';ctx.lineWidth=3;ctx.beginPath();if(g==='MODIS_ONLY')ctx.rect(5,5,22,22);else if(g==='SHARED'){ctx.moveTo(16,2);ctx.lineTo(30,16);ctx.lineTo(16,30);ctx.lineTo(2,16);}else{ctx.moveTo(16,2);ctx.lineTo(30,29);ctx.lineTo(2,29);}ctx.closePath();ctx.fill();ctx.stroke();map.addImage('retention-'+g,ctx.getImageData(0,0,32,32),{pixelRatio:2});}
      map.addLayer({id:'eg-retention-grid',type:'fill',source:'eg-retention-cells',paint:{'fill-color':['match',['get','group'],'MODIS_ONLY',GROUP_COLORS.MODIS_ONLY,'SHARED',GROUP_COLORS.SHARED,'VIIRS_ONLY',GROUP_COLORS.VIIRS_ONLY,GROUP_COLORS.MIXED],'fill-opacity':['case',['>', ['get','kept'],0],.48,.10]}});
      map.addLayer({id:'eg-retention-outline',type:'line',source:'eg-retention-cells',paint:{'line-color':'#29483f','line-width':.7,'line-opacity':.6}});
      map.addLayer({id:'eg-retention-glyphs',type:'symbol',source:'eg-retention-marks',layout:{'icon-image':['concat','retention-',['get','group']],'icon-size':.7,'icon-offset':['match',['get','group'],'MODIS_ONLY',['literal',[-11,0]],'VIIRS_ONLY',['literal',[11,0]],['literal',[0,0]]],'icon-allow-overlap':true,'icon-ignore-placement':true},paint:{'icon-opacity':['case',['>', ['get','kept'],0],1,.25]}});
      for(const id of ['eg-research-aoi','eg-research-draft'])map.addLayer({id,type:'line',source:id,paint:{'line-color':id==='eg-research-aoi'?'#253f37':'#9a6b2b','line-width':2,'line-dasharray':[3,2]}});
      applyCartography(map,latest.current.theme,memory.current);setReady(true);setEpoch(v=>v+1);
    });
    const checkGeography=()=>{if(!baseLayers.length)return;
      // First geography is checked during rendering; later provider/fallback
      // changes only at idle. Never repeatedly serialize base features while
      // a user is changing source policy or the GPU is painting an interaction.
      const f=map.queryRenderedFeatures({layers:baseLayers});if(f.length){if(!geography){geography=true;setStatus('Geographic basemap rendered');}const kind=providerInstalled&&f.some(f=>f.source!=='ca-context')?'detail':'coarse';if(kind!==baseKind){baseKind=kind;setCoarse(kind==='coarse');}}
    };
    map.on('render',()=>{if(!geography&&performance.now()-lastGeoCheck>=100){lastGeoCheck=performance.now();checkGeography();}});
    map.on('idle',checkGeography);
    map.on('zoomend',()=>setStride(map.getZoom()<4.8?4:map.getZoom()<6?2:1));
    map.on('mousemove','eg-ca-support',e=>{const p=e.features?.[0]?.properties;if(p)setHover(`native mask ${p.mask} · row ${p.line} / sample ${p.sample} · QA ${p.qa} · VZA ${Number(p.zenith).toFixed(2)}° · center, unqualified support`);});
    map.on('mouseleave','eg-ca-support',()=>setHover(''));
    map.on('click','eg-ca-support-bins',e=>{const f=e.features?.[0];if(f?.geometry.type==='Point'){setDrill(true);map.easeTo({center:f.geometry.coordinates as [number,number],zoom:11,duration:250});}});
    map.on('mousemove','eg-ca-support-bins',e=>{const p=e.features?.[0]?.properties;if(p)setHover(`${p.count} native centers · ${p.positive} positive · ${p.invalid} cloud/invalid · 5 km display bin, NOT footprint area`);});
    map.on('mouseleave','eg-ca-support-bins',()=>setHover(''));
    map.on('mousemove','eg-ca-support-positive',e=>{const p=e.features?.[0]?.properties;if(p)setHover(`Positive native thermal pixel · row ${p.line} / sample ${p.sample} · VZA ${Number(p.zenith).toFixed(2)}° · shared support unknown`);});
    map.on('mouseleave','eg-ca-support-positive',()=>setHover(''));
    map.on('mousemove','eg-triangle-centers',e=>{const p=e.features?.[0]?.properties;if(p)setHover(`${p.source} row ${p.row} / col ${p.col} · native mask ${p.mask} · QA ${p.qa} · center only; qualified support UNKNOWN`);});
    map.on('mouseleave','eg-triangle-centers',()=>setHover(''));
    map.on('click','eg-ca-fill',e=>{if(latest.current.drawing||latest.current.retentionMode)return;const p=e.features?.[0]?.properties;if(!p)return;if(Number(p.stride)>1){const center=caUnproject((Number(p.i)+Number(p.stride)/2)*10000,(Number(p.j)+Number(p.stride)/2)*10000);map.easeTo({center,zoom:6.5,duration:300});}else latest.current.onCell(String(p.cell));});
    map.on('mousemove','eg-ca-fill',e=>{const p=e.features?.[0]?.properties;if(p)setHover(`${p.value} · ${Number(p.stride)*10} km display tile · ${Number(p.stride)>1?'zoom in to inspect fixed 10 km cells':'click for exact source/cell/day evidence'}`);map.getCanvas().style.cursor='pointer';});
    map.on('mouseleave','eg-ca-fill',()=>{setHover('');map.getCanvas().style.cursor='';});
    map.on('click','eg-ca-centers',e=>{if(latest.current.drawing||latest.current.retentionMode)return;const p=e.features?.[0]?.properties;if(p)latest.current.onCell(String(p.cell));});
    map.on('mousemove','eg-ca-centers',e=>{const p=e.features?.[0]?.properties;if(p)setHover(`${p.utc} UTC · ${p.dn} · ${p.frp} MW · pixel center, not fire boundary`);});
    map.on('mouseleave','eg-ca-centers',()=>setHover(''));
    map.on('click',e=>{if(latest.current.drawing||!latest.current.retentionMode||!map.getLayer('eg-retention-glyphs'))return;const hits=map.queryRenderedFeatures(e.point,{layers:['eg-retention-glyphs','eg-retention-grid']});const hit=hits.find(f=>f.layer.id==='eg-retention-glyphs')??hits.find(f=>f.layer.id==='eg-retention-grid');if(hit?.properties?.cell)latest.current.onCell(String(hit.properties.cell));});
    map.on('mousemove','eg-retention-grid',e=>{if(!latest.current.retentionMode)return;const p=e.features?.[0]?.properties;if(p)setHover(`${p.cell}: ${p.keys} positive UTC cell-day keys; ${p['kept_'+latest.current.mask]} retained. Not coincident sensor support or physical fires.`);});
    map.on('mouseleave','eg-retention-grid',()=>setHover(''));
    const draft=(a:[number,number],b:[number,number])=>{const [w,e]=[Math.min(a[0],b[0]),Math.max(a[0],b[0])],[s,n]=[Math.min(a[1],b[1]),Math.max(a[1],b[1])];(map.getSource('eg-research-draft') as ml.GeoJSONSource)?.setData({type:'FeatureCollection',features:[{type:'Feature',properties:{state:'DRAFT; no changed measurements'},geometry:{type:'Polygon',coordinates:[[[w,s],[e,s],[e,n],[w,n],[w,s]]]}}]});};
    map.on('click',e=>{if(!latest.current.drawing)return;const p:[number,number]=[e.lngLat.lng,e.lngLat.lat];if(!drawFirst.current){drawFirst.current=p;draft(p,p);}else{const a=drawFirst.current;drawFirst.current=null;latest.current.onRectangle?.([Math.min(a[0],p[0]),Math.min(a[1],p[1]),Math.max(a[0],p[0]),Math.max(a[1],p[1])]);}});
    map.on('mousemove',e=>{if(latest.current.drawing&&drawFirst.current)draft(drawFirst.current,[e.lngLat.lng,e.lngLat.lat]);});
    void contextFirst();const resize=new ResizeObserver(()=>map.resize());resize.observe(ref.current);
    return ()=>{controller.abort();resize.disconnect();mapRef.current=null;map.remove();};
  },[catalog]);
  useEffect(()=>{const map=mapRef.current;if(!ready||!map?.getSource('eg-ca-centers'))return;(map.getSource('eg-ca-centers') as ml.GeoJSONSource).setData({type:'FeatureCollection',features:points.filter(p=>p.source===lens).map(p=>({type:'Feature',geometry:{type:'Point',coordinates:[p.lon,p.lat]},properties:{cell:p.cell,utc:p.utc,dn:p.dn,frp:p.native.frp,color:CA_COLORS[p.source]}}))});},[points,lens,ready,epoch]);
  useEffect(()=>{if(cohortId&&ready)fitEvidence();},[cohortId,ready]);
  useEffect(()=>{const map=mapRef.current;if(!ready||!map?.getLayer('eg-ca-fill'))return;const color=CA_COLORS[lens];map.setPaintProperty('eg-ca-fill','fill-color',['interpolate',['linear'],['get','value'],0,theme==='night'?'#213c37':'#fff0ce',Math.max(maximum*.25,.5),color,Math.max(maximum,1),theme==='night'?'#fff0cd':lens==='SNPP_VIIRS'?'#07565d':lens==='TERRA_MODIS'?'#4e346d':'#823816']);map.setPaintProperty('eg-ca-fill','fill-opacity',cohortId&&query.cell? .14:['interpolate',['linear'],['get','value'],0,.2,Math.max(maximum,.1),.92]);applyCartography(map,theme,memory.current);},[data,maximum,ready,epoch,lens,theme,query.cell,cohortId]);
  useEffect(()=>{const map=mapRef.current;if(!ready||!map?.getSource('eg-ca'))return;(map.getSource('eg-ca') as ml.GeoJSONSource).setData(data);(map.getSource('eg-ca-selection') as ml.GeoJSONSource).setData({...data,features:query.cell?[{type:'Feature',properties:{cell:query.cell},geometry:gridPolygon(Number(query.cell.split(':').at(-2)),Number(query.cell.split(':').at(-1)))}]:[]});},[data,ready,epoch,query.cell]);
  useEffect(()=>{const m=mapRef.current;if(!ready||!m?.getSource('eg-retention-cells'))return;(m.getSource('eg-retention-cells') as ml.GeoJSONSource).setData(retainedGeometry.cells);(m.getSource('eg-retention-marks') as ml.GeoJSONSource).setData(retainedGeometry.marks);for(const id of ['eg-retention-grid','eg-retention-outline','eg-retention-glyphs'])m.setLayoutProperty(id,'visibility',retentionMode?'visible':'none');if(!observation)for(const id of ['eg-ca-fill','eg-ca-border'])m.setLayoutProperty(id,'visibility',retentionMode?'none':'visible');},[retainedGeometry,retentionMode,ready,epoch,observation]);
  useEffect(()=>{const m=mapRef.current;if(!ready||!m?.getSource('eg-research-aoi'))return;const b=query.rect;(m.getSource('eg-research-aoi') as ml.GeoJSONSource).setData({type:'FeatureCollection',features:b?[{type:'Feature',properties:{meaning:'Research AOI, cell-center membership; NOT observation footprint'},geometry:{type:'Polygon',coordinates:[[[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]],[b[0],b[1]]]]}}]:[]});},[query.rect,ready,epoch]);
  useEffect(()=>{const m=mapRef.current;if(!ready||!m?.getLayer('eg-retention-grid'))return;m.setPaintProperty('eg-retention-grid','fill-opacity',['case',['>', ['get','kept_'+mask],0],.48,.10]);m.setPaintProperty('eg-retention-glyphs','icon-opacity',['case',['>', ['get','kept_'+mask],0],1,.25]);},[mask,ready,epoch]);
  useEffect(()=>{drawFirst.current=null;const m=mapRef.current;if(m?.getSource('eg-research-draft'))(m.getSource('eg-research-draft') as ml.GeoJSONSource).setData({type:'FeatureCollection',features:[]});if(m)m.getCanvas().style.cursor=drawing?'crosshair':'';},[drawing]);
  function fitEvidence(){const map=mapRef.current;if(!map)return;const points=retentionMode?retentionKeys.map(k=>caUnproject((k.i+.5)*10000,(k.j+.5)*10000)):chunks.flatMap(c=>c.cells.map(([i,j])=>caUnproject((i+.5)*10000,(j+.5)*10000)));if(!points.length)return;let w=180,s=90,e=-180,n=-90;for(const [x,y]of points){w=Math.min(w,x);e=Math.max(e,x);s=Math.min(s,y);n=Math.max(n,y);}map.fitBounds([[w-.3,s-.3],[e+.3,n+.3]],{padding:window.innerWidth>800?{left:330,right:70,top:80,bottom:100}:{left:22,right:36,top:110,bottom:65},duration:0,maxZoom:8});}
  useEffect(()=>{const map=mapRef.current;if(!ready||!map||observation)return;const b=query.rect??areaBounds[query.area];if(query.area==='canada'&&!query.rect)initiallyFramed.current=false;else map.fitBounds([[b[0],b[1]],[b[2],b[3]]],{padding:window.innerWidth>800?{left:330,right:70,top:80,bottom:110}:40,duration:0,maxZoom:6.8});},[query.area,query.rect,ready,observation]);
  useEffect(()=>{if(!observation&&ready&&query.area==='canada'&&!initiallyFramed.current&&(chunks.some(c=>c.cells.length)||retentionMode&&retentionKeys.length>0)){initiallyFramed.current=true;fitEvidence();}},[ready,chunks,query.area,observation,retentionMode,retentionKeys]);
  useEffect(()=>{const map=mapRef.current;if(!ready||!map||!query.cell||observation)return;const parts=query.cell.split(':'),i=Number(parts.at(-2)),j=Number(parts.at(-1));if(!Number.isFinite(i+j))return;const sw=caUnproject(i*10000,j*10000),ne=caUnproject((i+1)*10000,(j+1)*10000);map.fitBounds([[Math.min(sw[0],ne[0]),Math.min(sw[1],ne[1])],[Math.max(sw[0],ne[0]),Math.max(sw[1],ne[1])]],{padding:window.innerWidth>800?{left:330,right:70,top:100,bottom:100}:{top:115,bottom:210,left:30,right:45},maxZoom:9,duration:0});},[query.cell,ready,epoch,observation]);
  useEffect(()=>{const map=mapRef.current;if(!ready||!map?.getSource('eg-ca-support'))return;
    if(observation?.triangle&&!previousObservation.current)nativeCamera.current={center:map.getCenter(),zoom:map.getZoom(),bearing:map.getBearing(),pitch:map.getPitch(),padding:map.getPadding()};
    setDrill(false);
    const spec=observation?.study.splits[observation.split];
    (map.getSource('eg-ca-support') as ml.GeoJSONSource).setData({type:'FeatureCollection',features:observation?observation.points.map(p=>({type:'Feature',geometry:{type:'Point',coordinates:[p[2],p[3]]},properties:{line:p[0],sample:p[1],mask:p[4],qa:p[5],zenith:p[6]}})):[]});
    const b=spec?.aoi_wsen;
    (map.getSource('eg-ca-support-scope') as ml.GeoJSONSource).setData({type:'FeatureCollection',features:b?[{type:'Feature',properties:{support:'UNKNOWN_SUPPORT'},geometry:{type:'Polygon',coordinates:[[[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]],[b[0],b[1]]]]}}]:[]});
    for(const id of ['eg-ca-fill','eg-ca-border','eg-selection-outline','eg-ca-centers'])map.setLayoutProperty(id,'visibility',observation||retentionMode&&id!=='eg-selection-outline'?'none':'visible');
    if(retentionMode)map.moveLayer('eg-selection-outline');
    if(b)map.fitBounds([[b[0],b[1]],[b[2],b[3]]],{padding:window.innerWidth>800?{left:60,right:75,top:145,bottom:80}:{left:25,right:48,top:150,bottom:90},duration:0,maxZoom:9});
    else if(previousObservation.current){if(nativeCamera.current){map.jumpTo(nativeCamera.current);nativeCamera.current=null;}else fitEvidence();}
    previousObservation.current=!!observation;
  },[observation?.points,observation?.study,observation?.split,observation?.product,ready,epoch,retentionMode]);
  useEffect(()=>{const map=mapRef.current;if(!ready||!map?.getSource('eg-ca-support-bins'))return;const event=observation?.study.phase===8,triangle=!!observation?.triangle;(map.getSource('eg-ca-support-bins') as ml.GeoJSONSource).setData(bins);map.setLayoutProperty('eg-ca-support-bins','visibility',event&&!drill&&!triangle?'visible':'none');map.setLayoutProperty('eg-ca-support','visibility',triangle||event&&!drill?'none':'visible');map.setLayoutProperty('eg-ca-support-positive','visibility',event&&(!triangle||triangleRegion)?'visible':'none');},[bins,observation,drill,ready,epoch,triangleRegion]);
  useEffect(()=>{const map=mapRef.current;if(!ready||!map?.getSource('eg-triangle'))return;const selection=observation?.triangle;const p=selection?selectedTriangle(selection):null;
    const points=p?[{...p,source:'VNP14IMG',qa:p.raw_qa},{...p.viirs750,source:'VNP14'},{...p.aqua,source:'MYD14'}]:[];
    const features:GeoJSON.Feature[] = points.map(r=>({type:'Feature',geometry:{type:'Point',coordinates:[r.lon,r.lat]},properties:{source:r.source,row:r.row,col:r.col,mask:r.mask,qa:r.qa,selection:p?.id,support:'UNKNOWN_SUPPORT'}}));
    if(p)features.push({type:'Feature',geometry:{type:'LineString',coordinates:[[p.viirs750.lon,p.viirs750.lat],[p.lon,p.lat],[p.aqua.lon,p.aqua.lat]]},properties:{kind:'candidate associations; NOT footprint boundaries'}});
    (map.getSource('eg-triangle') as ml.GeoJSONSource).setData({type:'FeatureCollection',features});
    for(const layer of ['eg-ca-support-scope','eg-ca-support-boundary'])map.setLayoutProperty(layer,'visibility',p?'none':'visible');
    if(p&&triangleRegion){const b=observation!.study.splits[observation!.split].aoi_wsen;map.fitBounds([[b[0],b[1]],[b[2],b[3]]],{padding:innerWidth>800?{left:60,right:75,top:145,bottom:80}:{left:25,right:48,top:80,bottom:130},duration:0,maxZoom:9});}
    else if(p)map.jumpTo({center:[p.lon,p.lat],zoom:12,padding:{top:0,bottom:0,left:0,right:0}});
  },[observation,ready,epoch,triangleRegion]);
  return <div className="map-shell ca-map-shell"><div className="geographic-map" ref={ref} tabIndex={0} aria-label="Canada geographic map of native source thermal detections" data-testid="canada-map" data-ready={ready} data-basemap={coarse?'coarse-context':'detailed-provider'} data-source={observation?.triangle?'THREE_NATIVE_L2_PRODUCTS':lens} data-records={observation?.triangle?undefined:sourceRecords} data-observation={observation?observation.split+'-'+observation.product:''} data-mask-centers={observation?.points.length||0} data-render-mode={observation?.triangle?(triangleRegion?'triangular-context':'triangular-centers'):observation?.study.phase===8?(drill?'native':'5km-aggregate'):'native'} data-display-bins={bins.features.length} data-retention-keys={retentionMode?retentionKeys.length:undefined} data-grid-m="10000" data-display-m={stride*10000}/>
    {coarse&&!observation&&ready&&mapRef.current&&<FallbackPlaces map={mapRef.current} area={query.area}/>}
    <div className="cartography-tag"><i/>{theme==='night'?'Night':'Day'} cartography<span>visual theme only</span></div>
    <div className="camera-tools"><button onClick={fitEvidence}>Fit native evidence</button><button onClick={()=>{const b=areaBounds[query.area];mapRef.current?.fitBounds([[b[0],b[1]],[b[2],b[3]]],{padding:60,duration:0});}}>Fit full study area</button></div>
    {observation?.triangle&&ready&&mapRef.current&&<TriangleLabels map={mapRef.current} selection={observation.triangle}/>}
    {observation?.triangle&&<TriangleMapCard selection={observation.triangle} regional={triangleRegion} onContext={()=>setTriangleRegion(v=>!v)}/>}
    {observation&&!observation.triangle&&(observation.study.phase===8?<div className="p7-map-legend p8-map-legend" aria-label="Observation support legend"><strong>{observation.study.splits.development.products[observation.product].positive_mask_centers} positive thermal pixels · {observation.product}</strong><span><i style={{background:'#b34b19'}}/>Positive center <i style={{background:'#805b92'}}/>Cloud / invalid bin <i style={{background:'#8a938f'}}/>Support unknown</span><details><summary>Inspect centers & support</summary><button aria-pressed={drill} onClick={()=>setDrill(v=>!v)}>{drill?'Return to 5 km aggregates':'Inspect native centers'}</button><small>{drill?'Exact centers, not boundaries':`${bins.features.length} display bins retain all ${observation.points.length.toLocaleString()} centers; click a bin to drill down.`}</small><small>Gray box: study extent, not observation footprint. Bins summarize source-specific mask counts; neither bin size nor native mask land counts measure observation area. Valid single-sensor, shared and source-only support: UNKNOWN. All mask/geolocation pairs match exact named inputs. Cloud flags are fire-algorithm classes, not proof of cloud-free coverage.</small></details></div>:<div className="p7-map-legend" aria-label="Observation support legend"><strong>{observation.product} · {observation.study.splits[observation.split].date} UTC</strong><span><i style={{background:'#825b95'}}/>Native cloud center <i style={{background:'#35393c'}}/>Invalid / unprocessed</span><span><i style={{background:'#868f8b'}}/>Other mask centers · support unknown</span><small>Native centers: {observation.study.splits[observation.split].products[observation.product].mask_counts['5']||0} land · {observation.study.splits[observation.split].products[observation.product].mask_counts['4']||0} cloud.<br/>Gray box: study extent, not observation footprint.<br/>Verified, sensor-only and shared eligible area: unqualified.<br/>All displayed mask/geolocation pairs match exact input names.</small></div>)}
    <div className="map-legend quantitative-legend ca-legend"><strong>{CA_NAMES[lens]} · {query.pc}</strong><span className="ca-ramp" style={{background:`linear-gradient(90deg,${rampLow} 0%,${CA_COLORS[lens]} 25%,${rampHigh} 100%)`}}/><span>{maximum>0?<>0 → {maximum.toLocaleString()} {metric==='records'?'records':'10 km cell-days'} / {stride*10} km display tile</>:<>No selected records · valid observation unknown</>}</span><small>Native counting grid: 10 km equal-area</small><small>Source-specific scale · opportunity unknown</small><small>Map lens · CSV retains all checked source lanes</small>{stride>1&&<small>Click tile to zoom; inspect individual 10 km cells</small>}</div>
    {hover&&<div className="map-hover">{hover}</div>}<div className="map-status" role="status">{observation?.triangle&&coarse?'Coarse basemap · local detail unavailable':status}</div>{coarse&&<div className="coarse-context">Coarse Natural Earth context · not observation QA</div>}<div className="map-watermark">Canada · {query.month}{query.day?`-${String(query.day).padStart(2,'0')}`:''} UTC · NASA FIRMS / UMD</div>
  </div>;
}
