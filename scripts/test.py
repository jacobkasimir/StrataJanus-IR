cd /Users/jacob/Documents/StrataJanus-IR

for size in 10000 50000 100000; do
  echo "Checking $size..."
  time shasum -a 256 "data/processed/wikipedia-20231101-en/$size/documents.jsonl"
done