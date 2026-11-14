import { useCallback, useEffect, useRef, useState } from 'react';
import { SOURCES, selectedMonth, selectionId, type Release, type Selection, type SourceId } from './science';

export function readSelection(search: string, release: Release): Selection {
  const params = new URLSearchParams(search);
  const requested = [...new Set((params.get('sources') ?? 'AQUA_MODIS,SNPP_VIIRS').split(','))];
  const sources = requested.filter((s): s is SourceId => SOURCES.includes(s as SourceId));
  const candidateMonth = params.get('month') ?? release.months[0];
  const month = /^(20[0-2]\d)-(0[1-9]|1[0-2])$/.test(candidateMonth) ? candidateMonth : release.months[0];
  const candidateDay = params.get('day');
  const validDay = candidateDay && /^\d{4}-\d{2}-\d{2}$/.test(candidateDay) && candidateDay.startsWith(month) &&
    !Number.isNaN(Date.parse(`${candidateDay}T00:00:00Z`)) && new Date(`${candidateDay}T00:00:00Z`).toISOString().slice(0, 10) === candidateDay;
  const candidateCell = params.get('cell');
  const cell = release.cells.features.some(f => f.properties.cell === candidateCell) ? candidateCell : null;
  const dn = params.get('dn');
  return { sources: sources.length ? sources : ['AQUA_MODIS', 'SNPP_VIIRS'], month, day: validDay ? candidateDay : null,
    cell, daynight: dn === 'D' || dn === 'N' ? dn : 'ALL' };
}
export function selectionSearch(selection: Selection): string {
  const params = new URLSearchParams({ month: selectedMonth(selection), sources: [...selection.sources].sort().join(','), dn: selection.daynight ?? 'ALL' });
  if (selection.day) params.set('day', selection.day);
  if (selection.cell) params.set('cell', selection.cell);
  return `?${params.toString()}`;
}
export function useInvestigationSelection(release: Release) {
  const [selection, commit] = useState(() => readSelection(location.search, release));
  const current = useRef(selection);
  useEffect(() => {
    history.replaceState(null, '', selectionSearch(current.current));
    const pop = () => { const value = readSelection(location.search, release); current.current = value; commit(value); };
    addEventListener('popstate', pop);
    return () => removeEventListener('popstate', pop);
  }, [release]);
  const update = useCallback((change: Selection | ((s: Selection) => Selection)) => {
    const next = typeof change === 'function' ? change(current.current) : change;
    if (selectionId(release.releaseId, next) === selectionId(release.releaseId, current.current)) return;
    current.current = next; history.pushState(null, '', selectionSearch(next)); commit(next);
  }, [release]);
  return [selection, update] as const;
}
