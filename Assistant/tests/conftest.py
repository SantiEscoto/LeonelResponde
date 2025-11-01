import os
import sys

# Asegurar rutas para importaciones relativas a 'Assistant'
TESTS_DIR = os.path.dirname(__file__)
ASSISTANT_DIR = os.path.abspath(os.path.join(TESTS_DIR, '..'))
REPO_ROOT = os.path.abspath(os.path.join(ASSISTANT_DIR, '..'))

for path in (REPO_ROOT, ASSISTANT_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)