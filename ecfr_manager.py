import requests
import sqlite3
import json
from datetime import datetime
import time
import logging
import os

class ECFRManager:
    def __init__(self, db_path="ecfr.db"):
        self.db_path = db_path
        self.base_url = "https://www.ecfr.gov/api/search/v1"
        
        # Set up logging first
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize database and create session
        self.init_db()
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "eCFR-Downloader/1.0"
        })

    def init_db(self):
        """Initialize SQLite database with required tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS regulations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    part TEXT,
                    section TEXT,
                    full_text TEXT,
                    starts_on DATE,
                    ends_on DATE,
                    hierarchy TEXT,
                    hierarchy_headings TEXT,
                    headings TEXT,
                    last_updated TIMESTAMP
                )
            ''')
            
            # Create indices for better search performance
            c.execute('CREATE INDEX IF NOT EXISTS idx_full_text ON regulations(full_text)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_title ON regulations(title)')
            
            conn.commit()
            conn.close()
            self.logger.info(f"Database initialized at {self.db_path}")
            
        except sqlite3.Error as e:
            self.logger.error(f"Database initialization error: {str(e)}")
            raise

    def _make_request(self, endpoint, params=None):
        """Make API request with error handling"""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error making request to {url}: {str(e)}")
            return None

    def download_ecfr(self):
        """Download complete eCFR data"""
        self.logger.info("Starting eCFR download...")
        
        params = {
            "query": "*",  # Search for everything
            "per_page": 100,
            "page": 1
        }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()  # Changed variable name from c to cursor
        
        try:
            # Get first page to determine total pages
            response = self._make_request("results", params)
            if not response:
                return False
            
            total_pages = response["meta"]["total_pages"]
            processed_count = 0
            
            while params["page"] <= total_pages:
                self.logger.info(f"Processing page {params['page']} of {total_pages}")
                
                if params["page"] > 1:
                    response = self._make_request("results", params)
                    if not response:
                        continue
                
                for result in response.get("results", []):
                    try:
                        self._process_content(cursor, result)  # Pass cursor to _process_content
                        processed_count += 1
                        if processed_count % 100 == 0:
                            conn.commit()
                            self.logger.info(f"Processed {processed_count} records")
                    
                    except sqlite3.Error as e:
                        self.logger.error(f"Error processing record: {str(e)}")
                        continue
                
                params["page"] += 1
                time.sleep(1)  # Rate limiting
            
            conn.commit()
            self.logger.info(f"Download complete! Processed {processed_count} records")
            return True
            
        except Exception as e:
            self.logger.error(f"Download failed: {str(e)}")
            return False
            
        finally:
            conn.close()

    def _create_session(self):
        """Create a requests session with retry logic and proper headers"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,  # number of retries
            backoff_factor=1,  # wait 1, 2, 4 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        # Mount the adapter with retry strategy
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            "Accept": "application/json",
            "User-Agent": "eCFR-Downloader/1.0"
        })
        
        return session

    def _process_content(self, cursor, content):
        """Process and store content in database"""
        now = datetime.now()
        
        cursor.execute('''
            INSERT OR REPLACE INTO regulations 
            (title, part, section, full_text, starts_on, ends_on, 
             hierarchy, hierarchy_headings, headings, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            content.get('title'),
            content.get('part'),
            content.get('section'),
            content.get('full_text_excerpt'),  # Changed from full_text to full_text_excerpt
            content.get('starts_on'),
            content.get('ends_on'),
            json.dumps(content.get('hierarchy', {})),
            json.dumps(content.get('hierarchy_headings', {})),
            json.dumps(content.get('headings', {})),
            now
        ))

    def search(self, query, page=1, per_page=20):
        """Search local database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Full-text search query
        search_query = f'''
            SELECT * FROM regulations 
            WHERE full_text LIKE ?
            LIMIT ? OFFSET ?
        '''
        
        c.execute(search_query, (f'%{query}%', per_page, (page-1)*per_page))
        results = [dict(row) for row in c.fetchall()]
        
        # Get total count
        c.execute('SELECT COUNT(*) FROM regulations WHERE full_text LIKE ?', (f'%{query}%',))
        total_count = c.fetchone()[0]
        
        conn.close()
        
        return {
            'results': results,
            'meta': {
                'current_page': page,
                'total_pages': (total_count + per_page - 1) // per_page,
                'total_count': total_count
            }
        }