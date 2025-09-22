// this is a shortcut library which internally simplies using react.
// is responsible for managing the state - state refers to how a component remembers data which can change over time
import { useState } from "react";
// used for managing http requests
import axios from "axios";

function App() {
  // useState hook to store the uploaded resume file for the user, 
  // then the top 5 results + info
  // then all the matched keywords
  // then the top 10 recommended keywords
  const [file, setFile] = useState(null);
  const [results, setResults] = useState([]);
  const [matched, setMatched] = useState([]);
  const [suggested, setSuggested] = useState([]);
  // triggered when a user selects a file. It updates file to be the uploaded PDF.
  const handleFileChange = (e) => {
    // save the uploaded file to local state
    setFile(e.target.files[0]);
  };
  // triggered when the user clicks the "Match Resume" button
  const handleUpload = async () => {
    // error handler
    if (!file) return alert("Please upload a PDF resume.");
    // creates an object to send to the backend
    const formData = new FormData();
    // appends said file with the resume file that we have stored locally
    formData.append("resume", file);

    // post request to the backend
    try {
      // Use a relative path; React dev server will proxy to Flask if "proxy" is set in package.json
      const res = await axios.post("/match", formData);
      // if successful iteration, update the state with data returned from backend
      setResults(res.data.matches || []);
      setMatched(res.data.matched_keywords || []);
      setSuggested(res.data.suggested_keywords || []);
    } catch (err) {
      // log the error for debugging and notify the user
      console.error("Axios error:", err?.response?.data || err?.message || err);
      alert(
        (err.response && err.response.data && err.response.data.error) ||
          err.message ||
          "There was an error matching your resume."
      );
    }
  };

  return (
    // creates a <div> (a container) with inline styling to add 40px of padding. All the UI elements will be inside this box. 
    // 
    <div style={{ padding: 40 }}>
      {/* creates our header */}
      <h1>Resume Matcher</h1>
      {/* creates a file input for accepting pdfs, accept="application/pdf" ensures only PDFs are selectable
          onChange={handleFileChange} attaches the earlier-defined function that saves the uploaded file to state. */}
      <input type="file" accept="application/pdf" onChange={handleFileChange} />
      {/* creates a button called match resume that when clicked runs the handleUpload, running the file to the backend, gets the results, and updates the state */}
      <button onClick={handleUpload} style={{ marginLeft: 10 }}>
        Match Resume
      </button>
      {/* if the length of our results is greater than 0 then we run this code chunk, otherwise we skip */}
      {results.length > 0 && (
        // creates another box
        <div style={{ marginTop: 40 }}>
          {/* creates a header*/}
          <h2>Top Matches</h2> 
          <ul>
            {/* start of an unordered list to hold all job match items */}
            {/* iterate over the 'results' array using .map(), for each job object, render an li (list item) */}
            {results.map((job, i) => (
              // Each list item needs a unique 'key' prop for React's virtual DOM (document object model) tracking
              <li key={i}>
                {/* bold job title */}
                <strong>{job.title}</strong>
                {job.company_name ? <> at {job.company_name}</> : null}
                {job.location ? <> in {job.location}</> : null}
                <br />
                {/* Display the match score formatted to 3 decimal places */}
                Score: {Number(job.match_score ?? 0).toFixed(3)} <br />
                {/* Link to the original job posting and prevents leakage of refferer data */}
                {job.job_posting_url ? (
                  <a href={job.job_posting_url} target="_blank" rel="noreferrer">
                    View Posting
                  </a>
                ) : (
                  <em>No link available</em>
                )}
              </li>
            ))}
          </ul>
          {/* rendered only if there are results (inside the conditional block) */} 
          {/* this section displays both matched and suggested keywords */}
          {/* the p is a paragraph indicator and the ", " is for the spacing for each term*/}
          <h3>Matched Keywords</h3>
          <p>{matched.join(", ")}</p>
          <h3>Suggested Keywords</h3>
          <p>{suggested.join(", ")}</p>
        {/* close the result display block and the conditional render */}
        </div>
      )}
    {/* close the outermost container div for the component */}
    </div>
  );
}

export default App;
