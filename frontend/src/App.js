import React, { useState, useEffect } from 'react';
import logo from './logo.svg';
import './App.css';

function App() {
  const [message, setMessage] = useState('');

  useEffect(() => {
    // Fetch the message from our backend API
    fetch('http://localhost:8000/')
      .then(response => response.json())
      .then(data => setMessage(data.message))
      .catch(error => console.error('Error fetching data:', error));
  }, []); // The empty dependency array ensures this effect runs only once

  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <h2>Collaborative Analytics Platform</h2>
        <p>
          Message from backend: <strong>{message || 'Loading...'}</strong>
        </p>
      </header>
    </div>
  );
}

export default App;
