import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AceEditor from "react-ace";
import ResultDisplay from '../components/ResultDisplay'; // Import the new component

import "ace-builds/src-noconflict/mode-python";
import "ace-builds/src-noconflict/mode-sql";
import "ace-builds/src-noconflict/theme-github";

function ProjectPage() {
    // ... (all the state and functions from the previous step remain the same)
    const { projectId } = useParams();
    const { token } = useAuth();
    const [project, setProject] = useState(null);
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(true);

    const [fileToUpload, setFileToUpload] = useState(null);
    const [datasetDescription, setDatasetDescription] = useState('');
    const [uploadError, setUploadError] = useState('');

    const [question, setQuestion] = useState('');
    const [language, setLanguage] = useState('python');
    const [queryResult, setQueryResult] = useState(null);
    const [isQueryLoading, setIsQueryLoading] = useState(false);
    const [queryError, setQueryError] = useState('');
    
    const [editableCode, setEditableCode] = useState("");

    const fetchProjectDetails = useCallback(async () => {
        if (!token) return;
        setIsLoading(true);
        setError('');
        try {
            const response = await fetch(`/api/projects/${projectId}`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (response.ok) {
                const data = await response.json();
                setProject(data);
            } else { setError('Failed to fetch project details.'); }
        } catch (err) { setError('An error occurred.'); } 
        finally { setIsLoading(false); }
    }, [projectId, token]);

    useEffect(() => { fetchProjectDetails(); }, [fetchProjectDetails]);

    const handleUpload = async (e) => {
        e.preventDefault();
        if (!fileToUpload) { setUploadError('Please select a file to upload.'); return; }
        setUploadError('');
        const formData = new FormData();
        formData.append('file', fileToUpload);
        formData.append('description', datasetDescription);
        try {
            const response = await fetch(`/api/projects/${projectId}/upload-dataset/`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData,
            });
            if (response.ok) {
                document.getElementById('file-input').value = '';
                setFileToUpload(null);
                setDatasetDescription('');
                fetchProjectDetails();
            } else {
                const errorData = await response.json();
                setUploadError(errorData.detail || 'Failed to upload file.');
            }
        } catch (err) { setUploadError('An error occurred during upload.'); }
    };

    const handleQuerySubmit = async (e) => {
        e.preventDefault();
        setIsQueryLoading(true);
        setQueryError('');
        setQueryResult(null);
        setEditableCode("");
        try {
            const response = await fetch(`/api/projects/${projectId}/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ question, language }),
            });
            if (response.ok) {
                const data = await response.json();
                setQueryResult(data);
                setEditableCode(data.generated_code);
            } else {
                const errorData = await response.json();
                setQueryError(errorData.detail || 'Failed to execute query.');
            }
        } catch (err) { setQueryError('An error occurred while querying.'); } 
        finally { setIsQueryLoading(false); }
    };
    
    const handleRunCode = async () => {
        setIsQueryLoading(true);
        setQueryError('');
        try {
            const response = await fetch(`/api/projects/${projectId}/run-code`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ code: editableCode, language }),
            });

            if (response.ok) {
                const data = await response.json();
                setQueryResult(prevResult => ({ ...prevResult, execution_results: data.execution_results }));
            } else {
                const errorData = await response.json();
                setQueryError(errorData.detail || 'Failed to run edited code.');
            }
        } catch (err) {
            setQueryError('An error occurred while running the code.');
        } finally {
            setIsQueryLoading(false);
        }
    };

    if (isLoading) return <p>Loading project...</p>;
    if (error) return <p style={{ color: 'red' }}>{error}</p>;
    if (!project) return <p>Project not found.</p>;

    return (
        <div>
            <h1>Project: {project.name}</h1>
            <p>{project.description}</p>
            <hr />
            <div className="datasets-section">
                <h2>Datasets</h2>
                {project.datasets.length > 0 ? (
                    <ul> {project.datasets.map(dataset => (<li key={dataset.id}><strong>{dataset.file_name}</strong> (Table Name: <code>{dataset.table_name}</code>)<p>{dataset.description || 'No description'}</p></li>))} </ul>
                ) : (<p>No datasets have been uploaded yet.</p>)}
            </div>
            <div className="upload-section">
                <h3>Upload a New Dataset</h3>
                <form onSubmit={handleUpload}>
                    <input type="text" value={datasetDescription} onChange={(e) => setDatasetDescription(e.target.value)} placeholder="Dataset Description" />
                    <input id="file-input" type="file" onChange={(e) => setFileToUpload(e.target.files[0])} accept=".csv" />
                    <button type="submit">Upload</button>
                </form>
                {uploadError && <p style={{ color: 'red' }}>{uploadError}</p>}
            </div>
            <hr />
            <div className="query-section">
                <h2>Ask a Question About Your Project</h2>
                <form onSubmit={handleQuerySubmit}>
                    <textarea value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="e.g., Show me a bar chart of the number of races per year" rows="4" cols="50" required />
                    <div>
                        <label>Language:</label>
                        <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                            <option value="python">Python (Pandas)</option>
                            <option value="sql">SQL</option>
                        </select>
                    </div>
                    <button type="submit" disabled={isQueryLoading}> {isQueryLoading ? 'Thinking...' : 'Generate Code'} </button>
                </form>

                {queryError && <p style={{ color: 'red' }}>{queryError}</p>}
                
                {isQueryLoading && <p>Loading results...</p>}

                {queryResult && (
                    <div className="results-section">
                        <h3>Generated Code ({queryResult.language})</h3>
                        <AceEditor mode={queryResult.language} theme="github" onChange={(newCode) => setEditableCode(newCode)} value={editableCode} name="code-editor" editorProps={{ $blockScrolling: true }} width="100%" height="200px" />
                        <button onClick={handleRunCode} style={{marginTop: '10px'}} disabled={isQueryLoading}> {isQueryLoading ? 'Running...' : 'Run Edited Code'} </button>
                        
                        <h3>Execution Results</h3>
                        {/* Use the new ResultDisplay component */}
                        {queryResult.execution_results.map((result, index) => (
                            <ResultDisplay key={index} result={result} />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

export default ProjectPage;