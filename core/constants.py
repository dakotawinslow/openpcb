import os

# ── Design files ───────────────────────────────────────────────────────────

ALLOWED_FILE_EXTENSIONS = {
    '.zip',
    '.gbr',
    '.gtl',
    '.gbl',
    '.gts',
    '.gbs',
    '.gto',
    '.gbo',
    '.gtp',
    '.gbp',
    '.drl',
    '.xln',
    '.kicad_pcb',
    '.kicad_sch',
    '.kicad_pro',
    '.brd',
    '.sch',  # Eagle
    '.pdf',
    '.csv',
    '.txt',
    '.md',
}

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100MB per file
MAX_FILES_PER_PROJECT = 20

FILE_TYPE_BY_EXTENSION = {
    '.gbr': 'Gerber',
    '.gtl': 'Gerber',
    '.gbl': 'Gerber',
    '.gts': 'Gerber',
    '.gbs': 'Gerber',
    '.gto': 'Gerber',
    '.gbo': 'Gerber',
    '.gtp': 'Gerber',
    '.gbp': 'Gerber',
    '.drl': 'Gerber',
    '.xln': 'Gerber',
    '.kicad_pcb': 'KiCad',
    '.kicad_sch': 'KiCad',
    '.kicad_pro': 'KiCad',
    '.brd': 'Eagle',
    '.sch': 'Eagle',
    '.csv': 'BOM',
}


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
    return FILE_TYPE_BY_EXTENSION.get(ext, 'Other')


# ── Photos ───────────────────────────────────────────────────────────────────

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024  # 20MB per photo
MAX_PHOTOS_PER_PROJECT = 20
