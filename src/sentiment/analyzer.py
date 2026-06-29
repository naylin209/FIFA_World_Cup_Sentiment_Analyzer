from transformers import pipeline

_sentiment_pipeline = None
_load_failed = False


def get_pipeline():
    global _sentiment_pipeline, _load_failed
    if _load_failed:
        return None
    if _sentiment_pipeline is None:
        try:
            print("Loading model (first time takes ~30 seconds, cached after)...")
            _sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-xlm-roberta-base-sentiment",
                max_length=512,
                truncation=True,
            )
            print("Model ready.")
        except Exception as exc:
            print(f"[analyzer] model load failed: {exc!r}")
            _load_failed = True
    return _sentiment_pipeline


def analyze_sentiment(text: str) -> dict:
    pipe = get_pipeline()
    if pipe is None:
        return {"sentiment": "neutral", "confidence": 0.0}
    try:
        result = pipe(str(text))[0]
        return {
            "sentiment": result["label"],
            "confidence": round(result["score"], 4),
        }
    except Exception as exc:
        print(f"[analyzer] scoring error: {exc!r} — text: {str(text)[:80]!r}")
        return {"sentiment": "neutral", "confidence": 0.0}


def analyze_dataframe(df, text_column: str):
    print(f"Scoring {len(df)} rows — grab a coffee, this takes a minute...")
    results = df[text_column].apply(lambda t: analyze_sentiment(str(t)))
    df = df.copy()
    df["predicted_sentiment"] = results.apply(lambda x: x["sentiment"])
    df["confidence"] = results.apply(lambda x: x["confidence"])
    return df


if __name__ == "__main__":
    samples = [
        "Argentina played absolutely brilliantly tonight!",
        "That referee was terrible, completely ruined the match",
        "Good game, both teams tried hard",
        "MESSI GOAT. What a goal!!!",
        "Disgusting performance, we deserved better",
    ]

    print("=== Sentiment Analysis Test ===\n")
    for text in samples:
        result = analyze_sentiment(text)
        print(f"Text:       {text}")
        print(f"Sentiment:  {result['sentiment']}  (confidence: {result['confidence']})")
        print()
