import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../../context/AuthContext';
import DashboardPage from '../DashboardPage';

// We mock the useAuth hook to simulate a logged-in user
jest.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ token: 'fake-token' }),
  AuthProvider: ({ children }) => <div>{children}</div>,
}));

test('renders dashboard with project creation form', () => {
  render(
    <AuthProvider>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </AuthProvider>
  );
  expect(screen.getByText(/Your Dashboard/i)).toBeInTheDocument();
  expect(screen.getByPlaceholderText(/Project Name/i)).toBeInTheDocument();
});