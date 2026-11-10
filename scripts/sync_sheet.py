#!/usr/bin/env python3
"""Build data/cases.json from the firm's Google Sheet (published as CSV).

Usage:
    python scripts/sync_sheet.py <csv-url-or-path> [output.json]

The Google Sheet is the master copy. Staff add or edit rows there; this script
(run by the GitHub Action every few hours, or on demand) converts the sheet into
the JSON file the website reads. Citations are parsed and normalised so that the
same judgment links up across entries however it was typed.
"""
import csv, io, json, os, re, sys, urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import citations as C          # noqa: E402
from extract import extract_fields  # noqa: E402

COLUMNS = ['ID', 'Subject', 'Topic', 'Side', 'Entry', 'Citations', 'Relied Upon', 'Contrary Authority',
           'Case Title', 'Court', 'Judges', 'Outcome', 'Provisions', 'Status', 'Review Note', 'Updated',
           'Source Text', 'Heading']
STATUSES = {'verified': 'Verified', 'unverified': 'Unverified', 'needs correction': 'Needs correction',
            'under review': 'Needs correction', 'hidden': 'Hidden', 'draft': 'Hidden'}


def read_source(src):
    if re.match(r'^https?://', src):
        req = urllib.request.Request(src, headers={'User-Agent': 'flc-case-law-sync'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode('utf-8-sig')
    else:
        raw = open(src, encoding='utf-8-sig').read()
    if raw.lstrip().startswith('<'):
        sys.exit('ERROR: the sheet URL returned a web page, not CSV. Check that the sheet is published to the web as CSV.')
    return list(csv.DictReader(io.StringIO(raw)))


def split_list(v):
    return [x.strip() for x in re.split(r'[;\n]+', v or '') if x.strip()]


def keys_from(text):
    return [c['key'] for c in C.parse(text or '')]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), '..', 'data', 'cases.json')
    rows = read_source(src)
    missing = [c for c in ('Subject', 'Entry') if rows and c not in rows[0]]
    if missing:
        sys.exit(f'ERROR: sheet is missing required column(s): {", ".join(missing)}')

    records, seen, warnings = [], set(), []
    for n, row in enumerate(rows, start=2):  # row 1 is the header
        row = {k.strip() if k else k: (v or '').strip() for k, v in row.items()}
        entry, subject = row.get('Entry', ''), row.get('Subject', '')
        if not entry and not subject:
            continue
        if not entry or not subject:
            warnings.append(f'row {n}: skipped (Subject and Entry are both required)')
            continue
        status = STATUSES.get(row.get('Status', '').lower(), 'Unverified')
        if status == 'Hidden':
            continue
        rid = row.get('ID') or f'ROW-{n:04d}'
        if rid in seen:
            warnings.append(f'row {n}: duplicate ID {rid}; renamed')
            rid = f'{rid}-{n}'
        seen.add(rid)

        auto = extract_fields(entry, subject)
        cites = keys_from(row.get('Citations')) or auto['citations']
        relied = keys_from(row.get('Relied Upon')) if row.get('Relied Upon') else auto['relied']
        contrary = keys_from(row.get('Contrary Authority')) if row.get('Contrary Authority') else auto['contrary']
        relied = [k for k in relied if k not in cites]
        year = None
        for k in cites + relied:
            m = re.search(r'\b(1[89]\d{2}|20\d{2})\b', k)
            if m:
                year = int(m.group(1))
                break
        court = row.get('Court') or auto['court']
        if not court and cites:
            parsed = C.parse(row.get('Citations') or entry)
            court = next((c['court'] for c in parsed if c['court']), '')
        side = row.get('Side', '').title()
        if side not in ('Accused', 'Complainant'):
            side = ''
        records.append(dict(
            id=rid, subject=subject, topic=row.get('Topic', ''), side=side,
            heading=row.get('Heading', ''), text=entry,
            citations=cites, relied=relied, contrary=contrary,
            title=row.get('Case Title') or auto['title'], court=court, year=year,
            judges=split_list(row.get('Judges')) or auto['judges'],
            outcome=row.get('Outcome') or auto['outcome'],
            provisions=split_list(row.get('Provisions')) or auto['provisions'],
            status=status, updated=row.get('Updated', ''),
        ))

    if len(records) < 10:
        sys.exit(f'ERROR: only {len(records)} usable rows found; refusing to overwrite the database.')
    payload = dict(generated=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), count=len(records), records=records)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    old = None
    if os.path.exists(out):
        try:
            old = json.load(open(out, encoding='utf-8'))
        except Exception:
            pass
    if old and old.get('records') == records:
        print(f'No changes ({len(records)} entries).')
        return
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
    print(f'Wrote {len(records)} entries to {out}')
    for w in warnings:
        print('WARNING:', w)


if __name__ == '__main__':
    main()
