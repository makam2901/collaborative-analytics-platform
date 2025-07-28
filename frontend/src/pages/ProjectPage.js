import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AceEditor from "react-ace";
import ResultDisplay from '../components/ResultDisplay';

import "ace-builds/src-noconflict/mode-python";
import "ace-builds/src-noconflict/mode-sql";
import "ace-builds/src-noconflict/theme-github";

function DataTable({ jsonData }) {
    if (!jsonData) return null;
    try {
        const data = JSON.parse(jsonData);
        if (!Array.isArray(data) || data.length === 0) return <p>Query returned no data.</p>;

        const headers = Object.keys(data[0]);
        return (
            <table style={{ borderCollapse: 'collapse', width: '100%', marginTop: '10px' }}>
                <thead>
                    <tr>
                        {headers.map(header => <th key={header} style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'left' }}>{header}</th>)}
                    </tr>
                </thead>
                <tbody>
                    {data.map((row, i) => (
                        <tr key={i}>
                            {headers.map(header => <td key={header} style={{ border: '1px solid #ddd', padding: '8px' }}>{String(row[header])}</td>)}
                        </tr>
                    ))}
                </tbody>
            </table>
        );
    } catch (e) {
        // If it's not JSON, it might be a single value or an error message
        return <pre>{jsonData}</pre>;
    }
}

function ProjectPage() {
    const { projectId } = useParams();
    const { token } = useAuth();
    const [project, setProject] = useState(null);
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(true);

    // State for the upload form
    const [fileToUpload, setFileToUpload] = useState(null);
    const [datasetDescription, setDatasetDescription] = useState('');
    const [uploadError, setUploadError] = useState('');

    // State for the query form
    const [question, setQuestion] = useState('');
    const [language, setLanguage] = useState('python');
    const [queryResult, setQueryResult] = useState(null);
    const [isQueryLoading, setIsQueryLoading] = useState(false);
    const [queryError, setQueryError] = useState('');
    const [editableCode, setEditableCode] = useState("");

    // State for model selection
    const [provider, setProvider] = useState('openrouter');
    const [model, setModel] = useState('qwen/qwen3-coder:free');

    // State for visulization
    const [chartType, setChartType] = useState('bar');
    const [xAxis, setXAxis] = useState('');
    const [yAxis, setYAxis] = useState('');
    const [legend, setLegend] = useState('');
    const [chartPlotJson, setChartPlotJson] = useState(null);
    const [isChartLoading, setIsChartLoading] = useState(false);

    const handleProviderChange = (e) => {
        const newProvider = e.target.value;
        setProvider(newProvider);
        // Set the default model when the provider changes
        if (newProvider === 'gemini') {
            setModel('gemini-1.5-flash');
        } else if (newProvider === 'ollama') {
            setModel('llama3');
        } else if (newProvider === 'openrouter') {
            setModel('qwen/qwen3-coder:free');
        }
    };

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
                body: JSON.stringify({ question, language, provider, model }),
            });
            if (response.ok) {
                const data = await response.json();
                setQueryResult(data);
                setEditableCode(data.aggregation_code || "");
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
                body: JSON.stringify({ code: editableCode, language: queryResult.language, provider, model }),
            });

            if (response.ok) {
                const data = await response.json();
                setQueryResult(prevResult => ({
                    ...prevResult,
                    aggregation_code: data.aggregation_code,
                    datatable_json: data.datatable_json,
                    plot_json: data.plot_json
                }));
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

    const tableColumns = useMemo(() => {
        if (!queryResult || !queryResult.datatable_json) return [];
        try {
            const data = JSON.parse(queryResult.datatable_json);
            if (Array.isArray(data) && data.length > 0) {
                return Object.keys(data[0]);
            }
        } catch (e) { return []; }
        return [];
    }, [queryResult]);

    const handleGenerateChart = async (e) => {
        e.preventDefault();
        setIsChartLoading(true);
        setChartPlotJson(null);
        try {
            const response = await fetch(`/api/projects/${projectId}/visualize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({
                    original_question: question,
                    datatable_json: queryResult.datatable_json,
                    chart_type: chartType,
                    x_axis: xAxis,
                    y_axis: yAxis,
                    legend: legend || undefined,
                    provider, model
                }),
            });
            if (response.ok) {
                const data = await response.json();
                setChartPlotJson(data.plot_json);
            } else {
                const errorData = await response.json();
                setQueryError(errorData.detail || 'Failed to generate chart.');
            }
        } catch (err) {
            setQueryError('An error occurred while generating the chart.');
        } finally {
            setIsChartLoading(false);
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
                    <div style={{ display: 'flex', gap: '20px', alignItems: 'center', marginTop: '10px' }}>
                        <div>
                            <label>Language: </label>
                            <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                                <option value="python">Python</option>
                                <option value="sql">SQL</option>
                            </select>
                        </div>
                        <div>
                            <label>LLM Provider: </label>
                            <select value={provider} onChange={handleProviderChange}>
                                <option value="gemini">Gemini</option>
                                <option value="ollama">Ollama</option>
                                <option value="openrouter">OpenRouter (Qwen)</option>
                            </select>
                        </div>
                        <div>
                            <label>Model: </label>
                            {provider === 'gemini' && (
                                <select value={model} onChange={(e) => setModel(e.target.value)}>
                                    <option value="gemini-1.5-flash">gemini-1.5-flash</option>
                                </select>
                            )}
                            {provider === 'ollama' && (
                                <select value={model} onChange={(e) => setModel(e.target.value)}>
                                    <option value="llama3">llama3</option>
                                    <option value="codellama">codellama</option>
                                </select>
                            )}
                            {provider === 'openrouter' && (
                                <select value={model} onChange={(e) => setModel(e.g.target.value)}>
                                    <option value="qwen/qwen3-coder:free">Qwen3 Coder (Free)</option>
                                </select>
                            )}
                        </div>
                    </div>
                    <button type="submit" disabled={isQueryLoading} style={{marginTop: '10px'}}>
                        {isQueryLoading ? 'Thinking...' : 'Generate Code'}
                    </button>
                </form>
                {queryError && <p style={{ color: 'red' }}>{queryError}</p>}
                {isQueryLoading && <p>Loading results...</p>}
            </div>

            {queryResult && (
                <div className="results-grid">
                    {/* Left Column: Code Editor */}
                    <div className="results-grid-left">
                        <h3>Generated Code</h3>
                        <AceEditor
                            mode={queryResult.language}
                            theme="github"
                            onChange={(newCode) => setEditableCode(newCode)}
                            value={editableCode}
                            name="aggregation-code-editor"
                            width="100%"
                            editorProps={{ $blockScrolling: true }}
                        />
                        <button onClick={handleRunCode} disabled={isQueryLoading}>
                            Run Edited Code
                        </button>
                    </div>

                    {/* Right Column: Data Table */}
                    <div className="results-grid-right">
                        <h3>Data Table Result</h3>
                        <DataTable jsonData={queryResult.datatable_json} />
                    </div>
                </div>
            )}

            {queryResult && queryResult.datatable_json && (
                <div className="visualization-creator" style={{marginTop: '20px', borderTop: '2px solid #eee', paddingTop: '20px'}}>
                    <h2>Create a Visualization</h2>
                    <form onSubmit={handleGenerateChart}>
                        <div style={{display: 'flex', gap: '15px', alignItems: 'center'}}>
                            <div>
                                <label>Chart Type: </label>
                                <select value={chartType} onChange={e => setChartType(e.target.value)}>
                                    <option value="bar">Bar Chart</option>
                                    <option value="line">Line Chart</option>
                                    <option value="scatter">Scatter Plot</option>
                                    <option value="pie">Pie Chart</option>
                                    <option value="histogram">Histogram</option>
                                </select>
                            </div>
                            <div>
                                <label>X-Axis: </label>
                                <select value={xAxis} onChange={e => setXAxis(e.target.value)} required>
                                    <option value="">Select Column</option>
                                    {tableColumns.map(col => <option key={col} value={col}>{col}</option>)}
                                </select>
                            </div>
                            <div>
                                <label>Y-Axis: </label>
                                <select value={yAxis} onChange={e => setYAxis(e.target.value)} required>
                                    <option value="">Select Column</option>
                                    {tableColumns.map(col => <option key={col} value={col}>{col}</option>)}
                                </select>
                            </div>
                            <div>
                                <label>Legend/Color (Optional): </label>
                                <select value={legend} onChange={e => setLegend(e.target.value)}>
                                    <option value="">None</option>
                                    {tableColumns.map(col => <option key={col} value={col}>{col}</option>)}
                                </select>
                            </div>
                        </div>
                        <button type="submit" disabled={isChartLoading} style={{marginTop: '10px'}}>
                            {isChartLoading ? 'Generating...' : 'Generate Chart'}
                        </button>
                    </form>
                </div>
            )}
            
            {chartPlotJson && (
                <div className="chart-section" style={{marginTop: '20px'}}>
                    <h3>Chart</h3>
                    <ResultDisplay result={{ type: 'plotly_json', data: chartPlotJson }} />
                </div>
            )}
        </div>
    );
}

export default ProjectPage;