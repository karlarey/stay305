"""Stay305 data pipeline.

Writes:
  data/occupations.json   BLS OEWS wages + employment, Miami-Fort Lauderdale-West Palm Beach MSA
  data/neighborhoods.json Zillow Observed Rent Index (ZORI) by ZIP, Miami-Dade County, latest month

Run: python data/fetch_data.py   (no API keys needed)
"""
import csv
import json
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
RAW = HERE / "raw"
RAW.mkdir(exist_ok=True)

# --- BLS OEWS -----------------------------------------------------------------
BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
AREA = "0033100"  # Miami-Fort Lauderdale-West Palm Beach, FL MSA
DATATYPES = {"13": "median_annual", "04": "mean_annual", "01": "employment"}

# Occupations a graduating senior could realistically target (2018 SOC).
OCCUPATIONS = {
    "15-1252": "Software Developers",
    "15-1253": "Software Quality Assurance Analysts and Testers",
    "15-1254": "Web Developers",
    "15-1255": "Web and Digital Interface Designers",
    "15-1211": "Computer Systems Analysts",
    "15-1212": "Information Security Analysts",
    "15-1244": "Network and Computer Systems Administrators",
    "15-1232": "Computer User Support Specialists",
    "15-2051": "Data Scientists",
    "15-2031": "Operations Research Analysts",
    "13-2011": "Accountants and Auditors",
    "13-2051": "Financial and Investment Analysts",
    "13-2052": "Personal Financial Advisors",
    "13-2072": "Loan Officers",
    "13-1161": "Market Research Analysts and Marketing Specialists",
    "13-1111": "Management Analysts",
    "13-1071": "Human Resources Specialists",
    "13-1081": "Logisticians",
    "13-1082": "Project Management Specialists",
    "13-1041": "Compliance Officers",
    "13-1121": "Meeting, Convention, and Event Planners",
    "13-1151": "Training and Development Specialists",
    "11-2021": "Marketing Managers",
    "11-3031": "Financial Managers",
    "11-9111": "Medical and Health Services Managers",
    "11-9081": "Lodging Managers",
    "11-9051": "Food Service Managers",
    "11-3071": "Transportation, Storage, and Distribution Managers",
    "27-3031": "Public Relations Specialists",
    "27-1024": "Graphic Designers",
    "27-3042": "Technical Writers",
    "27-2012": "Producers and Directors",
    "27-3043": "Writers and Authors",
    "29-1141": "Registered Nurses",
    "29-1171": "Nurse Practitioners",
    "29-1051": "Pharmacists",
    "29-1123": "Physical Therapists",
    "29-2034": "Radiologic Technologists and Technicians",
    "29-1031": "Dietitians and Nutritionists",
    "21-1021": "Child, Family, and School Social Workers",
    "21-1018": "Substance Abuse, Behavioral Disorder, and Mental Health Counselors",
    "25-2021": "Elementary School Teachers, Except Special Education",
    "25-2031": "Secondary School Teachers, Except Special and Career/Technical Education",
    "17-2051": "Civil Engineers",
    "17-2141": "Mechanical Engineers",
    "17-2071": "Electrical Engineers",
    "17-2011": "Aerospace Engineers",
    "17-2081": "Environmental Engineers",
    "17-1011": "Architects, Except Landscape and Naval",
    "19-2041": "Environmental Scientists and Specialists, Including Health",
    "23-2011": "Paralegals and Legal Assistants",
    "23-1011": "Lawyers",
    "41-3091": "Sales Representatives of Services, Except Advertising, Insurance, Financial Services, and Travel",
    "41-3031": "Securities, Commodities, and Financial Services Sales Agents",
    "41-9022": "Real Estate Sales Agents",
    "43-4051": "Customer Service Representatives",
}


def post_json(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def fetch_bls():
    series = {}
    for soc in OCCUPATIONS:
        for dt in DATATYPES:
            series[f"OEUM{AREA}000000{soc.replace('-', '')}{dt}"] = (soc, dt)
    ids = list(series)
    results = {}
    for i in range(0, len(ids), 25):  # keyless v2 limit: 25 series per request
        chunk = ids[i : i + 25]
        resp = post_json(BLS_URL, {"seriesid": chunk, "startyear": "2024", "endyear": "2025"})
        if resp.get("status") != "REQUEST_SUCCEEDED":
            raise RuntimeError(f"BLS error: {resp.get('message')}")
        for s in resp["Results"]["series"]:
            if s["data"]:
                latest = max(s["data"], key=lambda d: d["year"])
                results[s["seriesID"]] = (latest["value"], int(latest["year"]))
        time.sleep(0.5)
    (RAW / "bls_oews.json").write_text(json.dumps(results, indent=1))

    rows = []
    for soc, title in OCCUPATIONS.items():
        rec = {"soc": soc, "title": title}
        year = None
        for dt, field in DATATYPES.items():
            sid = f"OEUM{AREA}000000{soc.replace('-', '')}{dt}"
            val, yr = results.get(sid, (None, None))
            try:
                rec[field] = int(float(val.replace(",", "")))
            except (AttributeError, ValueError):
                rec[field] = None  # BLS uses '-' / '#' for suppressed or top-coded values
            year = year or yr
        if rec["median_annual"] is None:
            print(f"  skip {soc} {title}: no median wage published")
            continue
        rec.update(year=year, area="Miami-Fort Lauderdale-West Palm Beach, FL MSA", source="BLS OEWS")
        rows.append(rec)
    rows.sort(key=lambda r: -r["median_annual"])
    return rows


# --- Zillow ZORI by ZIP -------------------------------------------------------
ZORI_URL = "https://files.zillowstatic.com/research/public_csvs/zori/Zip_zori_uc_sfrcondomfr_sm_month.csv"

# Commonly used neighborhood names; ZIPs not listed fall back to Zillow's city name.
NEIGHBORHOODS = {
    "33125": "Little Havana / Grapeland Heights", "33126": "Flagami / Blue Lagoon", "33127": "Wynwood / Little Haiti",
    "33128": "Downtown Miami (West)", "33129": "The Roads / Brickell South", "33130": "Brickell West / Little Havana East",
    "33131": "Brickell", "33132": "Downtown Miami", "33133": "Coconut Grove", "33134": "Coral Gables",
    "33135": "Little Havana", "33136": "Overtown / Health District", "33137": "Edgewater / Design District",
    "33138": "Upper East Side / Miami Shores", "33139": "South Beach", "33140": "Mid-Beach",
    "33141": "North Beach", "33142": "Allapattah / Brownsville", "33143": "South Miami", "33144": "West Miami",
    "33145": "Shenandoah / Silver Bluff", "33146": "Coral Gables (UM area)", "33147": "West Little River",
    "33149": "Key Biscayne", "33150": "Little Haiti / El Portal", "33154": "Bal Harbour / Surfside",
    "33155": "Westchester / Bird Road", "33156": "Pinecrest", "33157": "Palmetto Bay / Perrine",
    "33158": "Palmetto Bay", "33160": "Sunny Isles / Aventura", "33161": "North Miami",
    "33162": "North Miami Beach", "33165": "Westchester / Olympia Heights", "33166": "Miami Springs / Medley",
    "33167": "North Miami (West)", "33168": "Biscayne Gardens", "33169": "Miami Gardens (East)",
    "33172": "Doral (South) / Sweetwater", "33173": "Kendall (Sunset)", "33174": "Sweetwater / FIU area",
    "33175": "Tamiami / Westwood Lakes", "33176": "Kendall", "33177": "South Miami Heights",
    "33178": "Doral", "33179": "Ojus / Ives Estates", "33180": "Aventura", "33181": "North Bay Village / Keystone",
    "33182": "Tamiami West", "33183": "Kendall Lakes", "33184": "Fontainebleau / Tamiami",
    "33185": "West Kendall (Bird Road)", "33186": "The Hammocks / Kendall West", "33187": "Richmond West",
    "33189": "Cutler Bay", "33190": "Cutler Bay (South)", "33193": "Kendall West (The Crossings)",
    "33194": "West Kendall (Far West)", "33196": "Country Walk / West Kendall",
    "33010": "Hialeah (East)", "33012": "Hialeah", "33013": "Hialeah (South)", "33014": "Miami Lakes (East)",
    "33015": "Country Club / Miami Lakes", "33016": "Hialeah Gardens", "33018": "Hialeah (West)",
    "33030": "Homestead", "33031": "Redland", "33032": "Princeton / Naranja", "33033": "Homestead (East)",
    "33034": "Florida City", "33035": "Homestead Base area", "33054": "Opa-locka", "33055": "Miami Gardens (West)",
    "33056": "Miami Gardens", "33109": "Fisher Island", "33122": "Doral (West)",
}


def fetch_zillow():
    path = RAW / "zori_zip.csv"
    if not path.exists():
        urllib.request.urlretrieve(ZORI_URL, path)
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        months = [c for c in header if c[:2] == "20"]
        for r in reader:
            rec = dict(zip(header, r))
            if rec["CountyName"] != "Miami-Dade County" or rec["State"] != "FL":
                continue
            # latest month with a value
            month = next((m for m in reversed(months) if rec[m]), None)
            if not month:
                continue
            zip_code = rec["RegionName"].zfill(5)
            rows.append({
                "zip": zip_code,
                "name": NEIGHBORHOODS.get(zip_code, rec["City"]),
                "median_rent": round(float(rec[month])),
                "month": month[:7],
                "source": "Zillow Observed Rent Index (ZORI), all homes, smoothed",
            })
    rows.sort(key=lambda r: r["median_rent"])
    return rows


if __name__ == "__main__":
    occ = fetch_bls()
    (HERE / "occupations.json").write_text(json.dumps(occ, indent=1))
    print(f"occupations.json: {len(occ)} occupations")
    hoods = fetch_zillow()
    (HERE / "neighborhoods.json").write_text(json.dumps(hoods, indent=1))
    print(f"neighborhoods.json: {len(hoods)} ZIPs, latest month {max(h['month'] for h in hoods)}")
