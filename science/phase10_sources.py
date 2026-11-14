"""Versioned source applicability, explicit gaps and unsent support question."""
import json
from phase10_contract import ROOT,OUT,sha,immutable
def run():
    refs=[
      ('data/acquisition/phase9/references/VNP14-C2-CMR.json','https://cmr.earthdata.nasa.gov/search/collections.umm_json?concept_id=C2545314536-LPCLOUD','NASA CMR VNP14.002 collection metadata, preserved Phase9 response','Recommends/requires MODLL; links C1 guide/specification, not exact C2 QA certification'),
      ('data/acquisition/phase10/MODLL_CMR.json','https://cmr.earthdata.nasa.gov/search/granules.json?short_name=VNP03MODLL&version=002&temporal=2023-06-13T10%3A42%3A00Z%2C2023-06-13T10%3A43%3A00Z&page_size=10','NASA CMR granule metadata','One exact1042 acquisition selected, adjacent1036 granule excluded'),
      ('data/acquisition/phase10/references/VIIRS_GEO_ATBD_B.pdf','https://www.star.nesdis.noaa.gov/jpss/documents/ATBD/D0001-M01-S01-004_JPSS_ATBD_VIIRS-Geolocation_B.pdf','NOAA/NASA JPSS geolocation ATBD Revision B, effective2022-07-22','Printed pp49–50 / PDF74–75 visually checked: detector sampling/aggregation, not exact thermal PSF certificate'),
      ('data/acquisition/phase10/references/Tilton2016.html','https://pmc.ncbi.nlm.nih.gov/articles/PMC6062855/','Tilton,Lin,Tan: IEEE JSTARS10(3),2017; DOI10.1109/JSTARS.2016.2601561','TableI one-based aggregation-zone columns; HSI denotes sampling interval, not exact operational response boundary; mean-orbit historical measurements'),
      ('data/acquisition/phase10/references/Tilton2019.html','https://pmc.ncbi.nlm.nih.gov/articles/PMC7340089/','Tilton etal., IEEE JSTARS12(11),2019; DOI10.1109/JSTARS.2019.2949677','SectionIII uses a first-order PSF approximation; along-scan overlap reinforces distinction from cell polygons; not exact per-pixel thermal response validation'),
      ('data/acquisition/phase8/references/VIIRS_L1B_C2.pdf','https://ladsweb.modaps.eosdis.nasa.gov/api/v2/content/archives/Document%20Archive/Science%20Data%20Product%20Documentation/NASA_VIIRS_L1B_UG_August_2021.pdf','NASA VIIRS C2 L1B user guide August2021, preserved Phase8','Source-specific navigation, scan-quality/time; not VNP14 C2 algorithm-QA definitions'),
      ('data/acquisition/phase7/references/VIIRS_C2_375_User_Guide.pdf','https://ladsweb.modaps.eosdis.nasa.gov/archive/Document%20Archive/Science%20Data%20Product%20Documentation/VIIRS_C2_AF-375m_User_Guide_1.2.pdf','NASA C2 375m user guide1.2 June2025','IMG QA and FRP allocation only; not750m bit definitions')]
    sources=[{'file':file,'sha256':sha(ROOT/file),'bytes':(ROOT/file).stat().st_size,'url':url,'version_authority':version,'scope':scope} for file,url,version,scope in refs]
    attempts=[{'url':'https://ladsweb.modaps.eosdis.nasa.gov/filespec/VIIRS/2/VNP14','status':404,'conclusion':'No C2 specification obtained at this guessed route; not evidence that none exists'},
       {'url':'https://www.earthdata.nasa.gov/data/catalog/lpcloud-vnp14-002','status':403,'conclusion':'Public web fetch failed; preserved official CMR metadata used, no authentication inference'},
       {'url':'https://www.earthdata.nasa.gov/data/alerts-outages/viirs-version-2-thermal-anomalies-fire-products-released','status':403,'conclusion':'Public release page inaccessible through web fetch; do not fabricate content'},
       {'url':'https://ladsweb.modaps.eosdis.nasa.gov/filespec/VIIRS/1/VNP14','status':200,'conclusion':'C1 specification NPP_PR14V1.4.3 dated2019-01-25; not promoted to exact1.6.1'}]
    immutable(OUT/'SOURCE_QUALIFICATION.json',{'state':'BOUNDED_SEARCH_COMPLETE','sources':sources,'unsuccessful_or_inapplicable_sources':attempts,'new_science_files':1,'new_science_bytes':73370707,'modll_verdict':'Exact full-to-light coordinates/height equivalent; angles/QA not present in MODLL','fire_mask_verdict':'VERIFIED from exact acquired file legend','algorithm_qa_verdict':'UNRESOLVED for exact750m C2 algorithm/PGE','footprint_verdict':'UNRESOLVED; instrument geometry is not sufficient for absolute per-pixel response/registration bounds','stop':'Stop after one exact companion granule and targeted primary sources. No new event/pass or calibration sample.'})
    question='''# Technical question for NASA LP DAAC / LAADS — DRAFT, NOT SENT

Subject: VNP14.002 NPP_PR14 1.6.1 / PGE530 2.0.4 QA applicability and response geometry

We are examining `VNP14.A2023164.1042.002.2023164205253.nc` (SHA256 `022e9ccdc4444aba6219a577c348875977f92c9680c97ebd27c3f617daab807e`), AlgorithmType SCI, AlgorithmVersion NPP_PR14 1.6.1, PGEVersion2.0.4. Its fire-mask legend explicitly defines0–9, but `algorithm QA` has only units="bit field" and no bit legend. Sixteen fixed candidate centers contain mask5 and QAword2. We do not currently decode that word or call them valid shared non-detections.

1. Please identify the version-controlled bit definitions or processing specification explicitly applicable to this exact SP Collection002 production. Does the 2019 NPP_PR14 V1.4.3 C1 specification apply without changes? Please supply a citable version/applicability statement, including input-radiance/geolocation quality, trim/bowtie, cloud, background and rejection tests.
2. The fire file names `VNP03MOD.A2023164.1042.002.2023164194353.nc` as InputFileGeo. `VNP03MODLL.A2023164.1042.002.2023183103833.h5` names the same input. We independently compared every latitude/longitude/height value (10,393,600 per variable); no stored differences were found. Is this the intended full/light compatibility? MODLL supplies no viewing-angle or quality arrays; is the exact named full MOD the intended source for those additional fields?
3. Which versioned detector response, aggregation/bowtie mapping and band-registration uncertainty should be used for a physically justified I4/I5/M13 thermal-response overlap test at IMG rows877–888, samples4534–4548 / MOD rows438–444, samples2267–2274? We have exact centers and scan intervals but no certified footprint or absolute registration bound. We are not assuming2x2 containment or using nominal-resolution rectangles.

Companion imagery: `VNP14IMG.A2023164.1042.002.2024079133754.nc`, NPP_PR14IMG3.1.6/PGE2.0.13, and `VNP03IMG.A2023164.1042.002.2023164194353.nc`. Same named M13 input: `VNP02CCMOD.A2023164.1042.002.2023164204525.nc`. We recognize the different production vintages and do not attribute the contrast solely to resolution.

This is a technical clarification request, not a request for NASA endorsement. No credentials are included. Team review and sending are outside this draft artifact.
'''
    path=OUT/'NASA_SUPPORT_QUESTION.md';raw=question.encode();assert not path.exists() or path.read_bytes()==raw
    if not path.exists():path.write_bytes(raw)
    print('Version-qualified source ledger and unsent technical question written')
if __name__=='__main__':run()
