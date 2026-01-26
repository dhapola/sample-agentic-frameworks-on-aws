import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from '../../src/App';

describe('App', () => {
  test('renders the application with navigation', () => {
    render(<App />);
    
    // Check that the app title is present
    expect(screen.getByText('Gen AI Evaluation Platform')).toBeInTheDocument();
    
    // Check that navigation items are present
    expect(screen.getAllByText('Dashboard').length).toBeGreaterThan(0);
    expect(screen.getByText('Datasets')).toBeInTheDocument();
    expect(screen.getByText('Evaluations')).toBeInTheDocument();
    expect(screen.getByText('Results')).toBeInTheDocument();
  });

  test('renders dashboard view by default', () => {
    render(<App />);
    
    // Check that the dashboard content is displayed
    expect(screen.getByText('Overview of recent evaluation runs and summary statistics will be displayed here.')).toBeInTheDocument();
  });
});
