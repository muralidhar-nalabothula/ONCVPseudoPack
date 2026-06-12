import os
import glob
import subprocess
import re

ONCVPSP_EXEC = "/Users/murali/Downloads/scratch/oncvpsp/build/bin/oncvpspr.x"

for filename in glob.glob("*.upf"):
    if "_SR.upf" in filename or "_FR.upf" in filename:
        continue

    match = re.search(r'_([A-Za-z]{1,2})_', filename)
    element = match.group(1) if match else filename.split('_')[0]

    sr_filename = f"{element}_SR.upf"
    os.rename(filename, sr_filename)

    with open(sr_filename, "r") as f:
        content = f.read()

    input_match = re.search(r"<PP_INPUTFILE>\n(.*?)\n\s*</PP_INPUTFILE>", content, re.DOTALL)
    if not input_match:
        print(f"Skipping {element}: No PP_INPUTFILE block found.")
        continue

    temp_in = f"{element}_temp.in"
    temp_out = f"{element}_temp.out"

    with open(temp_in, "w") as f:
        f.write(input_match.group(1))

    with open(temp_out, "w") as out_f, open(temp_in, "r") as in_f:
        subprocess.run([ONCVPSP_EXEC], stdin=in_f, stdout=out_f)

    with open(temp_out, "r") as f:
        out_lines = f.readlines()

    fr_filename = f"{element}_FR.upf"
    capture = False
    with open(fr_filename, "w") as f:
        for line in out_lines:
            if "END_PSP" in line:
                capture = False
            
            if capture:
                f.write(line)
                
            if "PSP_UPF" in line:
                capture = True

    print(f"\n--- {element} ---")
    ghosts_found = False

    for line in out_lines:
        if "WARNING - GHOST(+)" in line:
            ghosts_found = True
            parts = line.split()
            try:
                warning_idx = parts.index("WARNING")
                energy = float(parts[warning_idx - 2])
                
                if energy > 1.0:
                    print(f"Safe Ghost: {energy} Ha (Harmless continuum resonance)")
                else:
                    print(f"DANGER Ghost: {energy} Ha (Needs manual tuning!)")
                    
            except (ValueError, IndexError):
                print(f"Ghost detected: {line.strip()}")

    if not ghosts_found:
        print("Clean: No ghosts detected")

    if os.path.exists(temp_in):
        os.remove(temp_in)
        
    if os.path.exists(temp_out):
        os.remove(temp_out)
