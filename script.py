import pandas as pd
from pathlib import Path

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



