# ---------------#
# --- Modules ---#
# ---------------#

import argparse
from datetime import datetime
from pathlib import Path
import sys

# Forcer l'encodage de la console sous Windows pour éviter les UnicodeEncodeError
if sys.platform == "win32": sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# -----------------#
# --- Fonctions ---#
# -----------------#

def ls(
    path_str: str = ".",
    sort_by: str = "name",
    ext_filter: str | None = None,
) -> list[dict]:
    """Récupère la liste des éléments d'un répertoire avec leurs métadonnées.

    Args:
        path_str (str): Chemin du répertoire cible.
        sort_by (str): Critère de tri ('name', 'size', 'date').
        ext_filter (str | None): Extension à filtrer (ex: '.py').

    Returns:
        list[dict]: Dictionnaire contenant les métadonnées de chaque élément.
    """
    target_path = Path(path_str).resolve()
    entries: list[dict] = []

    # Vérification et gestion des erreurs de chemin principal
    if not target_path.exists():
        print(f"Erreur: Le chemin '{target_path}' n'existe pas.", file=sys.stderr)
        return []
    if not target_path.is_dir():
        print(f"Erreur: Le chemin '{target_path}' n'est pas un dossier.",file=sys.stderr,)
        return []

    try:
        children = list(target_path.iterdir())
    except PermissionError:
        print(f"Erreur: Accès refusé au dossier '{target_path}'.", file=sys.stderr)
        return []
    for item in children:
        # Filtrage par extension (uniquement sur les fichiers)
        if ext_filter:
            formatted_ext = (ext_filter if ext_filter.startswith(".") else f".{ext_filter}")
            if item.is_file() and item.suffix.lower() != formatted_ext.lower():
                continue
        try:
            # Sécurité contre les liens symboliques et jonctions NTFS cassés ou inaccessibles
            if item.is_symlink():
                item_type = "link"
                stat_info = item.lstat()
            elif item.is_dir():
                item_type = "dossier"
                stat_info = item.stat()
            else:
                item_type = "fichier"
                stat_info = item.stat()

            raw_mtime = stat_info.st_mtime
            mtime_str = datetime.fromtimestamp(raw_mtime).strftime("%d/%m/%Y %H:%M")
            size_bytes = stat_info.st_size

            entries.append(
                {
                    "name": item.name,
                    "type": item_type,
                    "size": size_bytes,
                    "mtime_str": mtime_str,
                    "raw_mtime": raw_mtime,
                }
            )

        except PermissionError:
            print(f"[Accès Refusé] {item.name}", file=sys.stderr)  # Ne plante pas l'exécution
        except OSError as e:
            print(f"[Erreur E/S] {item.name}: {e}", file=sys.stderr)

    # Trier les résultats
    if sort_by == "size":
        entries.sort(key=lambda x: x["size"])
    elif sort_by == "date":
        entries.sort(key=lambda x: x["raw_mtime"])
    else:  # Par défaut: par nom (insensible à la casse)
        entries.sort(key=lambda x: x["name"].lower())

    return entries

# ------------#
# --- Main ---#
# ------------#

if __name__ == "__main__":

    # --- Lecture des arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Explorateur de répertoires optimisé Windows")
    parser.add_argument("path", nargs="?", default=".", help="Chemin du répertoire") # Répertoire à lire
    parser.add_argument( # Critères de tri (par nom, taille ou date)
        "--sort",
        choices=["name", "size", "date"],
        default="name",
        help="Trier par: name, size ou date",
    )
    parser.add_argument("--ext", help="Filtrer par extension de fichier (ex: .py ou py)") # Critère de filtrage par extension
    args = parser.parse_args()

    # --- Récupération et affichage des fichiers/répertoires lus dans le répertoire cible
    results = ls(args.path, sort_by=args.sort, ext_filter=args.ext)
    if results:
        for result in results:
            print(result)