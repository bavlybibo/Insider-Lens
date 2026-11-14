export const REFERENCES = {
  firms: 'https://firms.modaps.eosdis.nasa.gov/',
  archive: 'https://firms.modaps.eosdis.nasa.gov/download/',
  readme: 'https://firms.modaps.eosdis.nasa.gov/download/Readme.txt',
  swaths: 'https://science.data.nasa.gov/features-events/data-software-highlights-june-2026',
  snpp: 'https://ladsweb.modaps.eosdis.nasa.gov/alerts-and-issues/199913',
  snppFinal: 'https://www.nesdis.noaa.gov/news/update-4-cessation-of-suomi-national-polar-orbiting-partnership-s-npp-data-users-november-02-2026-1540-utc-and-decommissioning-issued-november-2-2026-1800-utc',
  viirs: 'https://www.earthdata.nasa.gov/s3fs-public/2025-06/VIIRS_C2_AF-375m_User_Guide_1.2.pdf',
};
export function observationSupport(evidence: { swath?: boolean; mask?: boolean; qa?: boolean; geolocation?: boolean; qualified?: boolean }) {
  // File/geometry presence cannot establish valid observation quality. Qualification
  // must be an independent support product, which this release does not contain.
  if (!evidence.mask || !evidence.qa || !evidence.geolocation || !evidence.qualified) return 'OBSERVATION_UNKNOWN';
  return 'SUPPORT_PRODUCT_REQUIRES_SCOPE_REVIEW';
}
export function deliveryRegime(platform: string, date: string) {
  if (platform === 'NOAA20' || platform === 'NOAA21') return 'NEW_REGIME_NOT_QUALIFIED';
  if (platform === 'SNPP') {
    if (date === '2026-11' || date === '2026-11-02') return 'PERIOD_SPANS_DELIVERY_TRANSITION';
    if (date >= '2026-11-02T15:40:00Z') return 'NEW_DELIVERY_ENDED_HISTORICAL_ARCHIVE_REMAINS';
  }
  return 'HISTORICAL_PLATFORM_RECORD_NOT_A_COVERAGE_GUARANTEE';
}
