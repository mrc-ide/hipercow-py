from pathlib import Path


def find_file_descend(filename, path):
    path = Path(path)
    root = Path(path.anchor)

    while path != root:
        attempt = path / filename
        if attempt.exists():
            return attempt.parent.resolve()
        path = path.parent

    return None
