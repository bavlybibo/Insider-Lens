# Technical question for NASA LP DAAC / LAADS — DRAFT, NOT SENT

Subject: VNP14.002 NPP_PR14 1.6.1 / PGE530 2.0.4 QA applicability and response geometry

We are examining `VNP14.A2023164.1042.002.2023164205253.nc` (SHA256 `022e9ccdc4444aba6219a577c348875977f92c9680c97ebd27c3f617daab807e`), AlgorithmType SCI, AlgorithmVersion NPP_PR14 1.6.1, PGEVersion2.0.4. Its fire-mask legend explicitly defines0–9, but `algorithm QA` has only units="bit field" and no bit legend. Sixteen fixed candidate centers contain mask5 and QAword2. We do not currently decode that word or call them valid shared non-detections.

1. Please identify the version-controlled bit definitions or processing specification explicitly applicable to this exact SP Collection002 production. Does the 2019 NPP_PR14 V1.4.3 C1 specification apply without changes? Please supply a citable version/applicability statement, including input-radiance/geolocation quality, trim/bowtie, cloud, background and rejection tests.
2. The fire file names `VNP03MOD.A2023164.1042.002.2023164194353.nc` as InputFileGeo. `VNP03MODLL.A2023164.1042.002.2023183103833.h5` names the same input. We independently compared every latitude/longitude/height value (10,393,600 per variable); no stored differences were found. Is this the intended full/light compatibility? MODLL supplies no viewing-angle or quality arrays; is the exact named full MOD the intended source for those additional fields?
3. Which versioned detector response, aggregation/bowtie mapping and band-registration uncertainty should be used for a physically justified I4/I5/M13 thermal-response overlap test at IMG rows877–888, samples4534–4548 / MOD rows438–444, samples2267–2274? We have exact centers and scan intervals but no certified footprint or absolute registration bound. We are not assuming2x2 containment or using nominal-resolution rectangles.

Companion imagery: `VNP14IMG.A2023164.1042.002.2024079133754.nc`, NPP_PR14IMG3.1.6/PGE2.0.13, and `VNP03IMG.A2023164.1042.002.2023164194353.nc`. Same named M13 input: `VNP02CCMOD.A2023164.1042.002.2023164204525.nc`. We recognize the different production vintages and do not attribute the contrast solely to resolution.

This is a technical clarification request, not a request for NASA endorsement. No credentials are included. Team review and sending are outside this draft artifact.
