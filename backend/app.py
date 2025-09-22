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
# cosine similarity works in tandem with the vectorizer/embeddings by comparing 2 vectors and seeing what the match is like there. 
from sklearn.metrics.pairwise import cosine_similarity
# os is for the operating system manuevering
import os
# sentence-transformers is a Hugging Face library that lets us use BERT-like models to generate embeddings for text
from sentence_transformers import SentenceTransformer


### APP INITILIZATION + CORS ###

# if we have the Flask(__name__) which initializes the web application. And when we use the built in variable __name__, we allow the app to know where the root path 
# is when running the app, allowing it to correctly have the required resources such as static files. We then call this instance the variable app 
app = Flask(__name__)
# cors allows our flask web app initialization to properly communicate with requests that are based on different origins. adds a cors: Access-Control-Allow-Origin: *
CORS(app)


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

try:
    # grabs our dataframe that has already been cleaned
   csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "postings_clean_shortened.csv"))
   # read in the csv, __file__: refers to the current Python file. os.path.dirname(__file__): gives the directory where this file lives. os.path.join(...): 
   # safely joins that directory with the CSV filename.
   postings = pd.read_csv(csv_path)

    # identifies the columns of the "object" data type which is strings in pandas
   str_cols = postings.select_dtypes(include="object").columns
   # gets these string columns and then fills in the empty entries (na) with blank spaces
   postings[str_cols] = postings[str_cols].fillna("")
   # creates a new column that is a single line that concatenates the desirable columns
   postings["job_text"] = (
       postings["title"] + " " +
       postings["description"] + " " +
       postings["skills_desc"] + " " +
       postings["skill_name"] + " " +
       postings["industry_name"]
   )
   # normalizes the text through our previously established function
   postings["job_text"] = postings["job_text"].apply(normalize_text).astype(str)

    # ==========================
    # BERT MODEL FOR EMBEDDINGS
    # ==========================
    # Load a pre-trained sentence-transformers model (small, fast, semantically powerful)
   bert_model = SentenceTransformer("all-MiniLM-L6-v2")

    # applies the model to create embeddings for all job postings (done once at startup)
   job_embeddings = bert_model.encode(postings["job_text"].tolist(), convert_to_numpy=True)

    # sanity check to make sure that the creation of the job description lines and the embeddings was successful
   print("✅ Job postings loaded and BERT embeddings computed:", postings.shape)

# handles our errors gracefully in the previous chunk of "try"
# the first line handles that scenario
except Exception as e:
    # creates a string message to output
   print("❌ Failed to load job postings:", str(e))
   # sets back the postings and job_embeddings to None or empty values so that they do not cause errors or crash when running again
   postings = pd.DataFrame()
   job_embeddings = None
   bert_model = None


### MATCHING ROUTES ###

# registers a route with Flask that listens for POST requests at /match
# this is typically used to handle file uploads or data sent from the frontend to the backend
@app.route("/match", methods=["POST"])
def match_resume():
   try:
        # gets the uploaded resume file from the POST request
       file = request.files["resume"]
       # saves the uploaded file locally
       file.save("uploaded_resume.pdf")
       # sanity check that the file was received
       print("✅ File received:", file.filename)

        # extracts text from the saved PDF resume with our previous function
       resume_text = extract_resume_text("uploaded_resume.pdf")
       # prints out the length of our resume text length
       print("📄 Resume text length:", len(resume_text))

        # normalizes our resume text
       resume_text = normalize_text(resume_text)
       # ensures the data type that turns the text into string
       resume_text = str(resume_text)

        # ==========================
        # BERT EMBEDDING + SIMILARITY
        # ==========================
        # applies the BERT model to encode the resume text
       resume_embedding = bert_model.encode([resume_text], convert_to_numpy=True)
       # computes the cosine similarity scores between the resume and all the job descriptions and flattens into a 1D vector
       scores = cosine_similarity(resume_embedding, job_embeddings).flatten()
       # creates a new column that grabs the scores for each job description
       postings["match_score"] = scores

        # we get the top matches by score
       top_matches = postings.sort_values(by="match_score", ascending=False).head(5)

        # tokenizes the resume into a unique set of words
       resume_words = set(re.findall(r'\b\w+\b', resume_text))
       # initialize sets for matched keywords and recommended keywords
       matched_keywords = set()
       suggested_keywords = set()

        # iterates through the top 5 job descriptions
       for _, row in top_matches.iterrows():
           # creates a new job_text through concatenation
           job_text = " ".join([
               str(row.get("title", "")),
               str(row.get("skills_desc", "")),
               str(row.get("skill_name", ""))
           ]).lower()
           # tokenizes job_text into words 
           job_words = set(re.findall(r'\b\w+\b', job_text))
           matched_keywords.update(resume_words & job_words)
           suggested_keywords.update(job_words - resume_words)

        # sanity check 
       print("✅ Matching complete.")

        # returns the jsonified response for the top 5 job descriptions, all matched keywords, and the top 10 suggested keywords
       return jsonify({
           "matches": top_matches[["title", "company_name", "location", "job_posting_url", "match_score"]].to_dict(orient="records"),
           "matched_keywords": sorted(matched_keywords)[:10],
           "suggested_keywords": sorted(suggested_keywords)[:10]
       })

   except Exception as e:
       print("❌ Error in /match:", str(e))
       return jsonify({"error": str(e)}), 500


# ==========================
# CUSTOM JOB DESCRIPTION MATCH
# ==========================
# this route allows the user to paste their own job description text instead of relying on the Kaggle dataset
@app.route("/match_custom", methods=["POST"])
def match_custom():
    try:
        # get resume from uploaded file
        file = request.files["resume"]
        file.save("uploaded_resume.pdf")
        resume_text = extract_resume_text("uploaded_resume.pdf")
        resume_text = normalize_text(resume_text)

        # get custom job description text from the request (sent as form-data)
        job_text = request.form.get("job_description", "")
        job_text = normalize_text(job_text)

        if not resume_text or not job_text:
            return jsonify({"error": "Missing resume or job description"}), 400

        # encode both resume and job description with BERT
        resume_embedding = bert_model.encode([resume_text], convert_to_numpy=True)
        job_embedding = bert_model.encode([job_text], convert_to_numpy=True)

        # compute similarity score
        score = float(cosine_similarity(resume_embedding, job_embedding)[0][0])

        # extract matched and suggested keywords
        resume_words = set(re.findall(r'\b\w+\b', resume_text))
        job_words = set(re.findall(r'\b\w+\b', job_text))
        matched_keywords = sorted(resume_words & job_words)
        suggested_keywords = sorted(job_words - resume_words)

        print("✅ Custom job description matching complete.")

        return jsonify({
            "job_description": job_text,
            "match_score": score,
            "matched_keywords": matched_keywords[:10],
            "suggested_keywords": suggested_keywords[:10]
        })

    except Exception as e:
        print("❌ Error in /match_custom:", str(e))
        return jsonify({"error": str(e)}), 500


# starts running the flask app if this file is run directly
if __name__ == "__main__":
   app.run(debug=True, host="0.0.0.0", port=5001)
