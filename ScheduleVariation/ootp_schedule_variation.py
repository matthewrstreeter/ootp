import argparse
import xml.etree.ElementTree as ET
import random
import os
import glob
import sys

def parse_divisions_from_filename(filename):
    """
    Parses the OOTP schedule filename to determine the league structure.
    Returns a list of lists containing sequential team IDs per division.
    """
    base_name = os.path.splitext(os.path.basename(filename))[0]
    parts = base_name.split('_') 
    
    divisions = []
    current_team_id = 1
    
    for part in parts:
        if part.startswith('T') and part[1:].isdigit():
            num_teams = int(part[1:])
            division_teams = list(range(current_team_id, current_team_id + num_teams))
            divisions.append(division_teams)
            current_team_id += num_teams
            
    if not divisions:
        raise ValueError(f"Could not parse team structure from filename '{filename}'. Ensure it follows OOTP naming conventions.")
        
    return divisions


def generate_schedule_variants(input_file, output_prefix=None, num_variants=6):
    """
    Generates schedule variants by shuffling teams within divisions and alternating home/away matchups.
    """
    divisions = parse_divisions_from_filename(input_file)
    
    if not output_prefix:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_prefix = f"{base_name}_v"

    for year in range(1, num_variants + 1):
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        tree = ET.parse(input_file, parser=parser)
        root = tree.getroot()
        games = root.find("GAMES")

        mapping = {}
        for div in divisions:
            shuffled = div.copy()
            if year > 1:
                random.shuffle(shuffled)
            for orig, new in zip(div, shuffled):
                mapping[str(orig)] = str(new)

        for game in games.findall("GAME"):
            away = mapping[game.get("away")]
            home = mapping[game.get("home")]
            
            if year % 2 == 0:
                game.set("away", home)
                game.set("home", away)
            else:
                game.set("away", away)
                game.set("home", home)

        filename = f"{output_prefix}{year}.lsdl"
        tree.write(filename, encoding="ISO-8859-1", xml_declaration=True)
        print(f"Generated: {filename} based on parsed structure: {divisions}")


# --- Execution ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate OOTP schedule XML variants.")
    
    # The default is now 'None' so the script knows to trigger the auto-detect logic if omitted
    parser.add_argument("-i", "--input", type=str, default=None, help="The base OOTP schedule file to parse. Auto-detects if omitted.")
    parser.add_argument("-v", "--variants", type=int, default=6, help="Number of schedule variants to generate.")
    
    args = parser.parse_args()
    
    target_file = args.input
    
    # If no file is explicitly provided via command line, scan the current directory
    if not target_file:
        lsdl_files = glob.glob("*.lsdl")
        
        if not lsdl_files:
            print("Error: No .lsdl files found in the current directory.")
            print("Please place a schedule file in this folder or specify one using the -i flag.")
            sys.exit(1)
            
        elif len(lsdl_files) == 1:
            target_file = lsdl_files[0]
            print(f"Auto-selected schedule file: {target_file}\n")
            
        else:
            print("Multiple .lsdl files found in the current directory. Please select one:")
            for idx, file in enumerate(lsdl_files):
                print(f"  [{idx + 1}] {file}")
                
            # Keep prompting until the user enters a valid number from the list
            while True:
                try:
                    choice = int(input("\nEnter the number of the file to use: "))
                    if 1 <= choice <= len(lsdl_files):
                        target_file = lsdl_files[choice - 1]
                        print(f"\nSelected: {target_file}\n")
                        break
                    else:
                        print(f"Please enter a number between 1 and {len(lsdl_files)}.")
                except ValueError:
                    print("Invalid input. Please enter a valid number.")
                    
    # Run the generator with the finalized target file
    generate_schedule_variants(
        input_file=target_file, 
        num_variants=args.variants
    )