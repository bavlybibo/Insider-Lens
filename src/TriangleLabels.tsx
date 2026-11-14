import {useEffect,useState} from 'react';
import type {Map} from 'maplibre-gl';
import {selectedTriangle,type TriangleSelection} from './triangular';
export function TriangleLabels({map,selection}:{map:Map;selection:TriangleSelection}){
 const [positions,setPositions]=useState<{label:string;left:number;top:number;detail:string}[]>([]);
 useEffect(()=>{const p=selectedTriangle(selection);function place(){const container=map.getContainer(),w=container.clientWidth,h=container.clientHeight;const candidates=[{...p,label:'375 m positive',offset:-54},{...p.viirs750,label:'750 m candidate',offset:-110},{...p.aqua,label:'Aqua candidate',offset:46}];const next=candidates.map(r=>{const pt=map.project([r.lon,r.lat]);return {label:r.label,left:Math.max(8,Math.min(w-122,pt.x-56)),top:Math.max(70,Math.min(h-145,pt.y+r.offset)),detail:`${r.label}: row ${r.row}, column ${r.col}, native mask ${r.mask}. Center only; shared support unknown.`};}).sort((a,b)=>a.top-b.top);for(let i=1;i<next.length;i++)if(next[i].top<next[i-1].top+42)next[i].top=next[i-1].top+42;setPositions(next);}
 place();map.on('move',place);map.on('resize',place);return()=>{map.off('move',place);map.off('resize',place);};},[map,selection]);
 return <div className="triangle-source-labels" role="group" aria-label="Three source-center labels">{positions.map(p=><button key={p.label} style={{left:p.left,top:p.top}} aria-label={p.detail} title={p.detail} onClick={e=>{e.currentTarget.classList.toggle('expanded');e.currentTarget.style.left=Math.min(Number.parseFloat(e.currentTarget.style.left),map.getContainer().clientWidth-198)+'px';}}>{p.label}<small>{p.detail}</small></button>)}</div>;
}
