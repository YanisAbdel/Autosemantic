"""
Script de nettoyage pour vehicles_scraped.json
Normalise les données selon les concepts SKOS de l'ontologie
"""

import json
import re
from pathlib import Path

# ============================================================================
# Mappings vers concepts SKOS (alignés avec ontologie AutoSemantic)
# ============================================================================

FUEL_TYPE_MAPPING = {
    'Regular': 'Regular',
    'Premium': 'Premium',
    'Gasoline': 'Regular',
    'Petrol': 'Regular',
    'Diesel': 'Diesel',
    'Electric': 'Electric',
    'Electricity': 'Electric',
    'Hybrid': 'Hybrid',
    'Plug-in Hybrid': 'PlugInHybrid',
    'E85': 'E85',
    'CNG': 'CNG',
}

DRIVE_TYPE_MAPPING = {
    'FrontWheelDrive': 'FrontWheelDrive',
    'FWD': 'FrontWheelDrive',
    'Front-Wheel Drive': 'FrontWheelDrive',
    'RearWheelDrive': 'RearWheelDrive',
    'RWD': 'RearWheelDrive',
    'Rear-Wheel Drive': 'RearWheelDrive',
    'AllWheelDrive': 'AllWheelDrive',
    'AWD': 'AllWheelDrive',
    'All-Wheel Drive': 'AllWheelDrive',
    'FourWheelDrive': 'FourWheelDrive',
    '4WD': 'FourWheelDrive',
    'Four-Wheel Drive': 'FourWheelDrive',
    '4-Wheel Drive': 'FourWheelDrive',
}

VEHICLE_CLASS_MAPPING = {
    'Sedan': 'Sedan',
    'SUV': 'SUV',
    'Truck': 'Truck',
    'Van': 'Van',
    'Coupe': 'Coupe',
    'Convertible': 'Convertible',
    'Hatchback': 'Hatchback',
    'Wagon': 'Wagon',
    'Station Wagon': 'Wagon',
    'Minivan': 'Minivan',
    'Subcompact Car': 'SubcompactCar',
    'Compact Car': 'CompactCar',
    'Midsize Car': 'MidsizeCar',
    'Large Car': 'LargeCar',
    'Small SUV': 'SmallSUV',
    'Standard SUV': 'StandardSUV',
    'Pickup Truck': 'PickupTruck',
}

TRANSMISSION_MAPPING = {
    # Automatiques
    'Automatic': 'Automatic',
    'Auto': 'Automatic',
    'A/T': 'Automatic',
    'AT': 'Automatic',
    # Manuelles
    'Manual': 'Manual',
    'M/T': 'Manual',
    'MT': 'Manual',
    # CVT
    'CVT': 'CVT',
    'Continuously Variable': 'CVT',
    # Dual Clutch
    'Dual Clutch': 'DualClutch',
    'DCT': 'DualClutch',
    'DSG': 'DualClutch',
    # Automated Manual
    'Automated Manual': 'AutomatedManual',
    'AMT': 'AutomatedManual',
}

# Mappings fabricants spéciaux
MANUFACTURER_MAPPING = {
    'Mercedes-Benz': 'Mercedes_Benz',
    'Alfa Romeo': 'Alfa_Romeo',
    'Aston Martin': 'Aston_Martin',
    'Land Rover': 'Land_Rover',
    'Rolls-Royce': 'Rolls_Royce',
    'AM General': 'AM_General',
}


def clean_manufacturer_name(name):
    """Nettoie les noms de fabricants"""
    if not name:
        return None
    
    # Cas spéciaux
    if name in MANUFACTURER_MAPPING:
        return MANUFACTURER_MAPPING[name]
    
    # Enlève caractères spéciaux sauf tirets et underscores
    cleaned = re.sub(r'[^\w\s-]', '', name)
    cleaned = cleaned.strip()
    
    # Remplace espaces et tirets par underscores
    cleaned = cleaned.replace(' ', '_')
    cleaned = cleaned.replace('-', '_')
    
    return cleaned


def normalize_fuel_type(fuel):
    """Normalise le type de carburant"""
    if not fuel:
        return None
    
    fuel = fuel.strip()
    return FUEL_TYPE_MAPPING.get(fuel, fuel)


def normalize_drive_type(drive):
    """Normalise le type de transmission (FWD/RWD/AWD)"""
    if not drive:
        return None
    
    drive = drive.strip()
    return DRIVE_TYPE_MAPPING.get(drive, drive)


def normalize_vehicle_class(vclass):
    """Normalise la classe de véhicule"""
    if not vclass:
        return None
    
    vclass = vclass.strip()
    return VEHICLE_CLASS_MAPPING.get(vclass, vclass)


def normalize_transmission(trans):
    """Normalise le type de transmission"""
    if not trans:
        return None
    
    trans_str = trans.strip()
    
    # Chercher des patterns dans la chaîne
    trans_upper = trans_str.upper()
    
    # Automatique
    if 'AUTOMATIC' in trans_upper or 'AUTO' in trans_upper or 'TRONIC' in trans_upper:
        # Extraire le nombre de vitesses si présent
        match = re.search(r'(\d+)[-\s]*(?:SPEED|SPD|G)', trans_str, re.IGNORECASE)
        if match:
            speed = match.group(1)
            return f"Automatic_{speed}speed"
        return 'Automatic'
    
    # Manuelle
    if 'MANUAL' in trans_upper or 'M/T' in trans_upper:
        match = re.search(r'(\d+)[-\s]*(?:SPEED|SPD)', trans_str, re.IGNORECASE)
        if match:
            speed = match.group(1)
            return f"Manual_{speed}speed"
        return 'Manual'
    
    # CVT
    if 'CVT' in trans_upper or 'CONTINUOUSLY' in trans_upper:
        return 'CVT'
    
    # Dual Clutch
    if 'DUAL' in trans_upper or 'DCT' in trans_upper or 'DSG' in trans_upper:
        return 'DualClutch'
    
    # Par défaut, nettoyer la chaîne
    cleaned = re.sub(r'[^\w\s-]', '', trans_str)
    cleaned = cleaned.replace(' ', '_')
    cleaned = cleaned.replace('-', '_')
    return cleaned


def clean_model_name(model_name):
    """Nettoie le nom du modèle"""
    if not model_name:
        return None
    
    # Enlever les mots de description communs en fin
    stop_words = ['Sedan', 'Coupe', 'Convertible', 'Wagon', 'Hatchback',
                  'SUV', 'Truck', 'Van', 'AWD', '4WD', 'FWD', 'RWD']
    
    cleaned = model_name.strip()
    
    # Ne garder que les parties significatives
    return cleaned


def validate_numeric_field(value, field_name, min_val=None, max_val=None):
    """Valide et nettoie les champs numériques"""
    if value is None:
        return None
    
    try:
        # Si c'est un dict (comme mpgHighway avec UK/US), prendre la première valeur
        if isinstance(value, dict):
            value = list(value.values())[0]
        
        num_val = float(value)
        
        # Validation des bornes
        if min_val is not None and num_val < min_val:
            print(f"  Warning: {field_name}={num_val} < {min_val} (ignoré)")
            return None
        if max_val is not None and num_val > max_val:
            print(f"  Warning: {field_name}={num_val} > {max_val} (ignoré)")
            return None
        
        return num_val
    except (ValueError, TypeError) as e:
        print(f"  Warning: Invalid {field_name}={value} ({e})")
        return None


def clean_vehicle(vehicle):
    """Nettoie un véhicule individuel"""
    cleaned = {
        'id': vehicle.get('id')
    }
    
    # URL source
    if 'sourceUrl' in vehicle:
        cleaned['sourceUrl'] = vehicle['sourceUrl']
    
    # Manufacturer
    manufacturer = vehicle.get('manufacturer')
    if manufacturer:
        cleaned['manufacturer'] = clean_manufacturer_name(manufacturer)
    
    # Model Name
    model_name = vehicle.get('modelName')
    if model_name:
        cleaned['modelName'] = clean_model_name(model_name)
    
    # Year
    year = validate_numeric_field(vehicle.get('year'), 'year', 1900, 2030)
    if year:
        cleaned['year'] = int(year)
    
    # Fuel Type
    fuel = vehicle.get('fuelType')
    if fuel:
        normalized_fuel = normalize_fuel_type(fuel)
        if normalized_fuel:
            cleaned['fuelType'] = normalized_fuel
    
    # Transmission
    trans = vehicle.get('transmission')
    if trans:
        normalized_trans = normalize_transmission(trans)
        if normalized_trans:
            cleaned['transmission'] = normalized_trans
    
    # Drive Type
    drive = vehicle.get('driveType')
    if drive:
        normalized_drive = normalize_drive_type(drive)
        if normalized_drive:
            cleaned['driveType'] = normalized_drive
    
    # Vehicle Class
    vclass = vehicle.get('vehicleClass')
    if vclass:
        normalized_vclass = normalize_vehicle_class(vclass)
        if normalized_vclass:
            cleaned['vehicleClass'] = normalized_vclass
    
    # Engine Displacement (0.5 - 10.0 litres)
    displacement = validate_numeric_field(
        vehicle.get('engineDisplacement'), 
        'engineDisplacement', 
        0.5, 
        10.0
    )
    if displacement:
        cleaned['engineDisplacement'] = round(displacement, 2)
    
    # Number of Cylinders (1 - 16)
    cylinders = validate_numeric_field(
        vehicle.get('numberOfCylinders'),
        'numberOfCylinders',
        1,
        16
    )
    if cylinders:
        cleaned['numberOfCylinders'] = int(cylinders)
    
    # Horsepower (20 - 2000 HP)
    hp = validate_numeric_field(
        vehicle.get('horsepower'),
        'horsepower',
        20,
        2000
    )
    if hp:
        cleaned['horsepower'] = int(hp)
    
    # MPG City (5 - 150)
    mpg_city = validate_numeric_field(
        vehicle.get('mpgCity'),
        'mpgCity',
        5,
        150
    )
    if mpg_city:
        cleaned['mpgCity'] = round(mpg_city, 1)
    
    # MPG Highway (5 - 150)
    mpg_highway = validate_numeric_field(
        vehicle.get('mpgHighway'),
        'mpgHighway',
        5,
        150
    )
    if mpg_highway:
        cleaned['mpgHighway'] = round(mpg_highway, 1)
    
    return cleaned


def clean_json_data(input_file='vehicles_scraped.json', output_file='vehicles_scraped_clean.json'):
    """Nettoie le fichier JSON des véhicules scrapés"""
    
    # Résoudre les chemins relatifs vers 2_data_sources/unstructured/
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "2_data_sources" / "unstructured"
    
    # Si chemins relatifs, les résoudre vers data_dir
    if not Path(input_file).is_absolute():
        input_file = data_dir / input_file
    if not Path(output_file).is_absolute():
        output_file = data_dir / output_file
    
    print("="*60)
    print("NETTOYAGE DES DONNÉES SCRAPPÉES")
    print("="*60)
    
    # Charger le JSON
    print(f"\nChargement de {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        vehicles = json.load(f)
    
    print(f"  {len(vehicles)} véhicules chargés")
    
    # Nettoyer chaque véhicule
    print("\nNettoyage des données...")
    cleaned_vehicles = []
    empty_count = 0
    
    for i, vehicle in enumerate(vehicles):
        cleaned = clean_vehicle(vehicle)
        
        # Ne garder que les véhicules avec données suffisantes
        # (au moins: manufacturer OU modelName, ET au moins 3 autres champs)
        required_fields = ['manufacturer', 'modelName']
        has_required = any(cleaned.get(field) for field in required_fields)
        
        other_fields = [k for k in cleaned.keys() if k not in ['id', 'sourceUrl'] + required_fields]
        has_enough_data = len(other_fields) >= 3
        
        if has_required and has_enough_data:
            cleaned_vehicles.append(cleaned)
        else:
            empty_count += 1
            print(f"  [ID {vehicle.get('id')}] Données insuffisantes (ignoré)")
    
    print(f"\nRésultats:")
    print(f"  Véhicules nettoyés: {len(cleaned_vehicles)}")
    print(f"  Véhicules ignorés: {empty_count}")
    
    # Statistiques
    print("\nStatistiques après nettoyage:")
    stats = {
        'manufacturer': sum(1 for v in cleaned_vehicles if v.get('manufacturer')),
        'modelName': sum(1 for v in cleaned_vehicles if v.get('modelName')),
        'year': sum(1 for v in cleaned_vehicles if v.get('year')),
        'fuelType': sum(1 for v in cleaned_vehicles if v.get('fuelType')),
        'transmission': sum(1 for v in cleaned_vehicles if v.get('transmission')),
        'driveType': sum(1 for v in cleaned_vehicles if v.get('driveType')),
        'vehicleClass': sum(1 for v in cleaned_vehicles if v.get('vehicleClass')),
        'engineDisplacement': sum(1 for v in cleaned_vehicles if v.get('engineDisplacement')),
        'numberOfCylinders': sum(1 for v in cleaned_vehicles if v.get('numberOfCylinders')),
        'horsepower': sum(1 for v in cleaned_vehicles if v.get('horsepower')),
    }
    
    for field, count in stats.items():
        percentage = (count / len(cleaned_vehicles) * 100) if cleaned_vehicles else 0
        print(f"  {field}: {count} ({percentage:.1f}%)")
    
    # Sauvegarder
    print(f"\nSauvegarde dans {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_vehicles, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*60)
    print("NETTOYAGE TERMINÉ!")
    print("="*60)
    print(f"Fichier nettoyé: {output_file}")
    
    return cleaned_vehicles


if __name__ == "__main__":
    import sys
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else "vehicles_scraped.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "vehicles_scraped_clean.json"
    
    try:
        clean_json_data(input_file, output_file)
    except FileNotFoundError:
        print(f"ERREUR: Fichier {input_file} introuvable!")
        print("Exécutez d'abord: python graph/kg_ollama.py")
    except Exception as e:
        print(f"ERREUR: {e}")
        import traceback
        traceback.print_exc()
