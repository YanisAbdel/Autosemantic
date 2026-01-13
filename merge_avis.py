import glob
import os
import csv
import re

# --- CONFIGURATION ---
source_folder = 'avis/'
output_file = 'avis/consolidated_reviews_FINAL.csv'

# ANCIENNE REGEX (Trop permissive) : 
# index_pattern = re.compile(r'^\d+,')

# NOUVELLE REGEX (Blindée) :
# Elle cherche : Un nombre, une virgule, des espaces éventuels, et le mot "on" suivi d'un espace.
# "6409, on" -> MATCH (C'est une nouvelle ligne)
# "101,000 miles" -> NO MATCH (Pas de "on" après la virgule)
index_pattern = re.compile(r'^\d+,\s*on\s')

def extract_brand_from_filename(filename):
    """ Récupère la marque propre depuis le nom de fichier """
    basename = os.path.splitext(os.path.basename(filename))[0]
    raw_brand = basename.split('_')[-1]
    # Gestion CamelCase et Acronymes
    if raw_brand.isupper(): return raw_brand
    brand = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', raw_brand)
    return brand.strip()

# --- TRAITEMENT ---

all_files = [
    f for f in glob.glob(os.path.join(source_folder, '*.csv')) 
    if os.path.normpath(f) != os.path.normpath(output_file)
]

print(f"🛡️ Démarrage du nettoyage BLINDÉ sur {len(all_files)} fichiers...")

try:
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile)
        
        # En-têtes finaux
        final_headers = ['Index', 'Date', 'Author', 'Vehicle_Title', 'Review_Title', 'Review', 'Rating', 'Brand']
        writer.writerow(final_headers)
        
        total_rows = 0
        
        for filename in all_files:
            brand_name = extract_brand_from_filename(filename)
            print(f"   -> {brand_name}...", end="")
            
            with open(filename, 'r', encoding='utf-8', errors='replace') as infile:
                # Lecture brute de toutes les lignes
                lines = infile.readlines()
                if len(lines) > 0: lines = lines[1:] # Skip header du petit fichier
                
                buffer_line = ""
                file_rows = 0
                
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    
                    # C'est ici que la magie opère avec la nouvelle Regex
                    if index_pattern.match(line):
                        
                        # Si on a un buffer plein, on l'écrit (c'était la ligne d'avant)
                        if buffer_line:
                            try:
                                # On parse la ligne complète
                                parts = next(csv.reader([buffer_line]))
                                # On ajoute la marque
                                parts.append(brand_name)
                                writer.writerow(parts)
                                file_rows += 1
                                total_rows += 1
                            except:
                                pass # Ligne trop cassée
                        
                        # On commence la nouvelle ligne
                        buffer_line = line
                    else:
                        # C'est une suite (ex: "101,000 miles...")
                        # On l'ajoute au buffer avec un espace
                        buffer_line += " " + line
                
                # Écriture du dernier buffer en fin de fichier
                if buffer_line:
                    try:
                        parts = next(csv.reader([buffer_line]))
                        parts.append(brand_name)
                        writer.writerow(parts)
                        file_rows += 1
                        total_rows += 1
                    except:
                        pass
            
            print(f" OK ({file_rows})")

    print(f"\n✅ TERMINÉ ! {total_rows} avis propres (et les 101,000 miles sont gérés).")

except Exception as e:
    print(f"❌ Erreur : {e}")