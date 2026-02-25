import pdfplumber
import re
import json


PDF_FILENAME = "Plakat_2026_PRZEMYSL_GLOWNY_Odjazdy_Wazny_20251214_20260307_PL_202602251137.pdf"
OUTPUT_FILENAME = "pkp_schedule_final.json"

START_BLOCK_PATTERN = re.compile(r"(?m)^(\d{1,2}:\d{2})(?:\s+\d)?")
TRAIN_ID_PATTERN = re.compile(r"\b(\d{4,5})\b")
ROUTE_PATTERN = re.compile(r"([^\d,;]+?)\s+(\d{1,2}:\d{2})")

IGNORED_TRAIN_NAMES = [
    "WAWEL", "NIEDŹWIADEK", "ZEFIR", "SAN", "RZESZOWIANIN", "WYCZÓŁKOWSKI",
    "VIA REGIA", "KOSSAK", "CRACOVIA", "GALICJA", "SZKUNER", "MATEJKO",
    "FAŁAT", "SIEMIRADZKI", "WYSPIAŃSKI", "WITOS", "GROTTGER", "CARPATIA",
    "URSA", "UZNAM", "PRZEMYŚLANIN", "PODHALANIN", "ŚLĄZAK", "MEHOFFER",
    "ROZEWIE", "ARTUS", "PIAST", "GÓRSKI", "LWOVIANIN", "HETMAN", "ZAMOYSKI",
    "MIESZKO", "ŁOKIETEK", "DANUBIUS", "LUBOMIRSKI", "ODRA", "PORTA MORAVICA",
    "REGIOJET", "ROZTOCZE", "SKARBEK", "MALCZEWSKI", "BIEBRZA",
    "ANIN", "KARPATY"
]

SPACED_CAPS_PATTERN = re.compile(r"\b(?:[A-ZŚĆŻŹŁÓŃĘĄV]\s+){3,}[A-ZŚĆŻŹŁÓŃĘĄV]\b")

MASK_PATTERNS = [
    (r"\b1-5\b", 31), (r"\b1-6\b", 63), (r"\b6-7\b", 96), (r"\b1-7\b", 127),
    (r"\b\(D\)", 31), (r"\b\(C\)", 96), (r"\b7\b", 64), (r"\b6\b", 32),
    (r"codziennie", 127)
]

def clean_station_name(raw_name):
    name = raw_name.strip()

    name = SPACED_CAPS_PATTERN.sub("", name)

    for train_name in IGNORED_TRAIN_NAMES:
        pattern = r"\b" + re.escape(train_name) + r"\b"
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)

    name = re.sub(r"^(?:IC|PR|MP|RJ|RP|TLK|EIC|RegioJet)\b\s*[-–]?\s*", "", name, flags=re.IGNORECASE)

    name = re.sub(r"^[-–]\s*", "", name)
    name = re.sub(r"[@+\/~]", " ", name)
    forbidden_codes = r"\b(?:b|x|R|y|a|G|I|e|k|h|T|l|d|c|Z|M|W|0|g)\b"
    name = re.sub(forbidden_codes, " ", name)
    name = " ".join(name.split())
    if name.isupper() and len(name) > 3:
        return ""

    if len(name) < 2: return ""

    return name

def parse_day_mask(text_block):
    mask = 127
    found_period = "codziennie"
    for pattern, val in MASK_PATTERNS:
        if re.search(pattern, text_block):
            mask = val
            found_period = pattern.replace(r"\b", "").replace(r"\(", "").replace(r"\)", "")
            break
    date_match = re.search(r"(\d{1,2}\s*[IVX]+[-\s]+\d{1,2}\s*[IVX]+)", text_block)
    if date_match:
        found_period = date_match.group(1)
    return mask, found_period

def parse_amenities(text_block):
    amenities = {
        "has_wifi": False, "has_AC": False, "has_bicycle": False,
        "accessible": False, "has_restaurant": False
    }
    if "@" in text_block: amenities["has_wifi"] = True
    if "y" in text_block: amenities["has_AC"] = True
    if "b" in text_block: amenities["has_bicycle"] = True
    if "&" in text_block or " G " in text_block or " a " in text_block or "wózk" in text_block.lower():
        amenities["accessible"] = True
    if "e" in text_block or " I " in text_block or "x" in text_block.lower() or "bistro" in text_block.lower():
        amenities["has_restaurant"] = True
    if "IC" in text_block or "EIC" in text_block:
        amenities["has_wifi"] = True
        amenities["has_AC"] = True
    return amenities

def parse_block(block_text, departure_time):
    id_match = TRAIN_ID_PATTERN.search(block_text)
    train_id = id_match.group(1) if id_match else f"UNK_{departure_time.replace(':','')}"
    clean_text = block_text.replace("\n", " ")

    stations = []
    stations.append({
        "stationName": "Przemyśl Główny",
        "orderNumber": 1,
        "departureTime": departure_time
    })

    matches = ROUTE_PATTERN.finditer(clean_text)
    order = 2

    for m in matches:
        raw_name = m.group(1)
        time = m.group(2)

        clean_name = clean_station_name(raw_name)

        if not clean_name: continue
        if len(clean_name) < 2: continue
        if time == departure_time and order == 2: continue
        if any(x in clean_name.lower() for x in ["godzina", "peron", "tor", "odjazdu", "przyjazdu"]):
            continue

        stations.append({
            "stationName": clean_name,
            "orderNumber": order,
            "arrivalTime": time
        })
        order += 1

    amenities = parse_amenities(block_text)
    mask, period = parse_day_mask(block_text)

    return train_id, {
        "has_wifi": amenities["has_wifi"],
        "has_AC": amenities["has_AC"],
        "has_bicycle": amenities["has_bicycle"],
        "accessible": amenities["accessible"],
        "has_restaurant": amenities["has_restaurant"],
        "day_mask": mask,
        "stations": stations
    }

def process_pdf(pdf_path):
    final_data = {}

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text: continue

            matches = list(START_BLOCK_PATTERN.finditer(text))

            for idx, match in enumerate(matches):
                start = match.start()
                end = matches[idx+1].start() if idx + 1 < len(matches) else len(text)

                block = text[start:end]
                departure_time = match.group(1)

                t_id, t_data = parse_block(block, departure_time)

                if len(t_data["stations"]) > 1:
                    final_data[t_id] = t_data

    return final_data

if __name__ == "__main__":
    data = process_pdf(PDF_FILENAME)
    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Success! Output saved to {OUTPUT_FILENAME}")
