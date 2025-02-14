import ssl, nltk
ssl._create_default_https_context = ssl._create_unverified_context
nltk.download('vader_lexicon')