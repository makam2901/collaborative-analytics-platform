import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';

function DashboardPage() {
  const { token } = useAuth();
  const [projects, setProjects] = useState([]);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDesc, setNewProjectDesc] = useState('');
  const [error, setError] = useState('');

  // Function to fetch projects
  const fetchProjects = useCallback(async () => {
    if (!token) return;
    try {
      const response = await fetch('/api/projects/', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setProjects(data);
      } else {
        console.error('Failed to fetch projects');
        setError('Could not load projects.');
      }
    } catch (err) {
      setError('An error occurred while fetching projects.');
    }
  }, [token]);

  // useEffect to fetch projects when the component loads
  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // Handler for creating a new project
  const handleCreateProject = async (e) => {
    e.preventDefault();
    if (!newProjectName.trim()) {
      setError('Project name cannot be empty.');
      return;
    }
    setError('');
    
    try {
      const response = await fetch('/api/projects/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ name: newProjectName, description: newProjectDesc }),
      });

      if (response.ok) {
        setNewProjectName('');
        setNewProjectDesc('');
        fetchProjects(); // Refresh the project list
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to create project.');
      }
    } catch (err) {
      setError('An error occurred while creating the project.');
    }
  };

  return (
    <div>
      <h1>Your Dashboard</h1>
      
      <div className="create-project-form">
        <h2>Create a New Project</h2>
        <form onSubmit={handleCreateProject}>
          <input
            type="text"
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            placeholder="Project Name"
            required
          />
          <input
            type="text"
            value={newProjectDesc}
            onChange={(e) => setNewProjectDesc(e.target.value)}
            placeholder="Project Description"
          />
          <button type="submit">Create Project</button>
        </form>
        {error && <p style={{ color: 'red' }}>{error}</p>}
      </div>

      <div className="project-list">
        <h2>Your Projects</h2>
        {projects.length > 0 ? (
          <ul>
            {projects.map(project => (
              <li key={project.id}>
                <Link to={`/project/${project.id}`}>
                  <h3>{project.name}</h3>
                  <p>{project.description || 'No description'}</p>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p>You don't have any projects yet. Create one above!</p>
        )}
      </div>
    </div>
  );
}

export default DashboardPage;