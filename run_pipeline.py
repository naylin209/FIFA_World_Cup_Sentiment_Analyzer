from src.collector.kaggle_loader import load_kaggle_data
from src.sentiment.analyzer import analyze_dataframe
from src.database.db import create_table, insert_batch

DATASET_PATH = "data/kaggle_fifa_2022/kaggle_fifa_2022.csv"
SAMPLE_SIZE = 500  # increase once everything works


def run():
    print("=== FIFA Sentiment Pipeline ===\n")

    print("Step 1: Loading data...")
    df = load_kaggle_data(DATASET_PATH)
    df = df.head(SAMPLE_SIZE)
    print(f"Using {len(df)} rows.\n")

    print("Step 2: Running sentiment analysis...")
    df = analyze_dataframe(df, text_column="Tweet")
    print(f"Sample results:")
    print(df[["Tweet", "predicted_sentiment", "confidence"]].head(3).to_string(index=False))
    print()

    print("Step 3: Saving to PostgreSQL...")
    create_table()
    rows = [
        {
            "comment_text": row["Tweet"],
            "sentiment": row["predicted_sentiment"],
            "confidence": row["confidence"],
            "match_title": "FIFA World Cup 2022",
            "source": "kaggle",
        }
        for _, row in df.iterrows()
    ]
    insert_batch(rows)
    print(f"Saved {len(rows)} rows to database.\n")

    print("=== Pipeline complete! ===")
    print("Run: psql -U postgres -d fifa_sentiment -c \"SELECT sentiment, COUNT(*) FROM match_sentiments GROUP BY sentiment;\"")


if __name__ == "__main__":
    run()
