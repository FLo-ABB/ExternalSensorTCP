# This software is provided 'as-is', without any express or
# implied warranty. In no event will ABB be held liable for
# any damages arising from the use of this software.

import os
import sys

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
