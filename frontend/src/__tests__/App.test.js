import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App';
// Add useAuth to this import
import { AuthProvider, useAuth } from '../context/AuthContext';

// Import your page components
import LoginPage from '../pages/LoginPage';
import RegisterPage from '../pages/RegisterPage';
import DashboardPage from '../pages/DashboardPage';
import ProjectPage from '../pages/ProjectPage';

// Your console.log statements for debugging
console.log('LoginPage:', LoginPage);
console.log('RegisterPage:', RegisterPage);
console.log('DashboardPage:', DashboardPage);
console.log('ProjectPage:', ProjectPage);
console.log('useAuth:', useAuth);


test('renders login link when not authenticated', () => {
  render(
    <AuthProvider>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </AuthProvider>
  );
  const loginLink = screen.getByRole('link', { name: /login/i });
  expect(loginLink).toBeInTheDocument();
});

test('renders dashboard link when authenticated', () => {
  // Mock the useAuth hook to return an authenticated state
  const mockUseAuth = {
    token: 'fake-token',
    login: jest.fn(),
    logout: jest.fn(),
    loading: false,
  };

  jest.spyOn(require('../context/AuthContext'), 'useAuth').mockImplementation(() => mockUseAuth);


  render(
    <AuthProvider>
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    </AuthProvider>
  );

  const dashboardLink = screen.getByRole('link', { name: /dashboard/i });
  expect(dashboardLink).toBeInTheDocument();

  // Clean up the mock
  jest.restoreAllMocks();
});