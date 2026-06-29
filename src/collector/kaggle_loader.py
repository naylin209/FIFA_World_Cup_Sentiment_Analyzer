import pandas as pd
import os


def load_kaggle_data(filepath: str) -> pd.DataFrame:
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Dataset not found at '{filepath}'.\n"
            "Download it from Kaggle: search 'FIFA World Cup 2022 tweets sentiment' by Mr-Chang95\n"
            "and save the CSV to the data/ folder as kaggle_fifa_2022.csv"
        )

    df = pd.read_csv(filepath)
    print(f"Loaded {len(df)} rows")
    print(f"Columns: {df.columns.tolist()}")
    print("\nFirst 3 rows:")
    print(df.head(3))
    return df


if __name__ == "__main__":
    df = load_kaggle_data("data/kaggle_fifa_2022/kaggle_fifa_2022.csv")
    print(f"\nRow count: {len(df)}")
    print("Day 1 complete — data is loading correctly!")
