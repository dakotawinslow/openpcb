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


def detect_file_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    return FILE_TYPE_BY_EXTENSION.get(ext, 'Other')


# ── Photos ───────────────────────────────────────────────────────────────────

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024  # 20MB per photo
MAX_PHOTOS_PER_PROJECT = 20
