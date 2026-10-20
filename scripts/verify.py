"""
scripts/verify.py

Script de verification manuelle pre-commit (CI locale).
Verifie la syntaxe, l'integrite Git et les 94 tests unitaires.
"""

import os
import subprocess
import sys
from pathlib import Path

# Assure la compatibilite console Windows (cp1252 / UTF-8)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Couleurs ANSI pour terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_step(num: int, title: str) -> None:
    print(f"\n{YELLOW}{BOLD}[{num}/3] {title}...{RESET}")


def main() -> int:
    # Positionnement a la racine du projet
    root_dir = Path(__file__).resolve().parent.parent
    os.chdir(root_dir)

    print(f"\n{CYAN}{BOLD}======================================================{RESET}")
    print(f"{CYAN}{BOLD} >>> VERIFICATION PRE-COMMIT DU PROJET (CI LOCALE) <<<{RESET}")
    print(f"{CYAN}{BOLD}======================================================{RESET}")

    # 1. Verification de la syntaxe Python (compilation)
    print_step(1, "Verification de la syntaxe Python (compilation)")
    compile_res = subprocess.run(
        [sys.executable, "-m", "compileall", "src", "tests", "-q"]
    )
    if compile_res.returncode != 0:
        print(f"{RED}[FAIL] Erreur de syntaxe detectee dans les fichiers Python !{RESET}")
        return 1
    print(f"{GREEN}   -> [OK] Syntaxe Python 100% valide.{RESET}")

    # 2. Verification des fichiers sensibles / bases de donnees
    print_step(2, "Controle de l'etat Git (bases de donnees locales)")
    git_res = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=False
    )
    tracked_files = git_res.stdout.splitlines()
    forbidden = [
        f
        for f in tracked_files
        if "data/chroma" in f.replace("\\", "/") or "data/lexical.db" in f.replace("\\", "/")
    ]
    if forbidden:
        print(f"{RED}[FAIL] Attention : Des bases locales sont suivies par Git :{RESET}")
        for f in forbidden:
            print(f"{RED}   - {f}{RESET}")
        print(f"{RED}   Supprimez-les avec : git rm --cached [fichier]{RESET}")
        return 1
    print(f"{GREEN}   -> [OK] Aucune base de donnees locale suivie dans Git.{RESET}")

    # 3. Execution des tests unitaires
    print_step(3, "Execution de la suite de tests (94 tests)")
    test_res = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "tests"]
    )
    if test_res.returncode != 0:
        print(f"\n{RED}[FAIL] Des tests unitaires ont echoue !{RESET}")
        return 1

    print(f"\n{GREEN}{BOLD}======================================================{RESET}")
    print(f"{GREEN}{BOLD} [SUCCESS] TOUT EST AU VERT ! VOUS POUVEZ COMMIT EN TOUTE SECURITE.{RESET}")
    print(f"{GREEN}{BOLD}======================================================{RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
