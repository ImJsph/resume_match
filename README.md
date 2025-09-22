# Resume_Matcher
An app aimed at matching resumes with job descriptions. This is the first iteration/rough draft

diagram of the pipeline:
+--------------------+
|   User Interface   |
+--------------------+
        |
        v
[ Upload Resume PDF ]
        |
        v
   handleFileChange()
   -----------------
   - Saves file to React state
        |
        v
[ Click "Match Resume" ]
        |
        v
   handleUpload()
   -----------------
   - Packages file into FormData
   - Sends POST request -> Flask backend (/match)
        |
        v
+------------------------+
|   Flask Backend API    |
+------------------------+
   - Extracts resume text
   - Normalizes text
   - Encodes resume with BERT
   - Compares with job embeddings
   - Returns JSON:
       { matches, matched_keywords, suggested_keywords }
        |
        v
+--------------------+
|  React Frontend    |
+--------------------+
   res.data ->
   - setResults(res.data.matches)
   - setMatched(res.data.matched_keywords)
   - setSuggested(res.data.suggested_keywords)
        |
        v
[ Conditional Rendering ]
--------------------------
If results.length > 0:
   - Show Top Matches (job title, company, location, score, link)
   - Show Matched Keywords
   - Show Suggested Keywords
Else:
   - Show nothing
