import {test,expect} from '@playwright/test';
import {applyCartography,densityOpacity} from '../src/cartography';

test('night cartography changes geographic paint and restores day paint without replacing sources',()=>{
  const layers=[
    {id:'background',type:'background',paint:{'background-color':'#ffffff'}},
    {id:'water',type:'fill',paint:{'fill-color':'#e1e9e5'}},
    {id:'land',type:'fill',paint:{'fill-color':['match',['get','kind'],'park','#eee','#fff']}},
    {id:'place',type:'symbol',layout:{'text-field':['get','name']},paint:{'text-color':'#123','text-halo-color':'#fff'}},
    {id:'eg-density-fill',type:'fill',paint:{'fill-color':'#e89937','fill-opacity':.75}},
  ];
  const original=structuredClone(layers),source={data:'immutable evidence'},view={center:[-8,40],zoom:9};
  const map={getStyle:()=>({layers,sources:{science:source}}),getLayer:()=>undefined,
    getPaintProperty:(id:string,key:string)=>(layers.find(l=>l.id===id)!.paint as any)[key],
    setPaintProperty:(id:string,key:string,value:any)=>{(layers.find(l=>l.id===id)!.paint as any)[key]=value;}};
  const memory=new Map();applyCartography(map as any,'night',memory);
  expect(layers[0].paint['background-color']).toBe('#0b2429');expect(layers[1].paint['fill-color']).toBe('#0b2429');
  expect(layers[4]).toEqual(original[4]);expect(source).toEqual({data:'immutable evidence'});expect(view.zoom).toBe(9);
  applyCartography(map as any,'day',memory);expect(layers).toEqual(original);
});

test('density opacity is finite, monotonic and bound to the same numerical source scale',()=>{
  for(const maximum of [0,.00001,3.416]){
    const expression=densityOpacity(maximum),stops=expression.slice(3) as number[];
    expect(expression.slice(0,3)).toEqual(['interpolate',['linear'],['get','value']]);
    for(let i=0;i<stops.length;i+=2){expect(Number.isFinite(stops[i])).toBe(true);expect(stops[i+1]).toBeGreaterThanOrEqual(0);expect(stops[i+1]).toBeLessThanOrEqual(1);if(i) {expect(stops[i]).toBeGreaterThan(stops[i-2]);expect(stops[i+1]).toBeGreaterThanOrEqual(stops[i-1]);}}
  }
});
