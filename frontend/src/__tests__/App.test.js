import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext'; // ✅ Adjust path if needed
import App from '../App';

// We are telling Jest to replace 'react-plotly.js' with a fake component.
// This prevents it from running the complex Plotly code that crashes the test.
jest.mock('react-plotly.js', () => ({
  __esModule: true,
  default: () => <div data-testid="mocked-plot" />, // A simple, identifiable placeholder
}));

test('renders login link when not authenticated', () => {
  render(
    // The App must be wrapped in the AuthProvider for the useAuth() hook to work
    <AuthProvider>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </AuthProvider>
  );
  const linkElement = screen.getByText(/Login/i);
  expect(linkElement).toBeInTheDocument();
});

console.log('LoginPage:', LoginPage);
console.log('RegisterPage:', RegisterPage);
console.log('DashboardPage:', DashboardPage);
console.log('ProjectPage:', ProjectPage);
console.log('useAuth:', useAuth);