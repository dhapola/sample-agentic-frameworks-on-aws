import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { BrowserRouter } from 'react-router-dom';
import DashboardView from '../../src/views/DashboardView';

describe('DashboardView', () => {
  const renderDashboardView = () => {
    return render(
      <BrowserRouter>
        <DashboardView />
      </BrowserRouter>
    );
  };

  test('renders dashboard title', () => {
    renderDashboardView();

    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  test('renders dashboard content', () => {
    renderDashboardView();

    expect(
      screen.getByText('Overview of recent evaluation runs and summary statistics will be displayed here.')
    ).toBeInTheDocument();
  });

  test('renders paper component', () => {
    const { container } = renderDashboardView();

    const paper = container.querySelector('.MuiPaper-root');
    expect(paper).toBeInTheDocument();
  });
});
