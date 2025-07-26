import React from 'react';
import Plot from 'react-plotly.js';

function ResultDisplay({ result }) {
  // Check if the result is a Plotly JSON object
  if (result.type === 'plotly_json' && typeof result.data === 'string') {
    try {
      const plotData = JSON.parse(result.data);
      return (
        <Plot
          data={plotData.data}
          layout={plotData.layout}
          config={{ responsive: true }}
        />
      );
    } catch (e) {
      return <pre style={{ color: 'red' }}>Error parsing chart JSON: {e.toString()}</pre>;
    }
  }

  // Check for standard text or error output
  if (result.type === 'error') {
    return <pre style={{ color: 'red' }}><strong>Error:</strong> {result.evalue}</pre>;
  }

  // Fallback to display plain text
  return <pre>{result.text}</pre>;
}

export default ResultDisplay;
