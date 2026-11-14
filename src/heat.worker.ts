import { density } from './atlas';
import type { Detection } from './science';
self.onmessage=(event:MessageEvent<{token:string;records:Detection[];bandwidth:5|10;bbox:number[]}>)=>{
  const {token,records,bandwidth,bbox}=event.data;
  try{self.postMessage({token,data:density(records,bandwidth,bbox)});}catch{self.postMessage({token,data:{type:'FeatureCollection',features:[]},error:'Density calculation unavailable; native evidence remains available.'});}
};
