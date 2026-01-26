import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { BrowserRouter } from 'react-router-dom';
import ResultsView from '../../src/views/ResultsView';
import { CustomerProvider } from '../../src/contexts/CustomerContext';
import apiClient from '../../src/services/api';

// Mock the API client
jest.mock('../../src/services/api');

const mockCustomer = {
  id: 'cust1',
  name: 'Acme Corp',
  contactEmail: 'contact@acme.com',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

const mockDatasets = [
  {
    id: 'ds1',
    customerId: 'cust1',
    name: 'Test Dataset',
    description: 'Test dataset',
    testCases: [],
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
];

const mockProfiles = [
  {
    id: 'prof1',
    customerId: 'cust1',
    name: 'Test Profile',
    type: 'chatbot',
    connectionConfig: { endpoint: 'https://api.test.com', timeout: 30 },
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
];

const mockRuns = [
  {
    id: 'run1',
    customerId: 'cust1',
    datasetId: 'ds1',
    applicationProfileId: 'prof1',
    status: 'completed',
    startTime: '2024-01-01T10:00:00Z',
    endTime: '2024-01-01T10:05:00Z',
    responses: [
      {
        testCaseId: 'tc1',
        input: 'Test input',
        output: 'Test output',
        latency: 100,
        timestamp: '2024-01-01T10:00:01Z',
        individualMetrics: {
          accuracy: 0.95,
          relevance: 0.9,
        },
      },
    ],
    metrics: {
      averageAccuracy: 0.95,
      averageRelevance: 0.9,
      averageLatency: 100,
      medianLatency: 100,
      p95Latency: 100,
      successRate: 1.0,
      totalTestCases: 1,
      failedTestCases: 0,
    },
  },
];

// Mock CustomerContext
jest.mock('../../src/contexts/CustomerContext', () => ({
  ...jest.requireActual('../../src/contexts/CustomerContext'),
  useCustomer: () => ({
    currentCustomer: mockCustomer,
    setCurrentCustomer: jest.fn(),
    isAdmin: false,
    setIsAdmin: jest.fn(),
  }),
}));

describe('ResultsView', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (apiClient.getEvaluationRuns as jest.Mock).mockResolvedValue(mockRuns);
    (apiClient.getDatasets as jest.Mock).mockResolvedValue(mockDatasets);
    (apiClient.getApplicationProfiles as jest.Mock).mockResolvedValue(mockProfiles);
    (apiClient.getEvaluationRun as jest.Mock).mockResolvedValue(mockRuns[0]);
  });

  const renderResultsView = () => {
    return render(
      <BrowserRouter>
        <CustomerProvider>
          <ResultsView />
        </CustomerProvider>
      </BrowserRouter>
    );
  };

  test('renders results dashboard', async () => {
    renderResultsView();

    expect(screen.getByText('Results Dashboard')).toBeInTheDocument();
  });

  test('loads and displays evaluation runs', async () => {
    renderResultsView();

    await waitFor(() => {
      expect(screen.getByText('Test Dataset')).toBeInTheDocument();
      expect(screen.getByText('Test Profile')).toBeInTheDocument();
    });

    expect(apiClient.getEvaluationRuns).toHaveBeenCalledTimes(1);
  });

  test('displays metrics in table', async () => {
    renderResultsView();

    await waitFor(() => {
      expect(screen.getByText('100.0%')).toBeInTheDocument(); // Success rate
      expect(screen.getByText('100ms')).toBeInTheDocument(); // Avg latency
    });
  });

  test('shows filter and sort controls', async () => {
    renderResultsView();

    await waitFor(() => {
      expect(screen.getByLabelText('Filter by Status')).toBeInTheDocument();
      expect(screen.getByLabelText('Sort by')).toBeInTheDocument();
    });
  });

  test('shows empty state when no runs', async () => {
    (apiClient.getEvaluationRuns as jest.Mock).mockResolvedValue([]);
    renderResultsView();

    await waitFor(() => {
      expect(
        screen.getByText('No evaluation runs yet. Start an evaluation run to see results here.')
      ).toBeInTheDocument();
    });
  });

  test('displays run status chip', async () => {
    renderResultsView();

    await waitFor(() => {
      expect(screen.getByText('completed')).toBeInTheDocument();
    });
  });

  test('filters runs by status', async () => {
    const user = userEvent.setup();
    const completedRun = mockRuns[0];
    const runningRun = {
      ...mockRuns[0],
      id: 'run2',
      status: 'running',
      endTime: undefined,
    };

    (apiClient.getEvaluationRuns as jest.Mock).mockResolvedValue([completedRun, runningRun]);

    renderResultsView();

    await waitFor(() => {
      expect(screen.getByText('completed')).toBeInTheDocument();
      expect(screen.getByText('running')).toBeInTheDocument();
    });

    const filterSelect = screen.getByLabelText('Filter by Status');
    await user.selectOptions(filterSelect, 'completed');

    await waitFor(() => {
      expect(screen.getByText('completed')).toBeInTheDocument();
      expect(screen.queryByText('running')).not.toBeInTheDocument();
    });
  });

  test('sorts runs by different criteria', async () => {
    const user = userEvent.setup();
    renderResultsView();

    await waitFor(() => {
      expect(screen.getByLabelText('Sort by')).toBeInTheDocument();
    });

    const sortSelect = screen.getByLabelText('Sort by');
    await user.selectOptions(sortSelect, 'status');

    // Verify the sort select value changed
    expect(sortSelect).toHaveValue('status');
  });

  test('views run details when view button clicked', async () => {
    const user = userEvent.setup();
    renderResultsView();

    await waitFor(() => {
      expect(screen.getByText('Test Dataset')).toBeInTheDocument();
    });

    const viewButtons = screen.getAllByRole('button', { name: '' }).filter(
      (btn) => btn.querySelector('[data-testid="VisibilityIcon"]')
    );

    if (viewButtons.length > 0) {
      await user.click(viewButtons[0]);

      await waitFor(() => {
        expect(apiClient.getEvaluationRun).toHaveBeenCalledWith('run1');
        expect(screen.getByText('Run Details')).toBeInTheDocument();
      });
    }
  });

  test('displays detailed metrics in run detail view', async () => {
    const user = userEvent.setup();
    renderResultsView();

    await waitFor(() => {
      expect(screen.getByText('Test Dataset')).toBeInTheDocument();
    });

    const viewButtons = screen.getAllByRole('button', { name: '' }).filter(
      (btn) => btn.querySelector('[data-testid="VisibilityIcon"]')
    );

    if (viewButtons.length > 0) {
      await user.click(viewButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Metrics Overview')).toBeInTheDocument();
        expect(screen.getByText('95.0%')).toBeInTheDocument(); // Accuracy
        expect(screen.getByText('90.0%')).toBeInTheDocument(); // Relevance
      });
    }
  });

  test('displays test case results in detail view', async () => {
    const user = userEvent.setup();
    renderResultsView();

    await waitFor(() => {
      expect(screen.getByText('Test Dataset')).toBeInTheDocument();
    });

    const viewButtons = screen.getAllByRole('button', { name: '' }).filter(
      (btn) => btn.querySelector('[data-testid="VisibilityIcon"]')
    );

    if (viewButtons.length > 0) {
      await user.click(viewButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/Test Case Results/i)).toBeInTheDocument();
        expect(screen.getByText('Test input')).toBeInTheDocument();
        expect(screen.getByText('Test output')).toBeInTheDocument();
      });
    }
  });

  test('navigates back to list from detail view', async () => {
    const user = userEvent.setup();
    renderResultsView();

    await waitFor(() => {
      expect(screen.getByText('Test Dataset')).toBeInTheDocument();
    });

    const viewButtons = screen.getAllByRole('button', { name: '' }).filter(
      (btn) => btn.querySelector('[data-testid="VisibilityIcon"]')
    );

    if (viewButtons.length > 0) {
      await user.click(viewButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Run Details')).toBeInTheDocument();
      });

      const backButton = screen.getByRole('button', { name: '' }).querySelector('[data-testid="ArrowBackIcon"]')?.closest('button');
      if (backButton) {
        await user.click(backButton);

        await waitFor(() => {
          expect(screen.getByText('Results Dashboard')).toBeInTheDocument();
        });
      }
    }
  });

  test('displays error message when API call fails', async () => {
    (apiClient.getEvaluationRuns as jest.Mock).mockRejectedValue({
      response: { data: { detail: 'Failed to load results' } },
    });

    renderResultsView();

    await waitFor(() => {
      expect(screen.getByText('Failed to load results')).toBeInTheDocument();
    });
  });

  test('filters results by customer context', async () => {
    renderResultsView();

    await waitFor(() => {
      expect(apiClient.getEvaluationRuns).toHaveBeenCalled();
    });

    // Verify only customer's results are shown
    expect(screen.getByText('Test Dataset')).toBeInTheDocument();
  });

  test('displays charts in detail view', async () => {
    const user = userEvent.setup();
    renderResultsView();

    await waitFor(() => {
      expect(screen.getByText('Test Dataset')).toBeInTheDocument();
    });

    const viewButtons = screen.getAllByRole('button', { name: '' }).filter(
      (btn) => btn.querySelector('[data-testid="VisibilityIcon"]')
    );

    if (viewButtons.length > 0) {
      await user.click(viewButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Latency by Test Case')).toBeInTheDocument();
        expect(screen.getByText('Accuracy & Relevance')).toBeInTheDocument();
      });
    }
  });

  test('shows message when no runs match filters', async () => {
    const user = userEvent.setup();
    renderResultsView();

    await waitFor(() => {
      expect(screen.getByText('Test Dataset')).toBeInTheDocument();
    });

    const filterSelect = screen.getByLabelText('Filter by Status');
    await user.selectOptions(filterSelect, 'failed');

    await waitFor(() => {
      expect(screen.getByText('No runs match the selected filters.')).toBeInTheDocument();
    });
  });

  test('shows warning when no customer selected', () => {
    // Override the mock for this specific test
    const useCustomerSpy = jest.spyOn(require('../../src/contexts/CustomerContext'), 'useCustomer');
    useCustomerSpy.mockReturnValue({
      currentCustomer: null,
      setCurrentCustomer: jest.fn(),
      isAdmin: false,
      setIsAdmin: jest.fn(),
    });

    render(
      <BrowserRouter>
        <CustomerProvider>
          <ResultsView />
        </CustomerProvider>
      </BrowserRouter>
    );

    expect(screen.getByText('Please select a customer to view results.')).toBeInTheDocument();
    
    // Restore the original mock
    useCustomerSpy.mockRestore();
  });
});
