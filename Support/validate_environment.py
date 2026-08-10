import importlib
import shutil
import subprocess
import sys

print("=" * 45)
print(" Customer 360 Environment Check")
print("=" * 45)

checks = [
    ("Python", True),
    ("pandas", importlib.util.find_spec("pandas") is not None),
    ("duckdb", importlib.util.find_spec("duckdb") is not None),
    ("faker", importlib.util.find_spec("faker") is not None),
    ("pytest", importlib.util.find_spec("pytest") is not None),
    ("streamlit", importlib.util.find_spec("streamlit") is not None),
]

for name, ok in checks:
    print(f"{name:<25} {'PASS' if ok else 'FAIL'}")

print(f"{'Python Version':<25} {sys.version.split()[0]}")
print(f"{'Git':<25} {'PASS' if shutil.which('git') else 'NOT REQUIRED'}")
print()
print("PySpark is intentionally not required for this capstone.")
print("Airflow, Docker and DataHub are trainer-led/optional.")
