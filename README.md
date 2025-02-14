# eCFR Search

eCFR Search is a web application designed to facilitate advanced searches within the Electronic Code of Federal Regulations (eCFR). 
The original intention was to have several dynamic pages and cool flashy dashboards, but for the sake of brevity, this was left out.

This application allows users to search for specific keywords, titles, and parts within the eCFR, providing detailed results and metadata.

## Features

- **Advanced Search**: Search by keyword, title, and part.
- **Metadata Display**: View total results, number of active and ended entries, and number of pages.
- **Tone Analysis**: Analyze the tone of the search results (strict, neutral, permissive).
- **Statistics**: Display statistics for titles and parts.
- **Result Details**: View detailed information about each search result, including start and end dates, subtitles, subject groups, and full text excerpts.
- **Version Comparison**: Compare different versions of a title and part to see the differences.

## How to Launch

1. **Clone the Repository**:
    ```sh
    git clone https://github.com/ryanheinrich/ecfr-search.git
    cd ecfr-search
    ```

2. **Install Dependencies**:
    Ensure you have Python and pip installed. Then, install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

3. **Run the Application**:
    Start the Flask application:
    ```sh
    python app.py
    ```

4. **Access the Application**:
    Open your web browser and navigate to `http://127.0.0.1:5000/` to access the eCFR Search application.

## What to Expect

- **Search Form**: Enter your search criteria in the provided form and submit to see the results.
- **Results**: View a list of search results with detailed information and metadata.
- **Tone Analysis**: See the tone analysis of the search results.
- **Statistics**: View statistics for titles and parts based on the search results.
- **Error Handling**: If there is an issue with the search, an error message will be displayed.