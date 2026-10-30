"""Citation parsing for Pakistani and related law reports.

Shared by the one-off PDF converter and by the Google Sheets sync script,
so that citations typed by staff are normalised the same way.
"""
import re

SERIES = {
    'SCMR': 'SCMR', 'CLC': 'CLC', 'YLR': 'YLR', 'MLD': 'MLD', 'CLD': 'CLD',
    'PTD': 'PTD', 'SCJ': 'SCJ', 'CLJ': 'CLJ', 'PSC': 'PSC', 'PLC': 'PLC',
    'PCRLJ': 'PCrLJ', 'PCRLJ.': 'PCrLJ', 'CRLJ': 'CrLJ', 'SD': 'SD', 'LHC': 'LHC',
}
SERIES_RE = (r'(?:SCMR|CLC|YLR|MLD|CLD|PTD|SCJ|CLJ|PSC|PLC(?:\s*\(?C\.?S\.?\)?)?|'
             r'P\.?\s?C\s?r?\.?\s?R?\s?L\.?\s?J\.?|PCRLJ|PCrLJ|P\.Cr\.\s?LJ|CRLJ|Cr\.?\s?L\.?J\.?|SD|LHC)')

# Court / qualifier tokens that may sit between series and page, or after the page
COURT_RE = (r'(?:SC\s?\(Pak\.\)|HC\s?AJ\s?&\s?K|SC\s?AJ\s?&\s?K|AJ\s?&\s?K|SC|Lahore|Lah\.?|LAH|LHC|'
            r'Islamabad|ISB|Isb|Karachi|Kar\.?|KAR|Sindh|SINDH|Peshawar|Pesh\.?|PESH|'
            r'Balochistan|BALOCHISTAN|Balochsitan|Bal\.?|BAL|Quetta|Q\.?|GB|FSC|FC|PC|Dacca|Dac\.?|BJ|'
            r'RWP|DI\s?Khan\s?\(Pesh\)|CrC|Cr\.\s?C\.|\((?:Lah|Pesh|Kar)\.?\)|Civil|Cr\.|DB|\(DB\)|CS)')

PAGE = r'(?:pg\.?\s?)?\d{1,4}(?:\s*/\s*\d{1,4})*'

PAT_YEAR_FIRST = re.compile(
    r'(?<![\w/])(?P<year>(?:18|19|20)\d{2})\s+(?P<series>' + SERIES_RE + r')'
    r'(?P<mid>(?:[\s,]+' + COURT_RE + r')*)[\s,]*(?P<page>' + PAGE + r')'
    r'(?P<post>(?:[\s,]+(?:' + COURT_RE + r'))*)(?!\d)')

PAT_REPORT_FIRST = re.compile(
    r'(?<![\w/])(?P<rep>PLD|PLJ|NLR|AIR)\s+(?P<year>\d{4}|\d{2}(?!\d))(?P<mid>(?:[\s,]+' + COURT_RE + r')*)'
    r'[\s,.]*(?P<page>' + PAGE + r')(?!\d)')

PAT_NOTE = re.compile(
    r'(?<![\w/])(?:(?P<rep>PLJ)\s+(?P<y1>(?:18|19|20)\d{2})|(?P<y2>(?:18|19|20)\d{2})\s+(?P<series>' + SERIES_RE + r'))'
    r'(?P<mid>(?:[\s,]+' + COURT_RE + r')*)[\s,]+(?:[Nn]ote|NOTE)\.?\s?(?P<note>\d+)(?:[\s,]*pg\.?\s?\d+)?'
    r'(?P<post>(?:[\s,]+(?:' + COURT_RE + r'))*)(?!\d)')

PAT_OLD = re.compile(r'(?<![\w/])(?P<vol>\d{1,3})\s+(?P<rep>MIA|IC|Cr\.\s?LJ)\s+(?P<page>\d{1,4})')
PAT_ILR = re.compile(r'ILR\s+(?P<vol>\d+)\s+(?P<court>Lah)\.?\s+(?P<page>\d+)')

COURT_NAMES = [
    (r'HC\s?AJ\s?&\s?K', 'AJ&K High Court'), (r'SC\s?AJ\s?&\s?K', 'AJ&K Supreme Court'),
    (r'AJ\s?&\s?K', 'AJ&K'), (r'\bFSC\b', 'Federal Shariat Court'),
    (r'\bSC\b', 'Supreme Court'), (r'\bLHC\b|\bLah|LAH|Lahore|\bRWP\b|Multan', 'Lahore High Court'),
    (r'\bISB\b|\bIsb\b|Islamabad', 'Islamabad High Court'), (r'Sindh|SINDH|\bKar\b|KAR|Karachi', 'Sindh High Court'),
    (r'Pesh|PESH|Peshawar|DI\s?Khan', 'Peshawar High Court'),
    (r'Bal|BAL|Balochistan|BALOCHISTAN|Balochsitan|Quetta|\bQ\b', 'Balochistan High Court'),
    (r'\bGB\b', 'Gilgit-Baltistan Chief Court'), (r'\bFC\b', 'Federal Court'), (r'\bPC\b', 'Privy Council'),
    (r'Dac', 'Dacca High Court'), (r'\bBJ\b', 'Baluchistan Judicial Commissioner'),
]


def court_of(text):
    for pat, name in COURT_NAMES:
        if re.search(pat, text):
            return name
    return ''


def norm_series(s):
    s2 = re.sub(r'[\s.]', '', s).upper()
    if s2.startswith('PLC'):
        return 'PLC'
    if s2 in ('PCRLJ', 'PCRL J', 'PCRLJ.') or (s2.startswith('P') and 'RLJ' in s2 or s2 == 'PCRLJ'):
        return 'PCrLJ'
    if s2 in ('CRLJ',):
        return 'CrLJ'
    return SERIES.get(s2, s2)


def parse(text):
    """Return list of dicts: raw, key, year, series, page, court, start, end, issues."""
    out = []
    taken = []

    def free(a, b):
        return all(b <= x or a >= y for x, y in taken)

    for m in PAT_NOTE.finditer(text):
        if m.group('rep'):
            year, ser = m.group('y1'), 'PLJ'
            crc = 'CrC ' if re.search(r'Cr\.?\s?C', m.group('mid') or '') else ''
            key = f"PLJ {year} {crc}Note {m.group('note')}"
        else:
            year, ser = m.group('y2'), norm_series(m.group('series'))
            key = f"{year} {ser} Note {m.group('note')}"
        court = court_of((m.group('mid') or '') + ' ' + (m.group('post') or ''))
        out.append(dict(raw=m.group(0).strip(), key=key, year=year, series=ser, page='Note ' + m.group('note'),
                        court=court, start=m.start(), end=m.end(), issues=[]))
        taken.append((m.start(), m.end()))

    for m in PAT_REPORT_FIRST.finditer(text):
        if not free(m.start(), m.end()):
            continue
        rep, year, mid, page = m.group('rep'), m.group('year'), m.group('mid') or '', m.group('page')
        issues = []
        if len(year) == 2:
            issues.append('two-digit year')
        ctx = mid
        court = court_of(ctx)
        if (rep == 'PLD' or (rep == 'PLJ' and not re.search(r'Cr\.?\s?C', ctx))) and not court and not re.search(r'Q|Dac|BJ', ctx):
            issues.append('court missing')
        page = re.sub(r'^pg\.?\s?', '', page)
        pages = [p.strip() for p in page.split('/')]
        crc = 'CrC ' if re.search(r'Cr\.?\s?C', mid) else ''
        ctoken = re.sub(r'\s+', ' ', mid.strip(' ,'))
        for i, p in enumerate(pages):
            key = f'{rep} {year} {crc}{ctoken} {p}'.replace('  ', ' ').strip()
            out.append(dict(raw=m.group(0).strip(), key=normkey(key), year=year, series=rep,
                            page=p, court=court, start=m.start(), end=m.end(), issues=list(issues)))
        taken.append((m.start(), m.end()))

    for m in PAT_YEAR_FIRST.finditer(text):
        if not free(m.start(), m.end()):
            continue
        year, ser, mid, page, post = m.group('year'), norm_series(m.group('series')), m.group('mid') or '', m.group('page'), m.group('post') or ''
        court = court_of(mid + ' ' + post)
        if ser == 'SCMR':
            court = 'Supreme Court'
        issues = []
        if ser == 'CrLJ':
            issues.append('CrLJ series: Indian Criminal Law Journal or mislabelled PCrLJ?')
        if ser in ('SD', 'LHC'):
            issues.append(f'unrecognised report series "{ser}"')
        note = None
        page = re.sub(r'^pg\.?\s?', '', page)
        pages = [p.strip() for p in page.split('/')]
        for p in pages:
            if note:
                key = f'{year} {ser} Note {note.group(1)}'
            else:
                key = f'{year} {ser} {p}'
            out.append(dict(raw=m.group(0).strip(), key=normkey(key), year=year, series=ser, page=p,
                            court=court, start=m.start(), end=m.end(), issues=list(issues)))
        taken.append((m.start(), m.end()))

    for m in PAT_OLD.finditer(text):
        if not free(m.start(), m.end()):
            continue
        rep = re.sub(r'\s', '', m.group('rep'))
        out.append(dict(raw=m.group(0), key=f"{m.group('vol')} {rep} {m.group('page')}", year='', series=rep,
                        page=m.group('page'), court='', start=m.start(), end=m.end(), issues=[]))
        taken.append((m.start(), m.end()))
    for m in PAT_ILR.finditer(text):
        if not free(m.start(), m.end()):
            continue
        out.append(dict(raw=m.group(0), key=f"ILR {m.group('vol')} Lah {m.group('page')}", year='', series='ILR',
                        page=m.group('page'), court='Lahore', start=m.start(), end=m.end(), issues=[]))
    out.sort(key=lambda d: d['start'])
    return out


def normkey(k):
    k = re.sub(r'\s+', ' ', k).strip()
    # PLD keys keep a normalised court; drop noise tokens
    m = re.match(r'^(PLD|PLJ|NLR|AIR) (\d{2,4}) ?(CrC )?(.*?) ?((?:Note )?\d+)$', k)
    if m:
        rep, year, crc, court, page = m.groups()
        court = re.sub(r'Cr\.?\s?C\.?|[Nn]ote\.?\s?\d+|\bDB\b|\(DB\)|Civil|Cr\.', ' ', court)
        c = court_short(court)
        return ' '.join(x for x in [rep, year, (crc or '').strip(), c, page] if x)
    return k


def court_short(c):
    c = c.strip(' ,.')
    table = [
        (r'HC\s?AJ\s?&\s?K', 'AJ&K'), (r'SC\s?AJ\s?&\s?K', 'SC AJ&K'), (r'^SC\s?\(Pak\.\)$|^SC$|^SC\b', 'SC'),
        (r'Lah|LAH|Lahore', 'Lah'), (r'ISB|Isb|Islamabad', 'Isb'), (r'Kar|KAR|Karachi|Sindh|SINDH', 'Kar'),
        (r'Pesh|PESH|Peshawar', 'Pesh'), (r'Bal|BAL|Balochistan|BALOCHISTAN', 'Bal'), (r'^Q\.?$|Quetta', 'Quetta'),
        (r'FSC', 'FSC'), (r'^FC$', 'FC'), (r'^PC$', 'PC'), (r'Dac', 'Dacca'), (r'^BJ$', 'BJ'), (r'GB', 'GB'),
    ]
    for pat, name in table:
        if re.search(pat, c):
            return name
    return re.sub(r'[^\w&]', ' ', c).strip()
