import ssl, nltk, os
from flask import Flask, render_template, request, jsonify
import requests, difflib
from nltk.sentiment import SentimentIntensityAnalyzer
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

# Index route
@app.route('/')
def index():
    return render_template('index.html')  # Serve the frontend HTML

@app.route('/search', methods=['GET'])
def search_ecfr():
    query = request.args.get('query', '').strip()
    per_page = request.args.get('per_page', '20')
    page = request.args.get('page', '1')
    order = request.args.get('order', 'relevance')
    paginate_by = request.args.get('paginate_by', 'results')

    if not query:
        return render_template('index.html', error="Please enter a search term.")

    # Construct API request parameters
    params = {
        "query": query,
        "per_page": per_page,
        "page": page,
        "order": order,
        "paginate_by": paginate_by
    }

    headers = {"accept": "application/json"}

    # Log the API request details
    print(f"\neCFR API Request:")
    print(f"URL: {ECFR_SEARCH_API}")
    print(f"Parameters: {params}")
    print(f"Headers: {headers}\n")

    # Send request to eCFR API
    response = requests.get(ECFR_SEARCH_API, params=params, headers=headers)

    if response.status_code != 200:
        return render_template('index.html', error=f"Failed to retrieve data, status {response.status_code}")

    data = response.json()
    
    # Save response to debug file
    debug_file = "ecfr_response_debug.json"
    with open(debug_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Response saved to {debug_file}")

    results = data.get("results", [])

    # Calculate statistics
    title_stats = {}
    part_stats = {}

    for result in results:
        title = result.get("hierarchy", {}).get("title", "Unknown")
        part = result.get("hierarchy", {}).get("part", "Unknown")

        if title not in title_stats:
            title_stats[title] = 0
        title_stats[title] += 1

        if part not in part_stats:
            part_stats[part] = 0
        part_stats[part] += 1

    # Filter unique results
    unique_results = {}
    for result in results:
        section = result.get("hierarchy", {}).get("section", "Unknown")
        excerpt = result.get("full_text_excerpt", "").strip()
        key = (section, excerpt)

        if key not in unique_results:
            unique_results[key] = result

    filtered_results = list(unique_results.values())

    # Sort results so that ended ones appear at the top
    filtered_results.sort(key=lambda x: x.get('ends_on') is None)

    # Tone analysis
    tone_counts = {"strict": 0, "neutral": 0, "permissive": 0}
    active_count = 0
    ended_count = 0
    for result in filtered_results:
        text = result.get("full_text_excerpt", "")
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

        if result.get('ends_on'):
            ended_count += 1
        else:
            active_count += 1

    # Metadata
    metadata = {
        "total_results": len(filtered_results),
        "active_count": active_count,
        "ended_count": ended_count,
        "num_pages": data.get("total_pages", 0),
        "current_page": page,
    }

    return render_template("index.html", results=filtered_results, metadata=metadata, tone_analysis=tone_counts, title_stats=title_stats, part_stats=part_stats)
        
@app.route('/diff', methods=['GET'])
def compare_versions():
    title = request.args.get('title')
    part = request.args.get('part')
    version1 = request.args.get('version1')
    version2 = request.args.get('version2')

    if not title or not part or not version1 or not version2:
        return jsonify({"error": "Provide title, part, and two versions"}), 400

    url1 = f"{ECFR_API_BASE}/titles/{title}/parts/{part}?version={version1}"
    url2 = f"{ECFR_API_BASE}/titles/{title}/parts/{part}?version={version2}"

    response1 = requests.get(url1).json()
    response2 = requests.get(url2).json()

    text1 = response1.get("text", "")
    text2 = response2.get("text", "")

    diff = list(difflib.unified_diff(text1.splitlines(), text2.splitlines(), lineterm=''))
    
    return jsonify({"diff": "\n".join(diff)})

if __name__ == '__main__':
    app.run(debug=True)