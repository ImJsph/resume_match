# flask is for the frontend web application with request handling the http information and jsonify for returning a good format of the data 
from flask import Flask, request, jsonify
# cors allows for a communication between separate ports since we are using the python and react for this app. A bridge of sorts
from flask_cors import CORS
# pandas for data frame manipulation 
import pandas as pd
# fitz is a library that is able to extract text from pdfs. It takes the text from the user's resume
import fitz  # PyMuPDF
# re handles the regex part of filtering for the words that we want to either highlight or ignore
import re
# tfidf vectorization is for words and in this case, it would create a vector for a given strings, finding unique words and putting a weight on it based on the frequency
from sklearn.feature_extraction.text import TfidfVectorizer
#cosine similarity works in tandem with the vectorizer by comparing 2 vectors and seeing what the match is like there. 
from sklearn.metrics.pairwise import cosine_similarity
# os is for the operating system manuevering
import os


### APP INITILIZATION + CORS ###

# if we have the Flask(__name__) which initializes the web application. And when we use the built in variable __name__, we allow the app to know where the root path 
# is when running the app, allowing it to correctly have the required resources such as static files. We then call this instance the variable app 
app = Flask(__name__)
# cors allows our flask web app initialization to properly communicate with requests that are based on different origins. adds a cors: Access-Control-Allow-Origin: *
# DEV: allow all origins to avoid localhost vs LAN IP mismatch issues
CORS(app)

# Optional: cap upload size (protect against giant PDFs)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

# Tiny request logger so you can see if the POST actually arrives
@app.after_request
def add_logs(resp):
    try:
        print(f"{request.method} {request.path} -> {resp.status_code}")
    except Exception:
        pass
    return resp


### TEXT TOOLS ###

# The function normalize text is used to first identify when the input is a string, otherwise removing those different data types. Then the text is normalized by
# making each word a lowercase with text.lower. re.sub(r"\W+", " ", text) is \W = anything that is NOT a letter, digit, or underscore (i.e., punctuation, symbols, etc.)
# + = match one or more of those in a row and then it replaces them with a spacebar and this text parameter is just clarifying where to apply said change. text.strip removes
# any trailing or leading whitespaces. 
def normalize_text(text):
   if not isinstance(text, str):
       return ""
   text = text.lower()
   text = re.sub(r"\W+", " ", text)
   return text.strip()

# This function aims to extract the text from the uploaded resume by using the fitz/pymupdf library. It first gets the path to the file, opens it, iterates through each page
# to extract text, and then connects the pages of the document together with a space in between 
def extract_resume_text(pdf_path):
   doc = fitz.open(pdf_path)
   return " ".join([page.get_text() for page in doc])


### LOADING DATA ###

# We’ll build an absolute path that works if your CSV is kept in the repo root (one folder up from backend).
# If you move the CSV into backend/, change the join below to just os.path.join(os.path.dirname(__file__), "postings_clean_shortened.csv")
postings = pd.DataFrame()
job_vectors = None
vectorizer = None

try:
   # grabs our dataframe that has alrady been cleaned
   csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "postings_clean_shortened.csv"))
   # read in the csv, __file__: refers to the current Python file. os.path.dirname(__file__): gives the directory where this file lives. os.path.join(...): 
   # safely joins that directory with the CSV filename.
   postings = pd.read_csv(csv_path)

   # identifies the columns of the "object" data type which is strings in pandas
   str_cols = postings.select_dtypes(include="object").columns
   # gets these string columns and then fills in the empty entries (na) with blank spaces
   postings[str_cols] = postings[str_cols].fillna("")

   # creates a new column that is a single line that concatenates the desirable columns
   # (defensive: only use columns that actually exist in your CSV)
   base_cols = ["title", "description", "skills_desc", "skill_name", "industry_name"]
   use_cols = [c for c in base_cols if c in postings.columns]
   if not use_cols:
       raise ValueError("No usable text columns found for job_text. Check your CSV column names.")

   postings["job_text"] = postings[use_cols].astype(str).agg(" ".join, axis=1)
   # normalizes the text through our previously established function
   postings["job_text"] = postings["job_text"].apply(normalize_text).astype(str)

   # the vectorizer function from tfidf uses the stop words to filter the english stop words that have no values in our scenario 
   # and then the max features = 10000 means that we are limiting to the top 10000 most frequent and important words across all of the documents
   vectorizer = TfidfVectorizer(stop_words="english", max_features=10000)
   # applies the vectorizer to the postings["job_text"] column
   job_vectors = vectorizer.fit_transform(postings["job_text"])

   # sanity check to make sure that the creation of the job description lines and the vectorization was successful
   print("✅ Job postings loaded and vectorized:", postings.shape)

# handles our errors gracefully in the previous chunk of "try"
# the first line handles that scenario
except Exception as e:
   # creates a string message to output
   print("❌ Failed to load job postings:", str(e))
   # sets back the postings and job_vectors to None or empty values so that they do not cause errors or crash when running again
   postings = pd.DataFrame()
   job_vectors = None
   vectorizer = None


### HEALTH / DEBUG ROUTES ###

# Lightweight health route so you can check readiness from the browser
@app.get("/health")
def health():
   ok_vec = job_vectors is not None and getattr(job_vectors, "shape", (0, 0))[0] > 0
   return jsonify({
       "status": "ok",
       "csv_loaded": not postings.empty,
       "n_rows": int(postings.shape[0]) if not postings.empty else 0,
       "n_cols": int(postings.shape[1]) if not postings.empty else 0,
       "vectorized": bool(ok_vec)
   })

# Simple route to see actual CSV columns (useful if names differ from expectations)
@app.get("/columns")
def columns():
   return jsonify({"columns": list(postings.columns)})


### MATCHING ROUTE ###

# registers a route with Flask that listens for POST requests at /match
# this is typically used to handle file uploads or data sent from the frontend to the backend
@app.route("/match", methods=["POST"])

# this
def match_resume():
   try:
       # early guards provide clearer, user-friendly errors
       if postings.empty or job_vectors is None or vectorizer is None:
           return jsonify({"error": "Jobs index not ready. Check /health and the CSV path/columns."}), 500

        # gets the uploaded resume file from the POST request
       if "resume" not in request.files:
           return jsonify({"error": "No file uploaded. Field name must be 'resume'."}), 400

       file = request.files["resume"]
       # saves the uploaded file locally
       file.save("uploaded_resume.pdf")
       # sanity check that the file was received
       print("✅ File received:", file.filename)

        # extracts text from the saved PDF resume with our previous function
       resume_text = extract_resume_text("uploaded_resume.pdf")
       # prints out the length of our resume text length
       print("📄 Resume text length:", len(resume_text))

       if not resume_text.strip():
           return jsonify({"error": "Could not extract text from PDF. Try a different resume file."}), 400

        # normalizes our resume text
       resume_text = normalize_text(resume_text)
       # ensures the data type that turns the text into string
       resume_text = str(resume_text)

        # applies the vectorizer transformation
       resume_vector = vectorizer.transform([resume_text])
       # computes the cosine similarity scores between the resume and all the job descriptions and flattens into a 1D vector
       scores = cosine_similarity(resume_vector, job_vectors).flatten()
       #creates a new column that grabs the scores for each job description
       postings["match_score"] = scores

        # we get the top matches by score
       top_matches = postings.sort_values(by="match_score", ascending=False).head(5)

        # tokenizes the resume into a unique set of words
       resume_words = set(re.findall(r'\b\w+\b', resume_text))
       # initialize sets for matched keywords and recommended keywords
       matched_keywords = set()
       suggested_keywords = set()

        # itereates through the top 5 job descriptions
       for _, row in top_matches.iterrows():
           # creates a new job_text through concatenation
           job_text = " ".join([
               str(row.get("title", "")),
               str(row.get("skills_desc", "")),
               str(row.get("skill_name", ""))
           ]).lower()
           # tokenizes job_text into words 
           # r denotes a raw string, b is for the word anchor boundary so that whole words are matched, \w is for all word characters
           # and the + is for the one or more character groups 
           job_words = set(re.findall(r'\b\w+\b', job_text))
           # finds common keywords between the resume and the job with the "&" being used for a set intersection allowing us to find the sets
           matched_keywords.update(resume_words & job_words)
           suggested_keywords.update(job_words - resume_words)

        # sanity check 
       print("✅ Matching complete.")

       # be defensive: only return columns that exist in your CSV
       ret_cols = [c for c in ["title", "company_name", "location", "job_posting_url", "match_score"] if c in top_matches.columns]

        # returns the jsonified response for the top 5 job descriptions, all matched keywords, and the top 10 suggested keywords
       # (small quality tweak: trim suggestions to those not already matched and prefer longer terms first)
       clean_suggestions = sorted((suggested_keywords - matched_keywords), key=len, reverse=True)[:15]

       return jsonify({
           "matches": top_matches[ret_cols].to_dict(orient="records"),
           "matched_keywords": sorted(matched_keywords),
           "suggested_keywords": clean_suggestions
       })

    # error handler matches a server side error and will return the error that we are dealing with in terms of the code chunk before
   except Exception as e:
       print("❌ Error in /match:", str(e))
       return jsonify({"error": str(e)}), 500

# starts running the flask app if this file is run directly
if __name__ == "__main__":
   # explicitly bind for clarity in dev; 0.0.0.0 lets localhost and LAN both work
   app.run(debug=True, host="0.0.0.0", port=5001)
