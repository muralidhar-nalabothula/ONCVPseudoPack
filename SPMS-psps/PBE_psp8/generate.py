import os
import glob
import subprocess
import re

ONCVPSP_EXEC = "/Users/murali/Downloads/scratch/oncvpsp/build/bin/oncvpspr.x"

for filename in glob.glob("*.psp8"):
    
    # Skip previously generated temp, SR, or FR files to prevent loops
    if "_SR.psp8" in filename or "_FR.psp8" in filename or "_temp" in filename:
        continue

    # Extract the element name from the file (e.g., 82_Pb_... -> Pb)
    match = re.search(r'_([A-Za-z]{1,2})_', filename)
    element = match.group(1) if match else filename.split('_')[0]

    sr_filename = f"{element}_SR.psp8"
    os.rename(filename, sr_filename)

    with open(sr_filename, "r") as f:
        content = f.read()

    # The input block in psp8 files is enclosed in <INPUT> tags
    input_match = re.search(r"<INPUT>\n(.*?)\n\s*</INPUT>", content, re.DOTALL | re.IGNORECASE)
    
    if not input_match:
        print(f"Skipping {element}: No <INPUT> block found.")
        continue

    # Extract the raw input string
    input_text = input_match.group(1)

    temp_in = f"{element}_temp.in"
    temp_out = f"{element}_temp.out"

    with open(temp_in, "w") as f:
        f.write(input_text)

    # Run the fully relativistic executable
    with open(temp_out, "w") as out_f, open(temp_in, "r") as in_f:
        subprocess.run([ONCVPSP_EXEC], stdin=in_f, stdout=out_f, stderr=subprocess.DEVNULL)

    with open(temp_out, "r") as f:
        out_lines = f.readlines()

    fr_filename = f"{element}_FR.psp8"
    capture = False
    
    # Extract the generated psp8 block and save to the new FR file
    with open(fr_filename, "w") as f:
        for line in out_lines:
            if "END_PSP" in line:
                capture = False
            
            if capture:
                f.write(line)
                
            if "PSPCODE8" in line:
                capture = True

    # Check for ghost states in the output
    ghosts = []
    for line in out_lines:
        if "WARNING - GHOST(+)" in line:
            parts = line.split()
            try:
                warning_idx = parts.index("WARNING")
                energy = float(parts[warning_idx - 2])
                
                if energy > 1.0:
                    ghosts.append(f"Safe Ghost: {energy} Ha (Harmless continuum resonance)")
                else:
                    ghosts.append(f"DANGER Ghost: {energy} Ha (Needs manual tuning!)")
                    
            except (ValueError, IndexError):
                ghosts.append(f"Ghost detected: {line.strip()}")

    # Only print to console if ghosts were found
    if ghosts:
        print(f"\n--- {element} ---")
        for g in ghosts:
            print(g)

    # Clean up the temporary input and output files
    if os.path.exists(temp_in):
        os.remove(temp_in)
        
    if os.path.exists(temp_out):
        os.remove(temp_out)
