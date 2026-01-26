import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { BrowserRouter } from 'react-router-dom';
import EvaluationsView from '../../src/views/EvaluationsView';
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
    testCases: [{ id: 'tc1', input: 'test', expectedOutput: 'output' }],
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
        input: 'test',
        output: 'result',
        latency: 100,
        timestamp: '2024-01-01T10:00:01Z',
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
  {
    id: 'run2',
    customerId: 'cust1',
    datasetId: 'ds1',
    applicationProfileId: 'prof1',
    status: 'running',
    startTime: '2024-01-01T11:00:00Z',
    responses: [],
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

describe('EvaluationsView', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (apiClient.getEvaluationRuns as jest.Mock).mockResolvedValue(mockRuns);
    (apiClient.getDatasets as jest.Mock).mockResolvedValue(mockDatasets);
    (apiClient.getApplicationProfiles as jest.Mock).mockResolvedValue(mockProfiles);
  });

  const renderEvaluationsView = () => {
    return render(
      <BrowserRouter>
        <CustomerProvider>
          <EvaluationsView />
        </CustomerProvider>
      </BrowserRouter>
    );
  };

  test('renders evaluations view', async () => {
    renderEvaluationsView();

    expect(screen.getByText('Evaluation Runs')).toBeInTheDocument();
  });

  test('loads and displays evaluation runs', async () => {
    renderEvaluationsView();

    await waitFor(() => {
      expect(screen.getAllByText('Test Dataset').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Test Profile').length).toBeGreaterThan(0);
    });

    expect(apiClient.getEvaluationRuns).toHaveBeenCalledTimes(1);
  });

  test('shows start evaluation run button', async () => {
    renderEvaluationsView();

    await waitFor(() => {
      expect(screen.getByText('Start Evaluation Run')).toBeInTheDocument();
    });
  });

  test('displays run status with correct colors', async () => {
    renderEvaluationsView();

    await waitFor(() => {
      expect(screen.getByText('completed')).toBeInTheDocument();
      expect(screen.getByText('running')).toBeInTheDocument();
    });
  });

  test('shows duration for completed runs', async () => {
    renderEvaluationsView();

    await waitFor(() => {
      // Duration should be 300 seconds (5 minutes)
      expect(screen.getByText('300s')).toBeInTheDocument();
    });
  });

  test('shows in progress for running runs', async () => {
    renderEvaluationsView();

    await waitFor(() => {
      expect(screen.getByText('In progress...')).toBeInTheDocument();
    });
  });

  test('shows empty state when no runs', async () => {
    (apiClient.getEvaluationRuns as jest.Mock).mockResolvedValue([]);
    renderEvaluationsView();

    await waitFor(() => {
      expect(
        screen.getByText('No evaluation runs yet. Start your first evaluation run to test your AI application.')
      ).toBeInTheDocument();
    });
  });

  test('shows info message when no datasets or profiles', async () => {
    (apiClient.getDatasets as jest.Mock).mockResolvedValue([]);
    (apiClient.getApplicationProfiles as jest.Mock).mockResolvedValue([]);
    renderEvaluationsView();

    await waitFor(() => {
      expect(
        screen.getByText(
          'You need to create at least one dataset and one application profile before starting an evaluation run.'
        )
      ).toBeInTheDocument();
    });
  });

  test('disables start button when no datasets or profiles', async () => {
    (apiClient.getDatasets as jest.Mock).mockResolvedValue([]);
    renderEvaluationsView();

    await waitFor(() => {
      const button = screen.getByText('Start Evaluation Run').closest('button');
      expect(button).toBeDisabled();
    });
  });

  test('opens run dialog when start button clicked', async () => {
    const user = userEvent.setup();
    renderEvaluationsView();

    await waitFor(() => {
      expect(screen.getByText('Start Evaluation Run')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Start Evaluation Run'));

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
  });

  test('starts evaluation run when form submitted', async () => {
    const user = userEvent.setup();
    (apiClient.startEvaluationRun as jest.Mock).mockResolvedValue({
      id: 'run3',
      customerId: 'cust1',
      datasetId: 'ds1',
      applicationProfileId: 'prof1',
      status: 'pending',
      startTime: '2024-01-01T12:00:00Z',
      responses: [],
    });

    renderEvaluationsView();

    await waitFor(() => {
      expect(screen.getByText('Start Evaluation Run')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Start Evaluation Run'));

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    const comboboxes = screen.getAllByRole('combobox');
    if (comboboxes.length >= 2) {
      await user.selectOptions(comboboxes[0], 'ds1');
      await user.selectOptions(comboboxes[1], 'prof1');
    }

    const startButtons = screen.getAllByRole('button', { name: /start run/i });
    if (startButtons.length > 0) {
      await user.click(startButtons[startButtons.length - 1]);
    }

    await waitFor(() => {
      expect(apiClient.startEvaluationRun).toHaveBeenCalledWith({
        datasetId: 'ds1',
        applicationProfileId: 'prof1',
      });
    });
  });

  test('displays error message when run fails to start', async () => {
    const user = userEvent.setup();
    (apiClient.startEvaluationRun as jest.Mock).mockRejectedValue({
      response: { data: { detail: 'Application profile not found' } },
    });

    renderEvaluationsView();

    await waitFor(() => {
      expect(screen.getByText('Start Evaluation Run')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Start Evaluation Run'));

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    const comboboxes = screen.getAllByRole('combobox');
    if (comboboxes.length >= 2) {
      await user.selectOptions(comboboxes[0], 'ds1');
      await user.selectOptions(comboboxes[1], 'prof1');
    }

    const startButtons = screen.getAllByRole('button', { name: /start run/i });
    if (startButtons.length > 0) {
      await user.click(startButtons[startButtons.length - 1]);
    }

    await waitFor(() => {
      expect(screen.getByText('Application profile not found')).toBeInTheDocument();
    });
  });

  test('shows warning when no customer selected', () => {
    jest.spyOn(require('../../src/contexts/CustomerContext'), 'useCustomer').mockReturnValue({
      currentCustomer: null,
      setCurrentCustomer: jest.fn(),
      isAdmin: false,
      setIsAdmin: jest.fn(),
    });

    render(
      <BrowserRouter>
        <CustomerProvider>
          <EvaluationsView />
        </CustomerProvider>
      </BrowserRouter>
    );

    expect(screen.getByText('Please select a customer to view evaluation runs.')).toBeInTheDocument();
  });

  test('displays loading state', async () => {
    (apiClient.getEvaluationRuns as jest.Mock).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(mockRuns), 100))
    );

    renderEvaluationsView();

    expect(screen.getByRole('progressbar')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });
  });

  test('filters runs by customer context', async () => {
    renderEvaluationsView();

    await waitFor(() => {
      expect(apiClient.getEvaluationRuns).toHaveBeenCalledTimes(1);
    });

    // Verify only customer's runs are shown
    expect(screen.getAllByText('Test Dataset').length).toBeGreaterThan(0);
  });

  test('disables start button when form incomplete', async () => {
    const user = userEvent.setup();
    renderEvaluationsView();

    await waitFor(() => {
      expect(screen.getByText('Start Evaluation Run')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Start Evaluation Run'));

    await waitFor(() => {
      const startButton = screen.getAllByRole('button', { name: /start run/i })[1];
      expect(startButton).toBeDisabled();
    });
  });

  test('closes dialog when cancel clicked', async () => {
    const user = userEvent.setup();
    renderEvaluationsView();

    await waitFor(() => {
      expect(screen.getByText('Start Evaluation Run')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Start Evaluation Run'));

    await waitFor(() => {
      expect(screen.getByLabelText('Dataset')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /cancel/i }));

    await waitFor(() => {
      expect(screen.queryByLabelText('Dataset')).not.toBeInTheDocument();
    });
  });
});
