import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { BrowserRouter } from 'react-router-dom';
import { CustomerProvider } from '../../src/contexts/CustomerContext';
import Layout from '../../src/components/Layout';

describe('Layout', () => {
  const renderLayout = () => {
    return render(
      <BrowserRouter>
        <CustomerProvider>
          <Layout />
        </CustomerProvider>
      </BrowserRouter>
    );
  };

  test('renders navigation menu', () => {
    renderLayout();
    
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Datasets')).toBeInTheDocument();
    expect(screen.getByText('Evaluations')).toBeInTheDocument();
    expect(screen.getByText('Results')).toBeInTheDocument();
  });

  test('renders app title', () => {
    renderLayout();
    
    expect(screen.getByText('Gen AI Evaluation Platform')).toBeInTheDocument();
  });

  test('does not show admin menu by default', () => {
    renderLayout();
    
    expect(screen.queryByText('Admin')).not.toBeInTheDocument();
  });
});
