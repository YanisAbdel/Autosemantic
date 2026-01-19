import pandas as pd
from pathlib import Path
import re

# ---------- Prétraitement du CSV ----------
vehicles = "data/vehicles.csv"
vehicles_path = Path(vehicles)
csv_clean_file = str(vehicles_path.parent / f"{vehicles_path.stem}_clean{vehicles_path.suffix}")

reviews = "data/reviews_final.csv"
reviews_path = Path(reviews)
csv_clean_reviews = str(reviews_path.parent / f"{reviews_path.stem}_clean{reviews_path.suffix}")



TEST_MODE = True
TEST_FRACTION = 0.10  # 10 %
TEST_RANDOM_STATE = 42

# ---------- Mappings vers concepts SKOS ----------
DRIVE_TYPE_MAPPING = {
    'Front-Wheel Drive': 'FrontWheelDrive',
    'Rear-Wheel Drive': 'RearWheelDrive',
    '4-Wheel Drive': 'FourWheelDrive',
    'Part-time 4-Wheel Drive': 'PartTimeFourWheelDrive',
    'All-Wheel Drive': 'AllWheelDrive',
    '4-Wheel or All-Wheel Drive': 'FourWheelOrAllWheelDrive',
    '2-Wheel Drive': 'TwoWheelDrive',
}

VEHICLE_CLASS_MAPPING = {
    'Compact Cars': 'CompactCar',
    'Subcompact Cars': 'SubcompactCar',
    'Minicompact Cars': 'MinicompactCar',
    'Midsize Cars': 'MidsizeCar',
    'Large Cars': 'LargeCar',
    'Two Seaters': 'TwoSeater',
    'Small Station Wagons': 'SmallStationWagon',
    'Midsize Station Wagons': 'MidsizeStationWagon',
    'Midsize-Large Station Wagons': 'MidsizeLargeStationWagon',
    'Small Pickup Trucks': 'SmallPickupTruck',
    'Standard Pickup Trucks': 'StandardPickupTruck',
    'Pickup Trucks': 'PickupTruck',
    'Minivans': 'Minivan',
    'Minivan - 4WD': 'Minivan',
    'Minivan - 2WD': 'Minivan',
    'Passenger Vans': 'PassengerVan',
    'Cargo Vans': 'CargoVan',
    'Vans': 'VanClass',
    'Vans Passenger': 'PassengerVan',
    'Vans, Cargo Type': 'CargoVan',
    'Vans, Passenger Type': 'PassengerVan',
    'Small Sport Utility Vehicle 4WD': 'SmallSUV',
    'Small Sport Utility Vehicle 2WD': 'SmallSUV',
    'Standard Sport Utility Vehicle 4WD': 'StandardSUV',
    'Standard Sport Utility Vehicle 2WD': 'StandardSUV',
    'Sport Utility Vehicle - 4WD': 'SUVClass',
    'Sport Utility Vehicle - 2WD': 'SUVClass',
    'Special Purpose Vehicle 2WD': 'SpecialPurposeClass',
    'Special Purpose Vehicle 4WD': 'SpecialPurposeClass',
}

TRANSMISSION_MAPPING = {
    'Automatic 3-spd': 'Automatic',
    'Automatic 4-spd': 'Automatic',
    'Automatic 5-spd': 'Automatic',
    'Automatic 6-spd': 'Automatic',
    'Automatic 7-spd': 'Automatic',
    'Automatic 8-spd': 'Automatic',
    'Automatic 9-spd': 'Automatic',
    'Automatic 10-spd': 'Automatic',
    'Automatic (AV)': 'Automatic',
    'Automatic (AV-S6)': 'Automatic',
    'Automatic (AV-S8)': 'Automatic',
    'Manual 3-spd': 'Manual',
    'Manual 4-spd': 'Manual',
    'Manual 5-spd': 'Manual',
    'Manual 6-spd': 'Manual',
    'Manual 7-spd': 'Manual',
    'Automated Manual 5-spd': 'AutomatedManual',
    'Automated Manual 6-spd': 'AutomatedManual',
    'Automated Manual 7-spd': 'AutomatedManual',
}

FUEL_TYPE_MAPPING = {
    'Regular': 'Regular',
    'Premium': 'Premium',
    'Midgrade': 'Midgrade',
    'Diesel': 'Diesel',
    'Gasoline': 'Gasoline',
    'Electricity': 'Electricity',
    'CNG': 'CNG',
    'Premium Gas or Electricity': 'PremiumGasOrElectricity',
    'Regular Gas or Electricity': 'RegularGasOrElectricity',
    'Premium and Electricity': 'PremiumAndElectricity',
    'Regular Gas and Electricity': 'RegularGasAndElectricity',
    'Gasoline or E85': 'GasolineOrE85',
    'Premium or E85': 'PremiumOrE85',
    'Gasoline or natural gas': 'GasolineOrNaturalGas',
    'Gasoline or propane': 'GasolineOrPropane',
}

def clean_manufacturer_name(name):
    """Nettoie les noms de fabricants pour correspondre aux concepts SKOS"""
    special_mappings = {
        'Mercedes-Benz': 'MercedesBenz',
        'Alfa Romeo': 'AlfaRomeo',
        'Aston Martin': 'AstonMartin',
        'Land Rover': 'LandRover',
        'Rolls-Royce': 'RollsRoyce',
        'AM General': 'AMGeneral',
    }
    
    if name in special_mappings:
        return special_mappings[name]
    
    # Enlève espaces et caractères spéciaux
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', name)
    return cleaned



def clean_data(csv_path: str, expected_cols: list = None) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    
    # Vérifier la présence des colonnes requises avant de filtrer
    if expected_cols:
        missing_cols = [col for col in expected_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing columns: {', '.join(missing_cols)}")
        
        # Ne garder que les colonnes attendues
        df = df[expected_cols]
    
    #df = df.fillna("not indicated")
    df = df.dropna()
    
    # Appliquer les mappings vers concepts SKOS si c'est le fichier vehicles
    if 'drive' in df.columns:
        print("Application des mappings vers concepts SKOS...")
        
        # Drive type
        df['drive'] = df['drive'].map(DRIVE_TYPE_MAPPING)
        missing_drive = df['drive'].isna().sum()
        if missing_drive > 0:
            print(f"  {missing_drive} valeurs de 'drive' non mappées")
        
        # Vehicle class
        df['VClass'] = df['VClass'].map(VEHICLE_CLASS_MAPPING)
        missing_vclass = df['VClass'].isna().sum()
        if missing_vclass > 0:
            print(f" {missing_vclass} valeurs de 'VClass' non mappées")
        
        # Transmission
        original_trany = df['trany'].copy()
        df['trany'] = df['trany'].map(TRANSMISSION_MAPPING)
        df['trany'].fillna(original_trany, inplace=True)
        
        # Fuel type
        df['fuelType'] = df['fuelType'].map(FUEL_TYPE_MAPPING)
        missing_fuel = df['fuelType'].isna().sum()
        if missing_fuel > 0:
            print(f"  {missing_fuel} valeurs de 'fuelType' non mappées")
        
        # Manufacturer
        df['make'] = df['make'].apply(clean_manufacturer_name)
        
        # Supprimer les lignes avec des valeurs nulles après mapping
        df = df.dropna()
        print(f" Mappings appliqués avec succès")

        
    # Réduire à un échantillon aléatoire de 10 % si TEST_MODE est activé
    if TEST_MODE:
        df = df.sample(frac=TEST_FRACTION, random_state=TEST_RANDOM_STATE)
        print(f"Test mode actif : échantillon de {int(TEST_FRACTION * 100)} % conservé")

    # Générer le chemin du fichier nettoyé
    input_path = Path(csv_path)
    output_path = str(input_path.parent / f"{input_path.stem}_clean{input_path.suffix}")
    
    df.to_csv(output_path, index=False)
    print(f"Clean CSV saved to {output_path}")

    return df

if __name__ == "__main__":

    # Vehicles dataset
    expected_cols_vehicles = [
    "id",
    "year",
    "make",
    "model",
    "baseModel",
    "VClass",
    "drive",
    "trans_dscr",
    "cylinders",
    "fuelType",
    "co2",
    "trany",
    "displ",
    ]
    clean_data(vehicles, expected_cols_vehicles)

    
    # Reviews dataset

    expected_cols_reviews = [
    "Review",
    "Rating",
    "Brand",
    "Review_Year",
    "Review_Trans_Type",
    "Review_Engine_Disp",
    "Review_Model",
    ]
    clean_data(reviews, expected_cols_reviews)



