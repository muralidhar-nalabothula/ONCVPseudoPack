import os
import glob
import re
import shutil
import subprocess
import tempfile

ONCVPSP_DIR = "/Users/murali/Downloads/cspbbr3-nc-phonon-mlip/pseudo/oncvpsp/src"
EXECS = {
    "SR": os.path.join(ONCVPSP_DIR, "oncvpsp.x"),    # -> SR/X.psml
    "FR": os.path.join(ONCVPSP_DIR, "oncvpspr.x"),   # -> FR/X.psml
}

# File the patched ONCVPSP writes in its working directory
PSML_NAME = "ONCVPSPPSML"

for label in EXECS:
    os.makedirs(label, exist_ok=True)


def set_psfile_both(input_text):
    """Replace the psfile field (6th field of the first non-comment line) with 'both'."""
    lines = input_text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            tokens = stripped.split()
            if len(tokens) >= 6:
                tokens[5] = "both"
            else:
                tokens.append("both")
            lines[i] = "  " + "  ".join(tokens)
            break
    return "\n".join(lines) + "\n"


def find_psml(workdir):
    """Locate the PSML file written by ONCVPSP in workdir."""
    exact = os.path.join(workdir, PSML_NAME)
    if os.path.isfile(exact):
        return exact
    # Fallback: any file with 'psml' in its name (e.g. ONCVPSP.psml)
    for name in os.listdir(workdir):
        if "psml" in name.lower() and os.path.isfile(os.path.join(workdir, name)):
            return os.path.join(workdir, name)
    return None


def run_oncvpsp(exe, input_text, out_path):
    """Run ONCVPSP with stdin redirected from a real file (like `< input`).
    Returns (stdout, None) on success, (None, diagnostics) on failure."""
    with tempfile.TemporaryDirectory() as tmp:
        in_path = os.path.join(tmp, "input.in")
        with open(in_path, "w") as f:
            f.write(input_text)

        with open(in_path, "r") as in_f:
            result = subprocess.run(
                [exe], stdin=in_f, capture_output=True, text=True, cwd=tmp
            )

        found = find_psml(tmp)
        if found:
            shutil.move(found, out_path)
            return result.stdout, None

        diag = (
            f"returncode={result.returncode}\n"
            f"files in workdir: {os.listdir(tmp)}\n"
            f"stderr: {result.stderr.strip()[-500:]}\n"
            "last stdout lines:\n  "
            + "\n  ".join(result.stdout.strip().splitlines()[-10:])
        )
        return None, diag


def find_ghosts(out_text):
    ghosts = []
    for line in out_text.splitlines():
        if "WARNING - GHOST(+)" in line:
            parts = line.split()
            try:
                idx = parts.index("WARNING")
                energy = float(parts[idx - 2])
                if energy > 1.0:
                    ghosts.append(f"Safe Ghost: {energy} Ha (Harmless continuum resonance)")
                else:
                    ghosts.append(f"DANGER Ghost: {energy} Ha (Needs manual tuning!)")
            except (ValueError, IndexError):
                ghosts.append(f"Ghost detected: {line.strip()}")
    return ghosts


for filename in sorted(glob.glob("*.psp8")):
    # Element from filename: As_SR.psp8 -> As, 82_Pb_xxx.psp8 -> Pb
    match = re.search(r'_([A-Za-z]{1,2})_', filename)
    element = match.group(1) if match else filename.split('_')[0]

    with open(filename, "r") as f:
        content = f.read()

    input_match = re.search(r"<INPUT>\n(.*?)\n\s*</INPUT>", content, re.DOTALL | re.IGNORECASE)
    if not input_match:
        print(f"Skipping {element}: No <INPUT> block found.")
        continue

    input_text = set_psfile_both(input_match.group(1))

    for label, exe in EXECS.items():
        out_path = os.path.join(label, f"{element}.psml")
        stdout, diag = run_oncvpsp(exe, input_text, out_path)

        if stdout is None:
            print(f"\n--- {element} ({label}) ---")
            print(f"{PSML_NAME} was not written")
            print(diag)
            continue

        # Only print if ghosts were found
        ghosts = find_ghosts(stdout)
        if ghosts:
            print(f"\n--- {element} ({label}) ---")
            for g in ghosts:
                print(g)
