# build_tnved_struct.py
import pandas as pd
import re
from collections import defaultdict, OrderedDict
import json

CSV_PATH = "underwear.csv"
OUT_PATH = "undewear_tnved_res_struct.py"

CODE_PAT = re.compile(r"(?:<)?(\d{8,10})(?:>)?")

REAL_GENDERS = ("Без указания пола", "Жен.", "Муж.", "Унисекс")

def split_codes_with_descriptions(cell):
    if pd.isna(cell):
        return ()
    s = str(cell)
    matches = list(CODE_PAT.finditer(s))
    if not matches:
        return ()

    out = []
    for i, m in enumerate(matches):
        code = m.group(1).zfill(10)
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(s)
        desc = s[start:end].replace("\n"," ").replace("\r"," ")
        desc = re.sub(r"^[\s\-–—:•\u2022]*","",desc).strip()
        out.append((code, desc))

    return tuple(out)

def norm_kind(v):
    return str(v).strip().upper() if pd.notna(v) else ""

def norm_gender(v):
    if pd.isna(v) or not str(v).strip():
        return "Без указания пола"
    s = str(v).strip().lower()
    if "жен" in s: return "Жен."
    if "муж" in s: return "Муж."
    if "уни" in s: return "Унисекс"
    if "все" in s or "всё" in s or "all" in s:
        return "ВСЕ"
    return "Без указания пола"

def main():

    # LOAD CSV
    raw = pd.read_csv(CSV_PATH, header=None)
    raw.columns = list(range(raw.shape[1]))

    col_type, col_gender = 0, 1
    code_cols = tuple(c for c in raw.columns if c not in (col_type, col_gender))

    df = raw.dropna(how="all").copy()
    df[col_type] = df[col_type].ffill()
    df[col_gender] = df[col_gender].ffill()

    # Buckets: storing tuples only
    buckets = defaultdict(lambda: defaultdict(lambda: {"pairs": ()}))

    for _, row in df.iterrows():
        kind = norm_kind(row[col_type])
        gender = norm_gender(row[col_gender])
        if not kind:
            continue

        row_pairs_total = ()

        # collect codes from all code columns
        for cidx in code_cols:
            row_pairs_total += split_codes_with_descriptions(row[cidx])

        if gender == "ВСЕ":
            for real_gender in REAL_GENDERS:
                buckets[kind][real_gender]["pairs"] += row_pairs_total
        else:
            buckets[kind][gender]["pairs"] += row_pairs_total

    # Deduplicate → tuples only
    final = OrderedDict()

    for kind in sorted(buckets.keys()):
        final[kind] = OrderedDict()
        for gender, data in buckets[kind].items():
            pairs = data["pairs"]

            seen = set()
            merged = []
            for code, desc in pairs:
                if code not in seen:
                    merged.append((code, desc))
                    seen.add(code)

            if merged:
                merged = tuple(merged)
                codes = tuple(c for c, _ in merged)
                final[kind][gender] = (codes, merged)

    plain = {kind: dict(genders) for kind, genders in final.items()}

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n")
        f.write("UNDERWEAR_TNVED_DICT = ")
        f.write(repr(plain))

    print("Готово! Файл создан:", OUT_PATH)


if __name__ == "__main__":
    main()
