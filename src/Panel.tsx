import { useEffect, useRef, useState, type ReactNode } from 'react';
export function useMobile() {
  const [mobile, setMobile] = useState(() => matchMedia('(max-width: 800px)').matches);
  useEffect(() => { const query = matchMedia('(max-width: 800px)'); const change = () => setMobile(query.matches);
    query.addEventListener('change', change); return () => query.removeEventListener('change', change); }, []);
  return mobile;
}
export function Panel({ id, title, open, close, children, side }: { id: string; title: string; open: boolean; close: () => void; children: ReactNode; side: 'left' | 'right' }) {
  const mobile = useMobile();
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { if (!mobile || !dialog.current) return; if (open && !dialog.current.open) dialog.current.showModal();
    if (!open && dialog.current.open) dialog.current.close(); }, [open, mobile]);
  const content = <><div className="panel-title"><h2 id={`${id}-title`}>{title}</h2><button onClick={close} aria-label={`Close ${title}`} className="icon-button">×</button></div><div className="panel-scroll">{children}</div></>;
  if (mobile) return <dialog ref={dialog} id={id} className={`sheet sheet-${side}`} aria-labelledby={`${id}-title`} onCancel={close} onClose={close}>{content}</dialog>;
  return <aside id={id} className={`workspace-panel panel-${side}`} aria-labelledby={`${id}-title`} hidden={!open} onKeyDown={e => { if (e.key === 'Escape') close(); }}>{content}</aside>;
}
