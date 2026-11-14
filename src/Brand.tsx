/** Public identity only. Historical EmberGuard scientific identifiers stay immutable. */
export function Brand({onHome}:{onHome?:()=>void}) {
 return <a className="brand" href="/" aria-label="Insider Lens home" onClick={onHome?e=>{e.preventDefault();onHome();}:undefined}>
  <svg width="23" height="25" viewBox="0 0 28 28" fill="none" aria-hidden="true"><circle cx="14" cy="14" r="10" stroke="currentColor" strokeWidth="1.5"/><circle cx="14" cy="14" r="4" stroke="currentColor" strokeWidth="1.5"/><path d="M14 1v6m0 14v6M1 14h6m14 0h6" stroke="currentColor" strokeWidth="1.5"/></svg>
  <span>Insider<span className="brand-light"> Lens</span></span>
 </a>;
}
