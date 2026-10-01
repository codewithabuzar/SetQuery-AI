\# SETQUERY AI



Satellite Change Detection \& Grounded AI Analysis



SetQuery AI is a geospatial analysis application for comparing satellite-derived land conditions across two time periods.



The project combines Google Earth Engine, Sentinel-2, Google Dynamic World, Landsat, deterministic analysis, and Gemini-based grounded question answering.



SetQuery AI automatically selects between two analysis methodologies depending on the requested dates:



\- Modern ML Mode — Sentinel-2 + Dynamic World

\- Historical Spectral Mode — Landsat spectral comparison



The system is intended for area-level environmental and land-cover analysis. Results are satellite-derived estimates and should not be treated as surveyed ground truth.



\---



\## Features



SetQuery AI currently supports:



\- Place-name geocoding

\- Before and after target dates

\- Configurable analysis radius

\- Automatic date-aware analysis routing

\- Sentinel-2 true-color satellite composites

\- Dynamic World machine-learning land-cover analysis

\- Temporal-consensus confidence filtering

\- Land-cover area estimates

\- Selected land-cover transition detection

\- High-confidence change-map visualization

\- Historical Landsat imagery

\- Historical NDVI analysis

\- Historical MNDWI analysis

\- Historical NDBI analysis

\- Comparable spatial coverage reporting

\- Landsat temporal source-support reporting

\- Deterministic automatic analysis summaries

\- Gemini grounded question answering

\- Deterministic local fallback when Gemini is unavailable

\- Streamlit session-state persistence

\- Request validation and error handling



\---



\# Analysis Modes



\## 1. Modern ML Mode



Modern requests use:



\- Sentinel-2 Surface Reflectance Harmonized

\- Google Dynamic World V1

\- Approximate spatial scale: 10 m



This mode provides categorical land-cover measurements and selected land-cover transitions.



The current application routes requests to Modern ML Mode when both target dates are within the configured modern analysis period.



\### Land-cover classes



Dynamic World provides probabilities for:



\- Water

\- Trees

\- Grass

\- Flooded vegetation

\- Crops

\- Shrub and scrub

\- Built

\- Bare

\- Snow and ice



SetQuery AI currently groups the following classes as vegetation:



\- Trees

\- Grass

\- Flooded vegetation

\- Crops

\- Shrub and scrub



Other primary grouped classes include:



\- Water

\- Built-up

\- Bare ground



\---



\## Dynamic World Temporal Consensus



SetQuery AI originally experimented with averaging Dynamic World probability vectors across the composite window.



Multi-location validation showed that probability averaging could substantially reduce comparable spatial coverage in temporally heterogeneous environments.



The production Modern ML workflow therefore uses temporal consensus instead.



For every Dynamic World observation at a pixel:



1\. The most probable class is determined.

2\. The maximum class probability must be at least 0.60 for that observation to be considered confident.



A pixel is considered valid within one comparison period only when:



\- At least 2 confident observations are available.

\- At least 50% of the observations actually available at that pixel are confident.

\- At least 60% of the confident classifications agree on the dominant class.



A pixel enters the BEFORE/AFTER comparison only when it passes these rules in both periods.



The 0.60 probability threshold was not lowered to increase coverage.



\---



\## Comparable Coverage



Comparable coverage is not accuracy.



It measures the percentage of the requested study area that passes the configured temporal-consensus requirements in both periods.



SetQuery AI currently interprets coverage as:



\- GOOD: 70% or greater

\- MODERATE: 40% to 69.9%

\- LIMITED: 20% to 39.9%

\- VERY LOW: below 20%



VERY LOW coverage is considered insufficient for broad area-level conclusions.



Results with limited coverage should only be interpreted as describing the comparable subset.



\---



\# Modern Transition Analysis



The Modern ML workflow currently measures selected transitions:



\- Vegetation → Built-up

\- Built-up → Vegetation

\- Bare → Built-up

\- Water → Non-water

\- Non-water → Water



Change-map colors are:



\- Red — Vegetation → Built-up

\- Green — Built-up → Vegetation

\- Yellow — Bare → Built-up

\- Blue — Non-water → Water

\- Orange — Water → Non-water



For visualization, transition pixels may be enlarged using image morphology so small changes are visible.



Numerical area statistics always use the original classification pixels.



\---



\# 2. Historical Spectral Mode



Earlier requests use a common Landsat-based methodology for both comparison periods.



Supported Landsat collections include:



\- Landsat 5

\- Landsat 7

\- Landsat 8

\- Landsat 9



The application dynamically checks which sensors contain observations for the requested location and time window.



Approximate optical spatial resolution used by the workflow:



\- 30 m



Historical mode does not pretend to be Dynamic World classification.



It performs spectral comparison using common Landsat optical bands.



\---



\## Historical Spectral Indices



\### NDVI



Normalized Difference Vegetation Index:



NDVI is used as a vegetation-related spectral indicator.



An increase in mean NDVI does not directly mean that a specific number of square kilometres became vegetation.



\### MNDWI



Modified Normalized Difference Water Index:



MNDWI is used as a water-related spectral indicator.



MNDWI differences should not automatically be interpreted as flooding or changes in exact water area.



\### NDBI



Normalized Difference Built-up Index:



NDBI is treated as a built/bare-related spectral indicator.



NDBI can respond to both built surfaces and bare ground.



Therefore SetQuery AI does not convert NDBI directly into exact built-up area or claim that an NDBI increase proves urbanization.



\---



\## Historical Source Support



Historical mode reports both:



\- Comparable spatial coverage

\- Temporal source-observation support



These are different concepts.



Temporal Landsat source support is currently categorized as:



\- GOOD: 5 or more observations

\- MODERATE: 3–4 observations

\- LIMITED: 2 observations

\- VERY LOW: 1 observation



Source support is not an accuracy percentage.



A period based on a single Landsat scene receives a strong warning because the result may be especially sensitive to that scene.



\---



\## Landsat 7 Limitation



Landsat 7 experienced a Scan Line Corrector failure in 2003.



Post-2003 Landsat 7 scenes can contain scan-line gaps.



SetQuery AI uses multi-scene compositing where possible, but gaps may still affect spatial completeness.



The application reports this limitation when Landsat 7 contributes to a historical comparison.



\---



\## Cross-Sensor Historical Comparison



Historical comparisons may use different Landsat generations.



For example:



\- BEFORE: Landsat 7

\- AFTER: Landsat 8 and Landsat 9



Although corresponding optical bands are mapped to a common schema, the sensors do not have perfectly identical spectral response characteristics.



Therefore:



\- Sensor bandpass differences can influence absolute index values.

\- Historical results should be interpreted as approximate spectral comparisons.

\- They are not exact surveyed land-cover measurements.



\---



\# Satellite Composite Windows



Selected dates are target dates.



They are not necessarily satellite acquisition dates.



SetQuery AI searches approximately 45 days before and 45 days after each target date and builds a composite from available observations.



The application requires sufficient separation between Modern ML target dates to reduce overlap between comparison windows.



Sentinel-2 true-color composites use:



\- B4 — Red

\- B3 — Green

\- B2 — Blue



The current Sentinel-2 cloud mask excludes selected Scene Classification Layer classes including:



\- Cloud shadow

\- Medium-probability cloud

\- High-probability cloud

\- Cirrus

\- Snow / ice



\---



\# AI Analysis



SetQuery AI contains two different uses of machine intelligence.



\## Dynamic World ML



Google Dynamic World is the machine-learning land-cover dataset used by the Modern ML analysis engine.



\## Gemini LLM



Gemini is used only to explain structured measurements and answer user questions.



Gemini does not perform the satellite classification.



Gemini receives structured analysis data rather than being asked to visually inspect satellite imagery.



The grounding rules prohibit Gemini from inventing:



\- Buildings

\- Roads

\- Construction projects

\- Fires

\- Flood events

\- Disasters

\- Causes of observed changes

\- Exact property-level findings



Gemini must also distinguish between:



\- Net class-area differences

\- Explicit detected transitions

\- Spectral-index changes

\- Comparable coverage

\- Accuracy



\---



\# AI Fallback



SetQuery AI includes a deterministic local fallback.



If Gemini is unavailable because of:



\- Quota limits

\- Rate limits

\- Temporary service capacity

\- Network problems



the application can still answer common questions using measured analysis results.



HTTP 429 quota/rate-limit responses do not trigger repeated immediate Gemini requests.



Temporary 503 failures may be retried before falling back.



\---



\# Architecture



```text

User

&#x20;|

&#x20;v

Streamlit

&#x20;|

&#x20;v

Nominatim Geocoding

&#x20;|

&#x20;v

Analysis Router

&#x20;|

&#x20;+--------------------------+

&#x20;|                          |

&#x20;v                          v

Modern ML               Historical Spectral

&#x20;|                          |

Sentinel-2                  Landsat 5/7/8/9

Dynamic World ML            Spectral comparison

Temporal consensus          NDVI / MNDWI / NDBI

\~10 m                       \~30 m

&#x20;|                          |

&#x20;+-------------+------------+

&#x20;              |

&#x20;              v

&#x20;       Structured Results

&#x20;              |

&#x20;       +------+------+

&#x20;       |             |

&#x20;       v             v

Deterministic       Gemini

Summary / Q\&A       Grounded Q\&A

&#x20;       |             |

&#x20;       +------+------+

&#x20;              |

&#x20;              v

&#x20;            User

```



\---



\# Main Technologies



\- Python

\- Streamlit

\- Google Earth Engine Python API

\- Google Dynamic World

\- Sentinel-2

\- Landsat

\- geopy / Nominatim

\- Google Gen AI Python SDK

\- Gemini

\- python-dotenv

\- pytest

\- Git / GitHub



\---



\# Project Structure



```text

SetQuery-AI/

|

├── app.py

├── analysis.py

├── analysis\_router.py

├── historical\_analysis.py

├── historical\_report.py

├── report.py

├── query.py

├── llm.py

├── requirements.txt

├── .gitignore

|

├── tests/

│   └── test\_core\_logic.py

|

└── validation/

&#x20;   ├── validate\_modern.py

&#x20;   ├── validate\_historical.py

&#x20;   ├── modern\_validation\_results.json

&#x20;   ├── historical\_validation\_results.json

&#x20;   ├── investigate\_final\_consensus.py

&#x20;   └── consensus\_change\_preview.py

```



Local-only backups and credentials should not be committed.



\---



\# Installation



\## 1. Clone the repository



```bash

git clone https://github.com/codewithabuzar/SetQuery-AI.git

cd SetQuery-AI

```



\## 2. Create a Python virtual environment



On Windows:



```powershell

python -m venv venv

```



If PowerShell blocks `Activate.ps1`, activation is not required. The virtual environment's Python executable can be used directly.



\## 3. Install dependencies



```powershell

.\\venv\\Scripts\\python.exe -m pip install -r requirements.txt

```



\---



\# Environment Variables



Create a local `.env` file.



Example:



```text

GEMINI\_API\_KEY=your\_api\_key\_here

GEMINI\_MODEL=your\_available\_gemini\_model

```



Never commit `.env`.



Never commit API keys or service-account private keys.



Gemini model availability can change, so the configured model should be one available to the user's Gemini API account.



\---



\# Google Earth Engine



SetQuery AI requires an Earth Engine-enabled Google Cloud project.



The current development project uses Earth Engine's non-commercial Community tier.



Users running their own copy should configure and authenticate Earth Engine for their own Google Cloud project.



The application must not rely on secrets committed to the repository.



\---



\# Run SetQuery AI



From the project directory on Windows:



```powershell

.\\venv\\Scripts\\python.exe -m streamlit run app.py

```



Streamlit normally opens:



```text

http://localhost:8501

```



Stop the server with:



```text

Ctrl+C

```



\---



\# Tests



The project includes non-network core-logic tests.



Run:



```powershell

$env:PYTHONPATH = (Get-Location).Path

.\\venv\\Scripts\\python.exe -m pytest -v

```



Current test suite:



```text

18 passed

```



Tests currently cover areas including:



\- Date-based analysis routing

\- Modern coverage categories

\- Historical coverage categories

\- Historical observation support

\- Conservative historical Q\&A

\- Low-coverage reporting

\- Coverage-versus-accuracy language

\- Temporal-consensus methodology reporting



Passing these tests does not establish satellite classification ground-truth accuracy.



\---



\# Validation



SetQuery AI has been sanity-tested across multiple environments.



These tests are not claims of surveyed ground-truth accuracy.



They are intended to identify:



\- Pipeline failures

\- Data-availability problems

\- Coverage weaknesses

\- Obviously implausible behavior

\- Visualization failures



\---



\## Modern ML Validation



Test configuration:



```text

Before target: 2022-09-15

After target:  2025-09-15

Radius:        5 km

```



Temporal-consensus comparable coverage:



```text

New Delhi     51.9%

Mumbai        58.4%

Ludhiana      77.1%

Dehradun      79.5%

Bhopal        70.5%

```



Before imagery, after imagery and change-map products generated successfully for all five validation environments.



\---



\## Why Temporal Consensus Was Introduced



The earlier probability-mean approach produced:



```text

New Delhi     17.3%

Mumbai        19.9%

Ludhiana      27.5%

Dehradun      77.0%

Bhopal        39.0%

```



Experiments showed that averaging Dynamic World probability vectors over time could suppress maximum class confidence in heterogeneous regions.



The temporal-consensus methodology improved comparable coverage without lowering the per-observation 0.60 probability threshold.



This does not prove higher classification accuracy.



It provides a more explicit temporal-consistency rule for deciding which pixels are included in the comparison.



\---



\## Historical Spectral Validation



Historical test configuration:



```text

Before target: 2012-09-15

After target:  2025-09-15

Radius:        5 km

```



Example validation results:



```text

New Delhi

Coverage: 99.9%

NDVI Δ:  +0.084

MNDWI Δ: -0.013

NDBI Δ:  -0.040



Mumbai

Coverage: 57.8%

NDVI Δ:  +0.078

MNDWI Δ: -0.012

NDBI Δ:  -0.041



Ludhiana

Coverage: 99.9%

NDVI Δ:  +0.054

MNDWI Δ: -0.052

NDBI Δ:  +0.016



Dehradun

Coverage: 99.8%

NDVI Δ:  -0.021

MNDWI Δ: +0.029

NDBI Δ:  +0.008



Bhopal

Coverage: 99.5%

NDVI Δ:  +0.088

MNDWI Δ: -0.013

NDBI Δ:  -0.028

```



These values are spectral sanity-test results.



They should not be interpreted as direct categorical land-cover-area changes.



Exact results also depend on the resolved study coordinates.



\---



\# Known Limitations



SetQuery AI should not claim reliable detection of:



\- Individual small houses

\- Individual trees

\- Tiny or narrow roads

\- Exact property-level changes

\- Exact surveyed area

\- Exact causes of change



Modern ML results can be influenced by:



\- Dynamic World classification uncertainty

\- Temporal variation

\- Composite timing

\- Clouds

\- Seasonality

\- Spatial resolution



Historical results can additionally be influenced by:



\- Landsat 7 scan-line gaps

\- Limited source observations

\- Cross-sensor spectral differences

\- 30 m spatial resolution

\- Spectral-index ambiguity



\---



\# What SetQuery AI Does Not Claim



SetQuery AI does not claim:



\- Survey-grade ground truth

\- 100% classification accuracy

\- Exact acquisition on the selected target date

\- Exact causation

\- Reliable individual-building change detection

\- That comparable coverage equals accuracy

\- That NDBI directly equals built-up area

\- That NDVI directly equals vegetation area

\- That MNDWI directly equals water area



\---



\# Performance Note



The current prototype reconstructs some Google Earth Engine products when producing statistics, imagery and visualization outputs.



A future optimization can prepare shared Earth Engine collections/composites once per request and reuse them across result generation.



This optimization was intentionally deferred after methodology validation to avoid unnecessary regression risk before project finalization.



\---



\# Future Improvements



Potential future work includes:



\- Shared Earth Engine computation per request

\- More extensive automated integration testing

\- Interactive geographic location picker

\- Improved before/after comparison controls

\- Additional statistical visualizations

\- Better mobile layout

\- Historical cross-sensor harmonization research

\- Optional DEM-based 3D terrain visualization

\- Public deployment



Any future 3D terrain implementation should use an actual elevation dataset rather than treating Sentinel-2 imagery as elevation data.



\---



\# Project Status



SetQuery AI is currently a validated functional prototype.



Core analysis functionality is feature-frozen while the project moves through:



1\. Documentation

2\. Final UI refinement

3\. Configuration/security review

4\. Deployment preparation



\---



\# Disclaimer



SetQuery AI is an educational geospatial analysis project.



Results are derived from satellite imagery, machine-learning datasets, spectral indices and automated processing.



They should not be treated as a replacement for professional surveying, official land records, field verification or authoritative environmental assessment.

