import ssl
import nltk
import os
from flask import Flask, render_template, request, jsonify
from nltk.sentiment import SentimentIntensityAnalyzer
from ecfr_manager import ECFRManager
import json

ssl._create_default_https_context = ssl._create_unverified_context
# Ensure nltk_data directory exists
nltk_data_path = os.path.join(os.getcwd(), "nltk_data")
os.makedirs(nltk_data_path, exist_ok=True)

# Set nltk data path
nltk.data.path.append(nltk_data_path)

# Try downloading vader_lexicon if missing
try:
    nltk.data.find('sentiment/vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon', download_dir=nltk_data_path)

sia = SentimentIntensityAnalyzer()

app = Flask(__name__, static_folder='static')

ECFR_SEARCH_API = "https://www.ecfr.gov/api/search/v1/results"

app = Flask(__name__, static_folder='static')
ecfr = ECFRManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search_ecfr():
    query = request.args.get('query', '').strip()
    page = int(request.args.get('page', '1'))
    per_page = int(request.args.get('per_page', '20'))

    if not query:
        return render_template('index.html', error="Please enter a search term.")

    # Search local database
    data = ecfr.search(query, page=page, per_page=per_page)
    results = data['results']

    # Calculate statistics
    title_stats = {}
    part_stats = {}
    active_count = 0
    ended_count = 0

    for result in results:
        # Parse JSON strings back to dictionaries
        result['hierarchy'] = json.loads(result['hierarchy'])
        result['hierarchy_headings'] = json.loads(result['hierarchy_headings'])
        result['headings'] = json.loads(result['headings'])

        title = result['title']
        part = result['part']
        
        if title not in title_stats:
            title_stats[title] = 0
        title_stats[title] += 1
        
        if part not in part_stats:
            part_stats[part] = 0
        part_stats[part] += 1

        if result['ends_on']:
            ended_count += 1
        else:
            active_count += 1

    # Tone analysis
    tone_counts = {"strict": 0, "neutral": 0, "permissive": 0}
    for result in results:
        text = result.get("full_text", "")
        score = sia.polarity_scores(text)["compound"]
        if score < -0.2:
            result["tone"] = "STRICT"
            tone_counts["strict"] += 1
        elif score > 0.2:
            result["tone"] = "PERMISSIVE"
            tone_counts["permissive"] += 1
        else:
            result["tone"] = "NEUTRAL"
            tone_counts["neutral"] += 1

    metadata = {
        "total_results": len(results),
        "active_count": active_count,
        "ended_count": ended_count,
        "num_pages": data['meta']['total_pages'],
        "current_page": page,
    }

    return render_template(
        "index.html",
        results=results,
        metadata=metadata,
        tone_analysis=tone_counts,
        title_stats=title_stats,
        part_stats=part_stats
    )

if __name__ == '__main__':
    # Download data if database doesn't exist
    if not os.path.exists('ecfr.db'):
        print("Downloading eCFR data... This may take a while...")
        ecfr.download_ecfr()
    app.run(debug=True)