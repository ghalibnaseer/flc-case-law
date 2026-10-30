"""Derive structured fields (citations, reliance, outcome, provisions...) from entry text."""
import re
import citations as C

REL_MARK = re.compile(r'\b(?:[Rr]eliance|Rel\.|relying on)')
AGAINST_MARK = re.compile(r'\bAGAINST\b|(?:^|\n)\s*Against\b|\bAgainst:')

PPC_OFFENCES = {'34', '84', '109', '182', '201', '276', '302', '324', '334', '337', '367', '376', '377', '394', '406',
                '411', '420', '436', '452', '468', '471', '489', '496', '311', '338'}
CODES = [
    (r'PPC|P\.P\.C\.?|Penal Code', 'PPC'), (r'Cr\.?\s?P\.?\s?C\.?|CRPC|CrPc|Crpc|Cr\.P\.C', 'CrPC'),
    (r'QSO|Qanun', 'QSO'), (r'\bCPC\b|C\.P\.C', 'CPC'), (r'Const(?:itution)?\.?', 'Constitution'),
    (r'CNSA', 'CNSA'), (r'PECA', 'PECA 2016'), (r'Police\s+Order', 'Police Order 2002'),
    (r'Police Rules', 'Police Rules 1934'), (r'MFLO|Muslim Family Law', 'MFLO 1961'),
    (r'Succession Act', 'Succession Act'), (r'Juvenile Justice', 'Juvenile Justice System Act 2018'),
    (r'Contempt of Court Act', 'Contempt of Court Act 1976'), (r'Oath Act', 'Oaths Act'),
    (r'Child Marriage Restr', 'Child Marriage Restraint Act'), (r'Contract Act', 'Contract Act 1872'),
]
STATUTE_TAGS = [
    (r'PECA', 'PECA 2016'), (r'Police [Oo]rder', 'Police Order 2002'), (r'CNSA|9-?C\b', 'CNSA 1997'),
    (r'Child Marriage', 'Child Marriage Restraint Act'), (r'Juvenile Justice', 'Juvenile Justice System Act 2018'),
    (r'Muslim Family Law|MFLO', 'MFLO 1961'), (r'Illegal [Dd]ispos', 'Illegal Dispossession Act 2005'),
    (r'Guardian', 'Guardians and Wards Act 1890'), (r'Succession', 'Succession Act 1925'),
    (r'Contempt of Court', 'Contempt of Court Act 1976'), (r'Constitution|Const\.', 'Constitution of Pakistan 1973'),
    (r'NADRA', 'NADRA Ordinance 2000'), (r'Oath Act', 'Oaths Act'),
]

OUTCOMES = [
    (r'death sentence (?:was )?(?:converted|altered)|sentence (?:converted|altered)|converted into life', 'Sentence reduced'),
    (r'pre-?\s?arrest (?:bail )?(?:was )?confirm|bail confirm|confirmed\.', 'Bail confirmed'),
    (r'bail (?:was )?(?:allowed|granted)|\bbail allowed\b|released on statutory', 'Bail allowed'),
    (r'bail (?:was )?dismissed|bail dismissed|post-arrest bail dismissed|\bDismissed\.', 'Bail dismissed'),
    (r'cancellation of bail, which was allowed', 'Bail cancelled'),
    (r'\bacquitted\b', 'Acquitted'),
    (r'conviction (?:was )?(?:upheld|maintained)|sentence (?:maintained|upheld)|death sentence (?:maintained|upheld)|appeal dismissed', 'Conviction upheld'),
    (r'writ (?:petition )?allowed|petition (?:was )?allowed|writ allowed', 'Petition allowed'),
    (r'revision (?:was )?allowed|revision petition .{0,30}allowed', 'Revision allowed'),
    (r'appeal (?:was )?allowed', 'Appeal allowed'),
    (r'F\.?I\.?R\.? quashed', 'FIR quashed'),
    (r'suit decreed|decreed', 'Suit decreed'),
    (r'suit dismissed', 'Suit dismissed'),
    (r'remanded', 'Remanded'),
    (r'retrial ordered', 'Retrial ordered'), (r'retrial not ordered|not a fit case for retrial|retrial (?:order )?set aside|retrial (?:is )?not justified|retrial refused', 'Retrial refused'),
    (r'illegal|set aside', 'Order set aside / declared illegal'),
]


def split_sections(text):
    """Return (primary_text, reliance_text, against_text) by marker positions."""
    a = AGAINST_MARK.search(text)
    main, against = (text[:a.start()], text[a.start():]) if a else (text, '')
    r = REL_MARK.search(main)
    primary, rel = (main[:r.start()], main[r.start():]) if r else (main, '')
    return primary, rel, against


def uniq(seq):
    seen, out = set(), []
    for s in seq:
        if s['key'] not in seen:
            seen.add(s['key'])
            out.append(s)
    return out


def detect_outcome(text, subject):
    t = text.lower()
    # Prefer the last decisive statement in the entry
    best = None
    best_pos = -1
    for pat, label in OUTCOMES:
        for m in re.finditer(pat, t, re.I):
            if label.startswith('Bail') and not ('bail' in t):
                continue
            if label == 'Bail dismissed' and 'bail' not in t:
                continue
            if m.start() >= best_pos:
                best, best_pos = label, m.start()
    if best == 'Order set aside / declared illegal' and 'acquitted' in t:
        best = 'Acquitted'
    return best or ''


def provisions(text, subject):
    found = []
    for m in re.finditer(r'(?:\b[Ss]ection|\b[Ss]ec\.|\bu/s\.?|\bU/S|\bu/a|\b[Ss]\.|\bArt\.?|\bArticle|\bArts?\.)\s*'
                         r'((?:\d{1,3}(?:-?[A-Za-z])?(?:\s?\(\w{1,3}\))*(?:\s?(?:,|&|and|/|or)\s?)?)+)', text):
        nums = re.findall(r'\d{1,3}(?:-?[A-Za-z])?(?:\s?\(\w{1,3}\))*', m.group(1))
        tail = text[m.end():m.end() + 30]
        code = ''
        for pat, name in CODES:
            if re.match(r'^[\s,.\-:]*(?:read with\s*)?' + r'(?:' + pat + r')', tail, re.I):
                code = name
                break
        is_art = m.group(0).strip().lower().startswith('art')
        if not code and is_art:
            code = 'QSO' if 'QSO' in text or subject.startswith('Qanun') else ''
        for n in nums:
            n2 = re.sub(r'\s', '', n)
            base = re.match(r'\d+', n2).group(0)
            c = code
            if not c and base in PPC_OFFENCES and not is_art:
                c = 'PPC'
            if not c:
                continue
            label = (f'Art. {n2} {c}' if is_art else f's. {n2} {c}')
            if label not in found:
                found.append(label)
    for pat, name in STATUTE_TAGS:
        if re.search(pat, text) and not any(name.split()[0] in f for f in found):
            found.append(name)
    return found[:12]


def judges(text):
    js = []
    for m in re.finditer(r'(?:Justice|J\.|CJ)\s+([A-Z][A-Za-z.]+(?:\s+[A-Z][A-Za-z.]+){0,4})', text):
        name = m.group(1).strip(' .')
        name = re.sub(r'\s+(Vs|titled|Titled|v)\b.*$', '', name)
        if len(name) > 3 and name not in js:
            js.append(name)
    for m in re.finditer(r'\(([A-Z][A-Za-z ]+?)\s+J\.\)', text):
        if m.group(1) not in js:
            js.append(m.group(1))
    return js


def title(text, cites):
    m = re.search(r'[Tt]i[t]?led\s*:?\s*([A-Z][^,;()\n]*?\s(?:Vs\.?|vs\.?|v\.)\s[^,;()\n]+?)(?:[-,;(\n]|\.\s|\.$|$)', text)
    if m:
        return re.sub(r'\s+', ' ', m.group(1)).strip(' .')
    # "CITATION Name v. Name" style (older reports)
    m = re.search(r'(?:\d{1,4}),?\s+([A-Z][A-Za-z.\-\' ]{2,40}?\s(?:v\.|vs\.?|Vs\.?)\s[A-Z][A-Za-z.\-\' &]{2,50}?)(?:\.|$|\n)', text)
    if m:
        return m.group(1).strip(' .')
    return ''


def extract_fields(text, subject):
    primary_t, rel_t, against_t = split_sections(text)
    allc = C.parse(text)
    prim = uniq([c for c in C.parse(primary_t)])
    rel = uniq([c for c in C.parse(rel_t) if c['key'] not in {p['key'] for p in prim}])
    ag = uniq(C.parse(against_t))
    first = prim[0] if prim else (rel[0] if rel else None)
    courts = [c['court'] for c in prim if c['court']]
    issues = []
    for c in allc:
        for iss in c['issues']:
            issues.append(f"{c['raw']}: {iss}")
    return dict(
        citations=[c['key'] for c in prim],
        citations_raw=[c['raw'] for c in prim],
        relied=[c['key'] for c in rel],
        contrary=[c['key'] for c in ag],
        court=courts[0] if courts else '',
        year=int(first['year']) if first and str(first['year']).isdigit() and len(str(first['year'])) == 4 else None,
        judges=judges(text),
        title=title(text, prim),
        outcome=detect_outcome(text, subject),
        provisions=provisions(text, subject),
        parse_issues=sorted(set(issues)),
        _prim=[dict(key=c['key'], year=c['year'], series=c['series'], page=c['page']) for c in prim],
        _rel=[dict(key=c['key'], year=c['year'], series=c['series'], page=c['page']) for c in rel],
    )
