#!/usr/bin/env python3
"""
Test FMP Workflows with ITAN ETF Current Basket
Tests all FMP-enhanced workflows using ITAN's actual holdings.
"""

import os
import sys
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

# Load .env file if it exists
env_file = Path(__file__).parent.parent.parent / '.env'
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# ITAN ETF Current Basket (from user's data)
ITAN_HOLDINGS = [
    {"ticker": "AAL", "name": "American Airlines Group Inc", "cusip": "02376R102", "quantity": 17056, "price": 15.33, "market_value": 261468, "weight": 0.39},
    {"ticker": "ACI", "name": "Albertsons Cos Inc", "cusip": "013091103", "quantity": 12641, "price": 17.17, "market_value": 217046, "weight": 0.33},
    {"ticker": "ACM", "name": "AECOM", "cusip": "00766T100", "quantity": 2542, "price": 95.33, "market_value": 242329, "weight": 0.37},
    {"ticker": "ACN", "name": "Accenture PLC", "cusip": "G1151C101", "quantity": 3793, "price": 268.30, "market_value": 1017662, "weight": 1.54},
    {"ticker": "ADBE", "name": "Adobe Inc", "cusip": "00724F101", "quantity": 1867, "price": 349.99, "market_value": 653431, "weight": 0.99},
    {"ticker": "AGCO", "name": "AGCO Corp", "cusip": "001084102", "quantity": 1676, "price": 104.32, "market_value": 174840, "weight": 0.26},
    {"ticker": "AKAM", "name": "Akamai Technologies Inc", "cusip": "00971T101", "quantity": 3028, "price": 87.25, "market_value": 264193, "weight": 0.40},
    {"ticker": "ALK", "name": "Alaska Air Group Inc", "cusip": "011659109", "quantity": 3386, "price": 50.30, "market_value": 170316, "weight": 0.26},
    {"ticker": "ALL", "name": "Allstate Corp/The", "cusip": "020002101", "quantity": 2191, "price": 208.15, "market_value": 456057, "weight": 0.69},
    {"ticker": "ALLY", "name": "Ally Financial Inc", "cusip": "02005N100", "quantity": 5363, "price": 45.29, "market_value": 242890, "weight": 0.37},
    {"ticker": "ALV", "name": "Autoliv Inc", "cusip": "052800109", "quantity": 1256, "price": 118.70, "market_value": 149087, "weight": 0.23},
    {"ticker": "AMZN", "name": "Amazon.com Inc", "cusip": "023135106", "quantity": 12124, "price": 230.82, "market_value": 2798462, "weight": 4.22},
    {"ticker": "ANF", "name": "Abercrombie & Fitch Co", "cusip": "002896207", "quantity": 1519, "price": 125.87, "market_value": 191197, "weight": 0.29},
    {"ticker": "APTV", "name": "Aptiv PLC", "cusip": "G3265R107", "quantity": 2740, "price": 76.09, "market_value": 208487, "weight": 0.31},
    {"ticker": "BA", "name": "Boeing Co/The", "cusip": "097023105", "quantity": 3583, "price": 217.12, "market_value": 777941, "weight": 1.17},
    {"ticker": "BAH", "name": "Booz Allen Hamilton Holding Corp", "cusip": "099502106", "quantity": 3082, "price": 84.36, "market_value": 259998, "weight": 0.39},
    {"ticker": "BAX", "name": "Baxter International Inc", "cusip": "071813109", "quantity": 13016, "price": 19.11, "market_value": 248736, "weight": 0.38},
    {"ticker": "BBY", "name": "Best Buy Co Inc", "cusip": "086516101", "quantity": 4301, "price": 66.93, "market_value": 287866, "weight": 0.43},
    {"ticker": "BDX", "name": "Becton Dickinson & Co", "cusip": "075887109", "quantity": 2639, "price": 194.07, "market_value": 512151, "weight": 0.77},
    {"ticker": "BIIB", "name": "Biogen Inc", "cusip": "09062X103", "quantity": 2072, "price": 175.99, "market_value": 364651, "weight": 0.55},
    {"ticker": "BIO", "name": "Bio-Rad Laboratories Inc", "cusip": "090572207", "quantity": 629, "price": 302.99, "market_value": 190581, "weight": 0.29},
    {"ticker": "BMY", "name": "Bristol-Myers Squibb Co", "cusip": "110122108", "quantity": 12867, "price": 53.31, "market_value": 685940, "weight": 1.04},
    {"ticker": "BWA", "name": "BorgWarner Inc", "cusip": "099724106", "quantity": 4302, "price": 45.06, "market_value": 193848, "weight": 0.29},
    {"ticker": "CACI", "name": "CACI International Inc", "cusip": "127190304", "quantity": 467, "price": 532.81, "market_value": 248822, "weight": 0.38},
    {"ticker": "CAH", "name": "Cardinal Health Inc", "cusip": "14149Y108", "quantity": 1867, "price": 204.99, "market_value": 382715, "weight": 0.58},
    {"ticker": "CAR", "name": "Avis Budget Group Inc", "cusip": "053774105", "quantity": 860, "price": 128.32, "market_value": 110355, "weight": 0.17},
    {"ticker": "CHTR", "name": "Charter Communications Inc", "cusip": "16119P108", "quantity": 1928, "price": 208.75, "market_value": 402470, "weight": 0.61},
    {"ticker": "CIEN", "name": "Ciena Corp", "cusip": "171779309", "quantity": 1978, "price": 233.87, "market_value": 462595, "weight": 0.70},
    {"ticker": "CMCSA", "name": "Comcast Corp", "cusip": "20030N101", "quantity": 21505, "price": 29.89, "market_value": 642784, "weight": 0.97},
    {"ticker": "CMI", "name": "Cummins Inc", "cusip": "231021106", "quantity": 1154, "price": 510.45, "market_value": 589059, "weight": 0.89},
    {"ticker": "CNC", "name": "Centene Corp", "cusip": "15135B101", "quantity": 8580, "price": 41.15, "market_value": 353067, "weight": 0.53},
    {"ticker": "COF", "name": "Capital One Financial Corp", "cusip": "14040H105", "quantity": 4193, "price": 242.36, "market_value": 1016215, "weight": 1.53},
    {"ticker": "CRM", "name": "Salesforce Inc", "cusip": "79466L302", "quantity": 4275, "price": 264.91, "market_value": 1132490, "weight": 1.71},
    {"ticker": "CSCO", "name": "Cisco Systems Inc", "cusip": "17275R102", "quantity": 14958, "price": 76.62, "market_value": 1146082, "weight": 1.73},
    {"ticker": "CTSH", "name": "Cognizant Technology Solutions Corp", "cusip": "192446102", "quantity": 6260, "price": 83.00, "market_value": 519580, "weight": 0.78},
    {"ticker": "CVS", "name": "CVS Health Corp", "cusip": "126650100", "quantity": 9949, "price": 79.36, "market_value": 789553, "weight": 1.19},
    {"ticker": "DAL", "name": "Delta Air Lines Inc", "cusip": "247361702", "quantity": 6415, "price": 69.40, "market_value": 445201, "weight": 0.67},
    {"ticker": "DBX", "name": "Dropbox Inc", "cusip": "26210C104", "quantity": 7389, "price": 27.80, "market_value": 205414, "weight": 0.31},
    {"ticker": "DELL", "name": "Dell Technologies Inc", "cusip": "24703L202", "quantity": 5165, "price": 125.88, "market_value": 650170, "weight": 0.98},
    {"ticker": "DGX", "name": "Quest Diagnostics Inc", "cusip": "74834L100", "quantity": 1571, "price": 173.53, "market_value": 272616, "weight": 0.41},
    {"ticker": "DIS", "name": "Walt Disney Co/The", "cusip": "254687106", "quantity": 7981, "price": 113.77, "market_value": 907998, "weight": 1.37},
    {"ticker": "DOCU", "name": "Docusign Inc", "cusip": "256163106", "quantity": 4124, "price": 68.40, "market_value": 282082, "weight": 0.43},
    {"ticker": "DOW", "name": "Dow Inc", "cusip": "260557103", "quantity": 10947, "price": 23.38, "market_value": 255941, "weight": 0.39},
    {"ticker": "DOX", "name": "Amdocs Ltd", "cusip": "G02602103", "quantity": 2087, "price": 80.51, "market_value": 168024, "weight": 0.25},
    {"ticker": "DVA", "name": "DAVITA INC", "cusip": "23918K108", "quantity": 1416, "price": 113.61, "market_value": 160872, "weight": 0.24},
    {"ticker": "EA", "name": "Electronic Arts Inc", "cusip": "285512109", "quantity": 1705, "price": 204.33, "market_value": 348383, "weight": 0.53},
    {"ticker": "EBAY", "name": "eBay Inc", "cusip": "278642103", "quantity": 5383, "price": 87.10, "market_value": 468859, "weight": 0.71},
    {"ticker": "ELAN", "name": "Elanco Animal Health Inc", "cusip": "28414H103", "quantity": 11950, "price": 22.63, "market_value": 270428, "weight": 0.41},
    {"ticker": "EMN", "name": "Eastman Chemical Co", "cusip": "277432100", "quantity": 2729, "price": 63.83, "market_value": 174192, "weight": 0.26},
    {"ticker": "EPAM", "name": "EPAM Systems Inc", "cusip": "29414B104", "quantity": 813, "price": 204.88, "market_value": 166567, "weight": 0.25},
    {"ticker": "ETSY", "name": "Etsy Inc", "cusip": "29786A106", "quantity": 3368, "price": 55.44, "market_value": 186722, "weight": 0.28},
    {"ticker": "EXAS", "name": "Exact Sciences Corp", "cusip": "30063P105", "quantity": 3264, "price": 101.56, "market_value": 331492, "weight": 0.50},
    {"ticker": "EXPE", "name": "Expedia Group Inc", "cusip": "30212P303", "quantity": 1654, "price": 283.31, "market_value": 468595, "weight": 0.71},
    {"ticker": "F", "name": "Ford Motor Co", "cusip": "345370860", "quantity": 44456, "price": 13.12, "market_value": 583263, "weight": 0.88},
    {"ticker": "FDX", "name": "FedEx Corp", "cusip": "31428X106", "quantity": 2302, "price": 288.86, "market_value": 664956, "weight": 1.00},
    {"ticker": "FFIV", "name": "F5 Inc", "cusip": "315616102", "quantity": 978, "price": 255.26, "market_value": 249644, "weight": 0.38},
    {"ticker": "FLR", "name": "Fluor Corp", "cusip": "343412102", "quantity": 3648, "price": 39.63, "market_value": 144570, "weight": 0.22},
    {"ticker": "G", "name": "Genpact Ltd", "cusip": "G3922B107", "quantity": 3833, "price": 46.78, "market_value": 179308, "weight": 0.27},
    {"ticker": "GD", "name": "General Dynamics Corp", "cusip": "369550108", "quantity": 1533, "price": 336.66, "market_value": 516100, "weight": 0.78},
    {"ticker": "GILD", "name": "Gilead Sciences Inc", "cusip": "375558103", "quantity": 5291, "price": 122.74, "market_value": 649417, "weight": 0.98},
    {"ticker": "GIS", "name": "General Mills Inc", "cusip": "370334104", "quantity": 5383, "price": 46.50, "market_value": 250310, "weight": 0.38},
    {"ticker": "GLW", "name": "Corning Inc", "cusip": "219350105", "quantity": 4992, "price": 87.56, "market_value": 437100, "weight": 0.66},
    {"ticker": "GM", "name": "General Motors Co", "cusip": "37045V100", "quantity": 9025, "price": 81.32, "market_value": 733913, "weight": 1.11},
    {"ticker": "GOOG", "name": "Alphabet Inc", "cusip": "02079K107", "quantity": 5032, "price": 313.80, "market_value": 1579042, "weight": 2.38},
    {"ticker": "GOOGL", "name": "Alphabet Inc", "cusip": "02079K305", "quantity": 5036, "price": 313.00, "market_value": 1576268, "weight": 2.38},
    {"ticker": "HAL", "name": "Halliburton Co", "cusip": "406216101", "quantity": 11421, "price": 28.26, "market_value": 322757, "weight": 0.49},
    {"ticker": "HAS", "name": "Hasbro Inc", "cusip": "418056107", "quantity": 2731, "price": 82.00, "market_value": 223942, "weight": 0.34},
    {"ticker": "HOLX", "name": "Hologic Inc", "cusip": "436440101", "quantity": 2775, "price": 74.49, "market_value": 206710, "weight": 0.31},
    {"ticker": "HON", "name": "Honeywell International Inc", "cusip": "438516106", "quantity": 3820, "price": 195.09, "market_value": 745244, "weight": 1.13},
    {"ticker": "HPE", "name": "Hewlett Packard Enterprise Co", "cusip": "42824C109", "quantity": 18087, "price": 24.02, "market_value": 434450, "weight": 0.66},
    {"ticker": "HPQ", "name": "HP Inc", "cusip": "40434L105", "quantity": 15093, "price": 22.28, "market_value": 336272, "weight": 0.51},
    {"ticker": "HUM", "name": "Humana Inc", "cusip": "444859102", "quantity": 1606, "price": 256.13, "market_value": 411345, "weight": 0.62},
    {"ticker": "IBM", "name": "International Business Machines Corp", "cusip": "459200101", "quantity": 4405, "price": 296.21, "market_value": 1304805, "weight": 1.97},
    {"ticker": "ILMN", "name": "Illumina Inc", "cusip": "452327109", "quantity": 2712, "price": 131.16, "market_value": 355706, "weight": 0.54},
    {"ticker": "INTC", "name": "Intel Corp", "cusip": "458140100", "quantity": 26005, "price": 36.90, "market_value": 959584, "weight": 1.45},
    {"ticker": "IQV", "name": "IQVIA Holdings Inc", "cusip": "46266C105", "quantity": 1813, "price": 225.41, "market_value": 408668, "weight": 0.62},
    {"ticker": "ITRI", "name": "Itron Inc", "cusip": "465741106", "quantity": 1327, "price": 92.86, "market_value": 123225, "weight": 0.19},
    {"ticker": "J", "name": "Jacobs Solutions Inc", "cusip": "46982L108", "quantity": 2176, "price": 132.46, "market_value": 288233, "weight": 0.44},
    {"ticker": "JAZZ", "name": "Jazz Pharmaceuticals PLC", "cusip": "G50871105", "quantity": 1370, "price": 170.00, "market_value": 232900, "weight": 0.35},
    {"ticker": "JBL", "name": "Jabil Inc", "cusip": "466313103", "quantity": 1463, "price": 228.02, "market_value": 333593, "weight": 0.50},
    {"ticker": "JLL", "name": "Jones Lang LaSalle Inc", "cusip": "48020Q107", "quantity": 829, "price": 336.47, "market_value": 278934, "weight": 0.42},
    {"ticker": "KR", "name": "Kroger Co/The", "cusip": "501044101", "quantity": 5899, "price": 62.48, "market_value": 368570, "weight": 0.56},
    {"ticker": "LCID", "name": "Lucid Group Inc", "cusip": "549498202", "quantity": 8056, "price": 10.57, "market_value": 85152, "weight": 0.13},
    {"ticker": "LDOS", "name": "Leidos Holdings Inc", "cusip": "525327102", "quantity": 1982, "price": 180.40, "market_value": 357553, "weight": 0.54},
    {"ticker": "LH", "name": "Labcorp Holdings Inc", "cusip": "504922105", "quantity": 1228, "price": 250.88, "market_value": 308081, "weight": 0.47},
    {"ticker": "LHX", "name": "L3Harris Technologies Inc", "cusip": "502431109", "quantity": 1918, "price": 293.57, "market_value": 563067, "weight": 0.85},
    {"ticker": "LMT", "name": "Lockheed Martin Corp", "cusip": "539830109", "quantity": 1292, "price": 483.67, "market_value": 624902, "weight": 0.94},
    {"ticker": "LRN", "name": "Stride Inc", "cusip": "86333M108", "quantity": 2059, "price": 64.93, "market_value": 133691, "weight": 0.20},
    {"ticker": "LUMN", "name": "Lumen Technologies Inc", "cusip": "550241103", "quantity": 26101, "price": 7.77, "market_value": 202805, "weight": 0.31},
    {"ticker": "LUV", "name": "Southwest Airlines Co", "cusip": "844741108", "quantity": 7490, "price": 41.33, "market_value": 309562, "weight": 0.47},
    {"ticker": "LYFT", "name": "Lyft Inc", "cusip": "55087P104", "quantity": 10322, "price": 19.37, "market_value": 199937, "weight": 0.30},
    {"ticker": "MDT", "name": "Medtronic PLC", "cusip": "G5960L103", "quantity": 8811, "price": 96.06, "market_value": 846385, "weight": 1.28},
    {"ticker": "MGM", "name": "MGM Resorts International", "cusip": "552953101", "quantity": 4347, "price": 36.49, "market_value": 158622, "weight": 0.24},
    {"ticker": "MMM", "name": "3M Co", "cusip": "88579Y101", "quantity": 2996, "price": 160.10, "market_value": 479660, "weight": 0.72},
    {"ticker": "MOH", "name": "Molina Healthcare Inc", "cusip": "60855R100", "quantity": 948, "price": 173.54, "market_value": 164516, "weight": 0.25},
    {"ticker": "MRK", "name": "Merck & Co Inc", "cusip": "58933Y105", "quantity": 9670, "price": 105.26, "market_value": 1017864, "weight": 1.54},
    {"ticker": "MTCH", "name": "Match Group Inc", "cusip": "57667L107", "quantity": 5161, "price": 32.29, "market_value": 166649, "weight": 0.25},
    {"ticker": "MU", "name": "Micron Technology Inc", "cusip": "595112103", "quantity": 3476, "price": 285.41, "market_value": 992085, "weight": 1.50},
    {"ticker": "NOC", "name": "Northrop Grumman Corp", "cusip": "666807102", "quantity": 1117, "price": 570.21, "market_value": 636925, "weight": 0.96},
    {"ticker": "NTAP", "name": "NetApp Inc", "cusip": "64110D104", "quantity": 3075, "price": 106.57, "market_value": 327703, "weight": 0.49},
    {"ticker": "NTNX", "name": "Nutanix Inc", "cusip": "67059N108", "quantity": 4552, "price": 51.69, "market_value": 235293, "weight": 0.36},
    {"ticker": "NXPI", "name": "NXP Semiconductors NV", "cusip": "N6596X109", "quantity": 2122, "price": 217.06, "market_value": 460601, "weight": 0.70},
    {"ticker": "OKTA", "name": "Okta Inc", "cusip": "679295105", "quantity": 3248, "price": 86.47, "market_value": 280855, "weight": 0.42},
    {"ticker": "PATH", "name": "UiPath Inc", "cusip": "90364P105", "quantity": 9707, "price": 16.39, "market_value": 159098, "weight": 0.24},
    {"ticker": "PEGA", "name": "Pegasystems Inc", "cusip": "705573103", "quantity": 3818, "price": 59.69, "market_value": 227896, "weight": 0.34},
    {"ticker": "PFE", "name": "Pfizer Inc", "cusip": "717081103", "quantity": 37876, "price": 24.90, "market_value": 943112, "weight": 1.42},
    {"ticker": "PINS", "name": "Pinterest Inc", "cusip": "72352L106", "quantity": 7761, "price": 25.89, "market_value": 200932, "weight": 0.30},
    {"ticker": "PL", "name": "Planet Labs PBC", "cusip": "72703X106", "quantity": 8017, "price": 19.72, "market_value": 158095, "weight": 0.24},
    {"ticker": "PPG", "name": "PPG Industries Inc", "cusip": "693506107", "quantity": 2545, "price": 102.46, "market_value": 260761, "weight": 0.39},
    {"ticker": "PRU", "name": "Prudential Financial Inc", "cusip": "744320102", "quantity": 2805, "price": 112.88, "market_value": 316628, "weight": 0.48},
    {"ticker": "PSKY", "name": "Paramount Skydance Corp", "cusip": "69932A204", "quantity": 17789, "price": 13.40, "market_value": 238373, "weight": 0.36},
    {"ticker": "PTCT", "name": "PTC Therapeutics Inc", "cusip": "69366J200", "quantity": 1878, "price": 75.96, "market_value": 142653, "weight": 0.22},
    {"ticker": "PYPL", "name": "PayPal Holdings Inc", "cusip": "70450Y103", "quantity": 9308, "price": 58.38, "market_value": 543401, "weight": 0.82},
    {"ticker": "QCOM", "name": "QUALCOMM Inc", "cusip": "747525103", "quantity": 6306, "price": 171.05, "market_value": 1078641, "weight": 1.63},
    {"ticker": "QRVO", "name": "Qorvo Inc", "cusip": "74736K101", "quantity": 2219, "price": 84.51, "market_value": 187528, "weight": 0.28},
    {"ticker": "RKT", "name": "Rocket Cos Inc", "cusip": "77311W101", "quantity": 18298, "price": 19.36, "market_value": 354249, "weight": 0.53},
    {"ticker": "ROK", "name": "Rockwell Automation Inc", "cusip": "773903109", "quantity": 870, "price": 389.07, "market_value": 338491, "weight": 0.51},
    {"ticker": "ROKU", "name": "Roku Inc", "cusip": "77543R102", "quantity": 2574, "price": 108.49, "market_value": 279253, "weight": 0.42},
    {"ticker": "RTX", "name": "RTX Corp", "cusip": "75513E101", "quantity": 4962, "price": 183.40, "market_value": 910031, "weight": 1.37},
    {"ticker": "RUN", "name": "Sunrun Inc", "cusip": "86771W105", "quantity": 9410, "price": 18.40, "market_value": 173144, "weight": 0.26},
    {"ticker": "S", "name": "SentinelOne Inc", "cusip": "81730H109", "quantity": 6985, "price": 15.00, "market_value": 104775, "weight": 0.16},
    {"ticker": "SIRI", "name": "Sirius XM Holdings Inc", "cusip": "829933100", "quantity": 7892, "price": 20.00, "market_value": 157801, "weight": 0.24},
    {"ticker": "SNAP", "name": "Snap Inc", "cusip": "83304A106", "quantity": 38010, "price": 8.07, "market_value": 306741, "weight": 0.46},
    {"ticker": "SWK", "name": "Stanley Black & Decker Inc", "cusip": "854502101", "quantity": 3344, "price": 74.28, "market_value": 248392, "weight": 0.37},
    {"ticker": "SWKS", "name": "Skyworks Solutions Inc", "cusip": "83088M102", "quantity": 2845, "price": 63.41, "market_value": 180401, "weight": 0.27},
    {"ticker": "T", "name": "AT&T Inc", "cusip": "00206R102", "quantity": 41482, "price": 24.84, "market_value": 1030413, "weight": 1.56},
    {"ticker": "TAP", "name": "Molson Coors Beverage Co", "cusip": "60871R209", "quantity": 3798, "price": 46.68, "market_value": 177291, "weight": 0.27},
    {"ticker": "TEL", "name": "TE Connectivity PLC", "cusip": "G87052109", "quantity": 1881, "price": 227.51, "market_value": 427946, "weight": 0.65},
    {"ticker": "TGT", "name": "Target Corp", "cusip": "87612E106", "quantity": 5614, "price": 97.75, "market_value": 548768, "weight": 0.83},
    {"ticker": "TMUS", "name": "T-Mobile US Inc", "cusip": "872590104", "quantity": 3726, "price": 203.04, "market_value": 756527, "weight": 1.14},
    {"ticker": "TPR", "name": "Tapestry Inc", "cusip": "876030107", "quantity": 2157, "price": 127.77, "market_value": 275600, "weight": 0.42},
    {"ticker": "TRMB", "name": "Trimble Inc", "cusip": "896239100", "quantity": 3023, "price": 78.35, "market_value": 236852, "weight": 0.36},
    {"ticker": "TSN", "name": "Tyson Foods Inc", "cusip": "902494103", "quantity": 3997, "price": 58.62, "market_value": 234304, "weight": 0.35},
    {"ticker": "TWLO", "name": "Twilio Inc", "cusip": "90138F102", "quantity": 2482, "price": 142.24, "market_value": 353040, "weight": 0.53},
    {"ticker": "TXT", "name": "Textron Inc", "cusip": "883203101", "quantity": 2693, "price": 87.17, "market_value": 234749, "weight": 0.35},
    {"ticker": "U", "name": "Unity Software Inc", "cusip": "91332U101", "quantity": 5349, "price": 44.17, "market_value": 236265, "weight": 0.36},
    {"ticker": "UAL", "name": "United Airlines Holdings Inc", "cusip": "910047109", "quantity": 4378, "price": 111.82, "market_value": 489548, "weight": 0.74},
    {"ticker": "URBN", "name": "Urban Outfitters Inc", "cusip": "917047102", "quantity": 1891, "price": 75.26, "market_value": 142317, "weight": 0.21},
    {"ticker": "VFC", "name": "VF Corp", "cusip": "918204108", "quantity": 7301, "price": 18.08, "market_value": 132002, "weight": 0.20},
    {"ticker": "VTRS", "name": "Viatris Inc", "cusip": "92556V106", "quantity": 25718, "price": 12.45, "market_value": 320189, "weight": 0.48},
    {"ticker": "VZ", "name": "Verizon Communications Inc", "cusip": "92343V104", "quantity": 21212, "price": 40.73, "market_value": 863965, "weight": 1.30},
    {"ticker": "W", "name": "Wayfair Inc", "cusip": "94419L101", "quantity": 2783, "price": 100.41, "market_value": 279441, "weight": 0.42},
    {"ticker": "WBD", "name": "Warner Bros Discovery Inc", "cusip": "934423104", "quantity": 23936, "price": 28.82, "market_value": 689836, "weight": 1.04},
    {"ticker": "WDAY", "name": "Workday Inc", "cusip": "98138H101", "quantity": 1938, "price": 214.78, "market_value": 416244, "weight": 0.63},
    {"ticker": "WDC", "name": "Western Digital Corp", "cusip": "958102105", "quantity": 3695, "price": 172.27, "market_value": 636538, "weight": 0.96},
    {"ticker": "WFC", "name": "Wells Fargo & Co", "cusip": "949746101", "quantity": 10458, "price": 93.20, "market_value": 974686, "weight": 1.47},
    {"ticker": "XYZ", "name": "Block Inc", "cusip": "852234103", "quantity": 7795, "price": 65.09, "market_value": 507377, "weight": 0.77},
    {"ticker": "ZBRA", "name": "Zebra Technologies Corp", "cusip": "989207105", "quantity": 957, "price": 242.82, "market_value": 232379, "weight": 0.35},
    {"ticker": "ZM", "name": "Zoom Communications Inc", "cusip": "98980L101", "quantity": 3569, "price": 86.29, "market_value": 307969, "weight": 0.46},
    {"ticker": "Cash&Other", "name": "Cash & Other", "cusip": "", "quantity": 34032, "price": 1.00, "market_value": 34032, "weight": 0.05},
    {"ticker": "FGXXX", "name": "First American Government Obligations Fund 12/01/2031", "cusip": "31846V336", "quantity": 124451, "price": 100.00, "market_value": 124452, "weight": 0.19},
]

# Separate stocks from cash/money market
STOCK_HOLDINGS = [h for h in ITAN_HOLDINGS if h['ticker'] not in ['Cash&Other', 'BBG01SQXBKP2', 'FGXXX']]
CASH_HOLDINGS = [h for h in ITAN_HOLDINGS if h['ticker'] in ['Cash&Other', 'FGXXX']]

def format_holdings_for_adapter(holdings):
    """Format holdings for FMP adapter"""
    return [
        {
            "ticker": h["ticker"],
            "cusip": h.get("cusip", ""),
            "quantity": h["quantity"],
            "weight": h["weight"],
            "name": h.get("name", ""),
            "market_value": h.get("market_value", 0)
        }
        for h in holdings
    ]


def test_itan_nav_calculation():
    """Test NAV calculation with ITAN holdings"""
    logger.info("=" * 60)
    logger.info("TEST: NAV Calculation with ITAN Holdings")
    logger.info("=" * 60)
    
    try:
        from lib.etf.adapters import FMPDataSourceAdapter
        from lib.etf.functions.core import FundAdministration
        
        api_key = os.getenv('FMP_API_KEY')
        if not api_key:
            logger.error("FMP_API_KEY not set")
            return False
        
        holdings = format_holdings_for_adapter(STOCK_HOLDINGS)
        logger.info(f"Testing with {len(holdings)} ITAN holdings")
        
        adapter = FMPDataSourceAdapter(
            manual_holdings=holdings,
            api_key=api_key
        )
        
        admin = FundAdministration(
            data_adapter=adapter,
            storage_path="./data/test_itan_admin"
        )
        
        logger.info("Calculating NAV with FMP prices...")
        nav_calc = admin.calculate_nav(date.today())
        
        if nav_calc:
            logger.info(f"✓ NAV calculated: ${nav_calc.nav_per_share}")
            logger.info(f"  Total assets: ${nav_calc.total_assets:,.2f}")
            logger.info(f"  Net assets: ${nav_calc.net_assets:,.2f}")
            logger.info(f"  Validation: {'PASSED' if nav_calc.validation_passed else 'FAILED'}")
            
            if nav_calc.pricing_exceptions:
                logger.warning(f"  Pricing exceptions: {len(nav_calc.pricing_exceptions)}")
                for exc in nav_calc.pricing_exceptions[:5]:
                    logger.warning(f"    - {exc}")
            
            return True
        return False
        
    except Exception as e:
        logger.error(f"✗ NAV calculation failed: {e}", exc_info=True)
        return False


def test_itan_accounting():
    """Test accounting operations with ITAN holdings"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Accounting Operations with ITAN Holdings")
    logger.info("=" * 60)
    
    try:
        from lib.etf.adapters import FMPDataSourceAdapter
        from lib.etf.functions.core import Accounting, FundAdministration
        
        api_key = os.getenv('FMP_API_KEY')
        if not api_key:
            logger.error("FMP_API_KEY not set")
            return False
        
        holdings = format_holdings_for_adapter(STOCK_HOLDINGS)
        
        adapter = FMPDataSourceAdapter(
            manual_holdings=holdings,
            api_key=api_key
        )
        
        accounting = Accounting(
            data_adapter=adapter,
            storage_path="./data/test_itan_accounting"
        )
        
        admin = FundAdministration(
            data_adapter=adapter,
            storage_path="./data/test_itan_admin"
        )
        
        # Calculate NAV
        nav_calc = admin.calculate_nav(date.today())
        
        # Run accounting operations
        logger.info("Running daily accounting operations...")
        results = accounting.daily_accounting_operations(date.today(), nav_calc)
        
        logger.info(f"✓ Accounting operations completed")
        logger.info(f"  NAV entries: {len(results.get('nav_entries', []))}")
        logger.info(f"  Expense entries: {len(results.get('expense_entries', []))}")
        logger.info(f"  Income entries: {len(results.get('income_entries', []))}")
        
        # Check trial balance
        tb = results.get('trial_balance')
        if tb:
            logger.info(f"  Trial balance: {'BALANCED' if tb.balanced else 'UNBALANCED'}")
            logger.info(f"  Total debits: ${tb.total_debits:,.2f}")
            logger.info(f"  Total credits: ${tb.total_credits:,.2f}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Accounting operations failed: {e}", exc_info=True)
        return False


def test_itan_workflows():
    """Test FMP workflows with ITAN holdings"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: FMP Workflows with ITAN Holdings")
    logger.info("=" * 60)
    
    try:
        from lib.etf.functions.core import FMPEnhancedWorkflows
        
        api_key = os.getenv('FMP_API_KEY')
        if not api_key:
            logger.error("FMP_API_KEY not set")
            return False
        
        holdings = format_holdings_for_adapter(STOCK_HOLDINGS)
        
        workflows = FMPEnhancedWorkflows(
            etf_symbol="ITAN",
            manual_holdings=holdings,
            api_key=api_key,
            storage_path="./data/test_itan_workflows"
        )
        
        # Test individual workflows
        logger.info("Testing daily price import and NAV...")
        nav_result = workflows.daily_price_import_and_nav(date.today())
        if nav_result:
            nav = nav_result.get('nav_calculation', {})
            logger.info(f"✓ NAV: ${nav.get('nav_per_share', 'N/A')}")
        
        logger.info("Testing corporate actions...")
        ca_result = workflows.daily_corporate_actions_processing(date.today())
        logger.info(f"✓ Corporate actions: {ca_result.get('actions_processed', 0)} processed")
        
        logger.info("Testing dividend accrual...")
        div_result = workflows.daily_dividend_accrual_tracking(date.today())
        logger.info(f"✓ Dividend accrual: ${div_result.get('total_accrued_income', 0)}")
        
        logger.info("Testing expense accrual...")
        exp_result = workflows.daily_expense_accrual_and_fee_booking(date.today())
        logger.info(f"✓ Expense accrual completed")
        
        logger.info("Testing NAV verification...")
        nav_verif = workflows.daily_nav_verification_and_reconciliation(date.today(), "SPY")
        logger.info(f"✓ NAV verification: {nav_verif.get('reconciliation_status', 'N/A')}")
        
        # Test full daily operations
        logger.info("\nTesting full daily operations...")
        daily_results = workflows.run_daily_operations(date.today(), "SPY")
        
        if daily_results:
            logger.info(f"✓ Full daily operations completed")
            ops = daily_results.get('operations', {})
            logger.info(f"  Operations run: {list(ops.keys())}")
            
            # Save results
            results_file = Path("./data/test_itan_workflows/daily_operations_results.json")
            results_file.parent.mkdir(parents=True, exist_ok=True)
            with open(results_file, 'w') as f:
                json.dump(daily_results, f, indent=2, default=str)
            logger.info(f"  Results saved to: {results_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Workflows test failed: {e}", exc_info=True)
        return False


def test_itan_market_data():
    """Test market data retrieval for ITAN holdings"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Market Data Retrieval for ITAN Holdings")
    logger.info("=" * 60)
    
    try:
        from lib.etf.adapters import FMPDataSourceAdapter
        
        api_key = os.getenv('FMP_API_KEY')
        if not api_key:
            logger.error("FMP_API_KEY not set")
            return False
        
        holdings = format_holdings_for_adapter(STOCK_HOLDINGS[:20])  # Test with first 20
        adapter = FMPDataSourceAdapter(
            manual_holdings=holdings,
            api_key=api_key
        )
        
        # Test batch quotes
        logger.info("Testing batch quotes for 20 holdings...")
        tickers = [h['ticker'] for h in holdings]
        quotes = adapter.fmp_client.get_batch_quotes(tickers)
        
        if quotes:
            logger.info(f"✓ Retrieved quotes for {len(quotes)} tickers")
            for ticker, quote in list(quotes.items())[:5]:
                price = quote.get('price') or quote.get('close')
                logger.info(f"  {ticker}: ${price}")
        else:
            logger.warning("✗ No quotes returned")
        
        # Test security identifiers
        logger.info("\nTesting security identifier lookups...")
        identifiers = adapter.get_security_identifiers("AAPL")
        logger.info(f"✓ AAPL identifiers: CUSIP={identifiers.get('cusip', 'N/A')}, CIK={identifiers.get('cik', 'N/A')}")
        
        # Test portfolio metrics
        logger.info("\nTesting portfolio metrics calculation...")
        metrics = adapter.get_portfolio_metrics(date.today())
        logger.info(f"✓ Portfolio metrics calculated")
        logger.info(f"  Weighted P/E: {metrics.get('weighted_pe', 'N/A')}")
        logger.info(f"  Weighted Dividend Yield: {metrics.get('weighted_dividend_yield', 'N/A')}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Market data test failed: {e}", exc_info=True)
        return False


def main():
    """Run all ITAN tests"""
    logger.info("\n" + "=" * 60)
    logger.info("ITAN ETF FMP WORKFLOWS TEST SUITE")
    logger.info("=" * 60)
    logger.info(f"Test Date: {date.today()}")
    logger.info(f"Holdings: {len(STOCK_HOLDINGS)} stocks")
    logger.info(f"FMP API Key: {'Set' if os.getenv('FMP_API_KEY') else 'NOT SET'}")
    logger.info("=" * 60 + "\n")
    
    results = {}
    
    results['nav_calculation'] = test_itan_nav_calculation()
    results['accounting'] = test_itan_accounting()
    results['market_data'] = test_itan_market_data()
    results['workflows'] = test_itan_workflows()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name:20s}: {status}")
    
    logger.info("=" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")
    logger.info("=" * 60)
    
    if passed == total:
        logger.info("🎉 All ITAN tests passed!")
        return 0
    else:
        logger.warning(f"⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())

