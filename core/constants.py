import os

# ── Design files ───────────────────────────────────────────────────────────

BLOCKED_FILE_EXTENSIONS = {
    '.bat',
    '.cmd',
    '.com',
    '.dll',
    '.exe',
    '.js',
    '.msi',
    '.ps1',
    '.py',
    '.sh',
    '.so',
    '.vbs',
}

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100MB per file
MAX_FILES_PER_PROJECT = 30

# fmt: off
FILE_TYPE_BY_EXTENSION = {
    # Gerber — legacy per-layer extensions (Protel/Altium convention)
    '.gbr': 'Gerber',  '.gtl': 'Gerber',  '.gbl': 'Gerber',
    '.gts': 'Gerber',  '.gbs': 'Gerber',  '.gto': 'Gerber',
    '.gbo': 'Gerber',  '.gtp': 'Gerber',  '.gbp': 'Gerber',
    '.gd1': 'Gerber',  '.gm1': 'Gerber',  '.gko': 'Gerber',
    '.gpb': 'Gerber',  '.gpt': 'Gerber',  '.g1':  'Gerber',
    '.g2':  'Gerber',  '.g3':  'Gerber',  '.g4':  'Gerber',
    '.gp1': 'Gerber',  '.gp2': 'Gerber',
    # Drill
    '.drl': 'Drill',   '.xln': 'Drill',   '.exc': 'Drill',
    # KiCad
    '.kicad_pcb': 'KiCad', '.kicad_sch': 'KiCad', '.kicad_pro': 'KiCad',
    '.kicad_mod': 'KiCad', '.kicad_sym': 'KiCad', '.kicad_wks': 'KiCad',
    # Eagle
    '.brd': 'Eagle',   '.sch': 'Eagle',
    # Altium
    '.pcbdoc': 'Altium', '.schdoc': 'Altium', '.prjpcb': 'Altium',
    # EasyEDA / LCSC
    '.json': 'EasyEDA',
    # Pick-and-place / BOM
    '.csv': 'BOM',     '.xlsx': 'BOM',     '.xls': 'BOM',
    # Documentation
    '.pdf': 'Document', '.txt': 'Document', '.md': 'Document',
    # Archives
    '.zip': 'Archive',  '.tar': 'Archive', '.gz': 'Archive',
    '.7z':  'Archive',  '.rar': 'Archive',
    # Images / renders
    '.png': 'Image',    '.jpg': 'Image',   '.jpeg': 'Image',
    '.svg': 'Image',    '.webp': 'Image',
}
# fmt: on


GERBER_EXTENSION_TO_LAYER = {
    '.gtl': ('top', 'copper'),
    '.gbl': ('bottom', 'copper'),
    '.gts': ('top', 'mask'),
    '.gbs': ('bottom', 'mask'),
    '.gto': ('top', 'silk'),
    '.gbo': ('bottom', 'silk'),
    '.gtp': ('top', 'paste'),
    '.gbp': ('bottom', 'paste'),
}

GERBER_DRILL_EXTENSIONS = {'.drl', '.xln'}

# KiCad-style: layer identified by filename suffix when extension is generic .gbr
GERBER_SUFFIX_TO_LAYER = {
    '-F_Cu': ('top', 'copper'),
    '-B_Cu': ('bottom', 'copper'),
    '-F_Mask': ('top', 'mask'),
    '-B_Mask': ('bottom', 'mask'),
    '-F_Silkscreen': ('top', 'silk'),
    '-B_Silkscreen': ('bottom', 'silk'),
    '-F_SilkS': ('top', 'silk'),
    '-B_SilkS': ('bottom', 'silk'),
    '-F_Paste': ('top', 'paste'),
    '-B_Paste': ('bottom', 'paste'),
}

GERBER_OUTLINE_SUFFIXES = {'-Edge_Cuts'}
GERBER_OUTLINE_EXTENSIONS = {'.gm1', '.gko'}


def detect_file_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    return FILE_TYPE_BY_EXTENSION.get(ext, 'Unknown')


# ── Photos ───────────────────────────────────────────────────────────────────

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024  # 20MB per photo
MAX_PHOTOS_PER_PROJECT = 20
