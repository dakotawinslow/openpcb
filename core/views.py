from django.shortcuts import render, get_object_or_404

PROJECTS = [
    {
        "id": 1,
        "title": "RP2040 Breakout Board",
        "author": "jsmith",
        "description": (
            "A minimal breakout for the RP2040 with USB-C, LiPo charging circuit, "
            "and 2MB onboard flash. Designed in KiCad 7. All components are LCSC "
            "stocked for easy JLCPCB assembly. Fits a standard Raspberry Pi Pico "
            "footprint so existing Pico cases work out of the box."
        ),
        "license": "CC BY-SA 4.0",
        "tags": ["microcontroller", "rp2040", "usb-c", "breakout"],
        "downloads": 312,
        "stars": 87,
        "uploaded": "2025-11-04",
        "files": [
            {"name": "rp2040-breakout-gerbers.zip", "type": "Gerber",    "size": "48 KB"},
            {"name": "rp2040-breakout.kicad_pcb",   "type": "KiCad PCB", "size": "210 KB"},
            {"name": "bom.csv",                      "type": "BOM",       "size": "4 KB"},
            {"name": "schematic.pdf",                "type": "Schematic", "size": "312 KB"},
        ],
        "thumbnail": "https://placehold.co/400x300/1a4d2e/ffffff?text=RP2040+Breakout",
    },
    {
        "id": 2,
        "title": "Buck Converter Module — 5A 24V→5V",
        "author": "powerlab",
        "description": (
            "High-efficiency synchronous buck converter based on the LM5140. "
            "Input 8–36V, output 5V at up to 5A continuous. Features soft-start, "
            "overcurrent protection, and thermal shutdown. Designed for robotics and "
            "automation applications where a compact, reliable 5V rail is needed."
        ),
        "license": "MIT",
        "tags": ["power", "buck", "smps", "24v", "robotics"],
        "downloads": 198,
        "stars": 54,
        "uploaded": "2025-09-17",
        "files": [
            {"name": "buck-5a-gerbers.zip",    "type": "Gerber",    "size": "62 KB"},
            {"name": "buck-5a.kicad_pcb",      "type": "KiCad PCB", "size": "185 KB"},
            {"name": "buck-5a-bom.csv",        "type": "BOM",       "size": "3 KB"},
            {"name": "buck-5a-schematic.pdf",  "type": "Schematic", "size": "224 KB"},
        ],
        "thumbnail": "https://placehold.co/400x300/1a4d2e/ffffff?text=Buck+Converter",
    },
    {
        "id": 3,
        "title": "ESP32-S3 LoRa Node",
        "author": "rf_garage",
        "description": (
            "Long-range IoT node combining an ESP32-S3 with an SX1276 LoRa radio. "
            "Targets the 915 MHz ISM band. Includes a u.FL antenna connector, "
            "18650 battery holder with TP4056 charging, and deep-sleep current under "
            "12µA. Ideal for remote sensor deployments where WiFi doesn't reach."
        ),
        "license": "CC BY 4.0",
        "tags": ["esp32", "lora", "iot", "wireless", "battery"],
        "downloads": 441,
        "stars": 133,
        "uploaded": "2025-07-22",
        "files": [
            {"name": "lora-node-gerbers.zip",   "type": "Gerber",    "size": "54 KB"},
            {"name": "lora-node.kicad_pcb",     "type": "KiCad PCB", "size": "298 KB"},
            {"name": "lora-node-bom.csv",       "type": "BOM",       "size": "5 KB"},
            {"name": "lora-node-schematic.pdf", "type": "Schematic", "size": "401 KB"},
            {"name": "lora-node-3d.step",       "type": "3D Model",  "size": "1.2 MB"},
        ],
        "thumbnail": "https://placehold.co/400x300/1a4d2e/ffffff?text=LoRa+Node",
    },
    {
        "id": 4,
        "title": "4-Channel Thermocouple Interface",
        "author": "instru_works",
        "description": (
            "Read up to four K-type thermocouples over SPI using the MAX31856. "
            "Onboard 3.3V LDO and level shifters make it compatible with both 3.3V "
            "and 5V microcontrollers. Screw terminals for rugged wiring. Used in "
            "kiln monitoring, reflow oven control, and industrial temperature logging."
        ),
        "license": "CC BY-SA 4.0",
        "tags": ["sensor", "thermocouple", "spi", "temperature", "industrial"],
        "downloads": 127,
        "stars": 41,
        "uploaded": "2025-12-01",
        "files": [
            {"name": "tc-interface-gerbers.zip",   "type": "Gerber",    "size": "39 KB"},
            {"name": "tc-interface.kicad_pcb",     "type": "KiCad PCB", "size": "167 KB"},
            {"name": "tc-interface-bom.csv",       "type": "BOM",       "size": "3 KB"},
            {"name": "tc-interface-schematic.pdf", "type": "Schematic", "size": "188 KB"},
        ],
        "thumbnail": "https://placehold.co/400x300/1a4d2e/ffffff?text=Thermocouple+Interface",
    },
    {
        "id": 5,
        "title": "USB-C PD Trigger Board",
        "author": "jsmith",
        "description": (
            "Negotiate a fixed voltage (5V, 9V, 12V, or 20V) from any USB-C PD "
            "supply using the HUSB238. Solder jumpers select the target voltage. "
            "Screw terminal output, reverse-polarity protection, and an LED power "
            "indicator. A dead-simple way to use laptop chargers as lab bench supplies."
        ),
        "license": "MIT",
        "tags": ["usb-c", "power-delivery", "pd", "utility"],
        "downloads": 876,
        "stars": 210,
        "uploaded": "2026-01-15",
        "files": [
            {"name": "pd-trigger-gerbers.zip",   "type": "Gerber",    "size": "28 KB"},
            {"name": "pd-trigger.kicad_pcb",     "type": "KiCad PCB", "size": "134 KB"},
            {"name": "pd-trigger-bom.csv",       "type": "BOM",       "size": "2 KB"},
            {"name": "pd-trigger-schematic.pdf", "type": "Schematic", "size": "156 KB"},
        ],
        "thumbnail": "https://placehold.co/400x300/1a4d2e/ffffff?text=USB-C+PD+Trigger",
    },
]


def index(request):
    return render(request, 'core/index.html', {'projects': PROJECTS})


def explore(request):
    return render(request, 'core/explore.html', {'projects': PROJECTS})


def project_detail(request, id):
    project = next((p for p in PROJECTS if p['id'] == id), None)
    if project is None:
        from django.http import Http404
        raise Http404
    others = [p for p in PROJECTS if p['id'] != id][:2]
    return render(request, 'core/project_detail.html', {'project': project, 'others': others})
