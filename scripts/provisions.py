"""Put provision tags and court names into one consistent form.

The same provision reaches the database in several spellings ("s. 489(f) PPC", "s. 489-F PPC",
"s. 489F PPC"), whether typed in the Sheet or picked out of the entry text. normalise() maps
them to one form so that the Provision filter lists each provision once.

The rules are deliberately narrow. A lettered suffix is rewritten only for sections known to be
either an inserted section (489-F PPC, 249-A CrPC) or a lettered clause (302(b) PPC, 9(c) CNSA).
Anything else is left exactly as written.
"""
import re

# Sections whose lettered members are separate, inserted sections: written "N-X".
INSERTED = {
    'PPC': {'120', '121', '123', '124', '153', '165', '171', '174', '216', '225', '295', '298', '310', '328',
            '336', '337', '338', '354', '364', '365', '366', '367', '371', '377', '381', '402', '462', '489',
            '493', '496', '498', '502'},
    'CrPC': {'22', '53', '164', '174', '198', '203', '249', '265', '339', '382', '402', '415', '491', '498',
             '514', '516', '539', '540', '544', '561'},
    'CPC': {'24', '26', '35'},
}
# Sections whose letters are clauses of one section: written "N(x)".
CLAUSED = {('PPC', '302'), ('CNSA', '9')}

ROMAN = {'1': 'i', '2': 'ii', '3': 'iii', '4': 'iv', '5': 'v', '6': 'vi'}
ARABIC = {'i': '1', 'ii': '2', 'iii': '3', 'iv': '4', 'v': '5', 'vi': '6', 'vii': '7', 'viii': '8', 'ix': '9'}

ACTS = r'PPC|CrPC|CPC|CNSA|QSO|Constitution|Police Order 2002'
LABEL = re.compile(r'^(s\.|Art\.)\s*(\d{1,3})(.*?)\s+(' + ACTS + r')$')
LETTER = re.compile(r'^(?:-?([A-Za-z])|\(([A-Za-z])\))(.*)$')

COURT_ALIASES = {'AJK High Court': 'AJ&K High Court'}


def normalise(label):
    s = ' '.join(str(label).split())
    m = LABEL.match(s)
    if not m:
        return s
    kind, base, suffix, act = m.group(1), m.group(2), m.group(3).strip(), m.group(4)

    # Article 10-A (fair trial) is an article of the Constitution; the Qanun-e-Shahadat has none.
    if kind == 'Art.' and base == '10' and re.fullmatch(r'-?A', suffix, re.I) and act in ('QSO', 'Constitution'):
        return 'Art. 10-A Constitution'
    # The Police Order 2002 is divided into Articles.
    if act == 'Police Order 2002':
        kind = 'Art.'

    lm = LETTER.match(suffix)
    if lm:
        letter, rest = lm.group(1) or lm.group(2), lm.group(3)
        if (act, base) in CLAUSED:
            if not rest:
                suffix = f'({letter.lower()})'
        elif base in INSERTED.get(act, ()):
            suffix = f'-{letter.upper()}{rest}'
            sub = re.fullmatch(r'\((\w{1,4})\)', rest)
            if sub:
                # 337-A and 337-F PPC number their kinds of hurt (i) to (vi); 265-F CrPC has sub-sections (1) to (7).
                if act == 'PPC' and base == '337' and letter.upper() in 'AF' and sub.group(1) in ROMAN:
                    suffix = f'-{letter.upper()}({ROMAN[sub.group(1)]})'
                elif act == 'CrPC' and base == '265' and sub.group(1).lower() in ARABIC:
                    suffix = f'-{letter.upper()}({ARABIC[sub.group(1).lower()]})'
    return f'{kind} {base}{suffix} {act}'


def normalise_list(labels):
    out = []
    for p in labels or []:
        n = normalise(p)
        if n and n not in out:
            out.append(n)
    return out


def normalise_court(name):
    return COURT_ALIASES.get(name, name)
