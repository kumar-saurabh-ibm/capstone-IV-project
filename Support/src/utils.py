from pathlib import Path

def remove_extension(filename):
    return Path(filename).stem