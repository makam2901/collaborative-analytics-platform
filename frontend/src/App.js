import React from 'react';
import { Routes, Route, Link, Navigate } from 'react-router-dom';  // Remove BrowserRouter
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import { useAuth } from './context/AuthContext';
import ProjectPage from './pages/ProjectPage';
import './App.css';

function App() {
  const { token, logout } = useAuth();

  return (
    
    <div className="App">
      <nav>
        <ul>
          {!token ? (
            <>
              <li><Link to="/login">Login</Link></li>
              <li><Link to="/register">Register</Link></li>
            </>
          ) : (
            <>
              <li><Link to="/dashboard">Dashboard</Link></li>
              <li><button onClick={logout}>Logout</button></li>
            </>
          )}
        </ul>
      </nav>

      <main>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route 
            path="/dashboard" 
            element={token ? <DashboardPage /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/" 
            element={token ? <Navigate to="/dashboard" /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/project/:projectId" 
            element={token ? <ProjectPage /> : <Navigate to="/login" />} 
          />
        </Routes>
      </main>
    </div>
    
  );
}

export default App;

