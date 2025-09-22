// this is a shortcut library which internally simplies using react.
// is responsible for managing the state - state refers to how a component remembers data which can change over time
import { useState } from "react";
// used for managing http requests
import axios from "axios";

function App() {
  // useState hook to store the uploaded resume file for the user
  const [file, setFile] = useState(null);
  // then the top 5 results + info (dataset mode)
  const [results, setResults] = useState([]);
  // then all the matched keywords (dataset mode)
  const [matched, setMatched] = useState([]);
  // then the top 10 recommended keywords (dataset mode)
  const [suggested, setSuggested] = useState([]);

  // ================= CUSTOM JOB DESCRIPTION STATE =================
  // state for storing the raw text of a custom job description typed/pasted by the user
  const [jobDescription, setJobDescription] = useState("");
  // state for storing the backend response when comparing resume ↔ custom job description
  const [customResult, setCustomResult] = useState(null);

  // triggered when a user selects a file. It updates file to be the uploaded PDF.
  const handleFileChange = (e) => {
    // save the uploaded file to local state
    setFile(e.target.files[0]);
  };

  // triggered when the user clicks the "Match Resume" button for Kaggle dataset
  const handleUpload = async () => {
    // error handler if no file is uploaded
    if (!file) return alert("Please upload a PDF resume.");
    // creates an object to send to the backend
    const formData = new FormData();
    // appends said file with the resume file that we have stored locally
    formData.append("resume", file);

    // post request to the backend (/match) for dataset-based matching
    try {
      const res = await axios.post("http://localhost:5001/match", formData);
      // if successful, update state with dataset results
      setResults(res.data.matches);
      setMatched(res.data.matched_keywords);
      setSuggested(res.data.suggested_keywords);
    } catch (err) {
      // log the error for debugging and notify the user
      console.error(err);
      alert("There was an error matching your resume.");
    }
  };

  // ================= CUSTOM JOB DESCRIPTION FUNCTION =================
  // triggered when the user clicks the "Match with Custom Job" button
  const handleCustomUpload = async () => {
    // error handler if no resume is uploaded
    if (!file) return alert("Please upload a PDF resume.");
    // error handler if no job description text is pasted
    if (!jobDescription.trim()) return alert("Please paste a job description.");

    // creates form data with both resume and custom job description
    const formData = new FormData();
    formData.append("resume", file);
    formData.append("job_description", jobDescription);

    // post request to backend (/match_custom) for custom job matching
    try {
      const res = await axios.post("http://localhost:5001/match_custom", formData);
      // save backend response (match score + keywords) into state
      setCustomResult(res.data);
    } catch (err) {
      console.error(err);
      alert("There was an error matching your resume to the custom job description.");
    }
  };

  return (
    // creates a <div> (a container) with inline styling to add 40px of padding. 
    // This is the main wrapper for all UI elements in the component.
    <div style={{ padding: 40 }}>
      {/* creates our header */}
      <h1>Resume Matcher</h1>

      {/* creates a file input for accepting pdfs, accept="application/pdf" ensures only PDFs are selectable
          onChange={handleFileChange} attaches the earlier-defined function that saves the uploaded file to state. */}
      <input type="file" accept="application/pdf" onChange={handleFileChange} />

      {/* creates a button called Match Resume (Dataset) that when clicked runs the handleUpload,
          sending the resume to the backend, getting the results, and updating the state */}
      <button onClick={handleUpload} style={{ marginLeft: 10 }}>
        Match Resume (Dataset)
      </button>

      {/* ================= DATASET MATCH RESULTS ================= */}
      {/* if the length of our results is greater than 0 then we run this code chunk, otherwise we skip */}
      {results.length > 0 && (
        // creates another box for dataset results
        <div style={{ marginTop: 40 }}>
          {/* creates a header */}
          <h2>Top Matches (Dataset)</h2> 
          <ul>
            {/* start of an unordered list to hold all job match items */}
            {/* iterate over the 'results' array using .map(), for each job object, render an li (list item) */}
            {results.map((job, i) => (
              // Each list item needs a unique 'key' prop for React's virtual DOM (document object model) tracking
              <li key={i}>
                {/* bold job title */}
                <strong>{job.title}</strong>
                {/* only show company_name if present */}
                {job.company_name ? <> at {job.company_name}</> : null}
                {/* only show location if present */}
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
          {/* this section displays both matched and suggested keywords from dataset results */}
          <h3>Matched Keywords</h3>
          <p>{matched.join(", ")}</p>
          <h3>Suggested Keywords</h3>
          <p>{suggested.join(", ")}</p>
        </div>
      )}

      {/* Custom Job Description Frontend */}
      <div style={{ marginTop: 40 }}>
        {/* header for the custom job description feature */}
        <h2>Custom Job Description Match</h2>

        {/* textarea for the user to paste a job description (multi-line input) */}
        <textarea
          placeholder="Paste job description here..."
          value={jobDescription}
          onChange={(e) => setJobDescription(e.target.value)}
          rows={6}
          cols={60}
          style={{ display: "block", marginBottom: 10 }}
        />

        {/* button that triggers handleCustomUpload, sending both resume + job description to backend */}
        <button onClick={handleCustomUpload}>Match with Custom Job</button>

        {/* only render the results if customResult has been set */}
        {customResult && (
          <div style={{ marginTop: 20 }}>
            <h3>Custom Job Match</h3>
            {/* display the similarity score */}
            <p><strong>Match Score:</strong> {customResult.match_score.toFixed(3)}</p>
            {/* display matched keywords (common between resume and custom JD) */}
            <h4>Matched Keywords</h4>
            <p>{customResult.matched_keywords.join(", ")}</p>
            {/* display suggested keywords (present in JD but missing from resume) */}
            <h4>Suggested Keywords</h4>
            <p>{customResult.suggested_keywords.join(", ")}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
