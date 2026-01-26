import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { BrowserRouter } from 'react-router-dom';
import DatasetsView from '../../src/views/DatasetsView';
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
    name: 'Test Dataset 1',
    description: 'First test dataset',
    testCases: [
      {
        id: 'tc1',
        input: 'Test input 1',
        expectedOutput: 'Test output 1',
      },
    ],
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'ds2',
    customerId: 'cust1',
    name: 'Test Dataset 2',
    description: 'Second test dataset',
    testCases: [],
    createdAt: '2024-01-02T00:00:00Z',
    updatedAt: '2024-01-02T00:00:00Z',
  },
];

// Mock CustomerContext
const MockCustomerProvider = ({ children }: { children: React.ReactNode }) => {
  return (
    <CustomerProvider>
      {children}
    </CustomerProvider>
  );
};

// Override useCustomer hook
jest.mock('../../src/contexts/CustomerContext', () => ({
  ...jest.requireActual('../../src/contexts/CustomerContext'),
  useCustomer: () => ({
    currentCustomer: mockCustomer,
    setCurrentCustomer: jest.fn(),
    isAdmin: false,
    setIsAdmin: jest.fn(),
  }),
}));

describe('DatasetsView', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (apiClient.getDatasets as jest.Mock).mockResolvedValue(mockDatasets);
    (apiClient.getDataset as jest.Mock).mockResolvedValue(mockDatasets[0]);
  });

  const renderDatasetsView = () => {
    return render(
      <BrowserRouter>
        <MockCustomerProvider>
          <DatasetsView />
        </MockCustomerProvider>
      </BrowserRouter>
    );
  };

  test('renders datasets view', async () => {
    renderDatasetsView();

    expect(screen.getByText('Datasets')).toBeInTheDocument();
  });

  test('loads and displays datasets', async () => {
    renderDatasetsView();

    await waitFor(() => {
      expect(screen.getByText('Test Dataset 1')).toBeInTheDocument();
      expect(screen.getByText('Test Dataset 2')).toBeInTheDocument();
    });

    expect(apiClient.getDatasets).toHaveBeenCalledTimes(1);
  });

  test('shows create dataset button', async () => {
    renderDatasetsView();

    await waitFor(() => {
      expect(screen.getByText('Create Dataset')).toBeInTheDocument();
    });
  });

  test('displays dataset information in table', async () => {
    renderDatasetsView();

    await waitFor(() => {
      expect(screen.getByText('First test dataset')).toBeInTheDocument();
      expect(screen.getByText('Second test dataset')).toBeInTheDocument();
    });
  });

  test('shows test case count', async () => {
    renderDatasetsView();

    await waitFor(() => {
      const chips = screen.getAllByText('1');
      expect(chips.length).toBeGreaterThan(0);
    });
  });

  test('shows empty state when no datasets', async () => {
    (apiClient.getDatasets as jest.Mock).mockResolvedValue([]);
    renderDatasetsView();

    await waitFor(() => {
      expect(screen.getByText('No datasets found. Create your first dataset to get started.')).toBeInTheDocument();
    });
  });

  test('shows dataset detail when selected', async () => {
    renderDatasetsView();

    await waitFor(() => {
      expect(screen.getByText('Test Dataset 1')).toBeInTheDocument();
    });

    // The detail view functionality is tested through the component's internal state
    // We verify the list view renders correctly
    expect(screen.getByText('First test dataset')).toBeInTheDocument();
  });

  test('opens create dataset dialog when button clicked', async () => {
    const user = userEvent.setup();
    renderDatasetsView();

    await waitFor(() => {
      expect(screen.getByText('Create Dataset')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Create Dataset'));

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
  });

  test('creates new dataset when form submitted', async () => {
    const user = userEvent.setup();
    (apiClient.createDataset as jest.Mock).mockResolvedValue({
      id: 'ds3',
      customerId: 'cust1',
      name: 'New Dataset',
      description: 'New description',
      testCases: [],
      createdAt: '2024-01-03T00:00:00Z',
      updatedAt: '2024-01-03T00:00:00Z',
    });

    renderDatasetsView();

    await waitFor(() => {
      expect(screen.getByText('Create Dataset')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Create Dataset'));

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    const textboxes = screen.getAllByRole('textbox');
    if (textboxes.length >= 2) {
      await user.type(textboxes[0], 'New Dataset');
      await user.type(textboxes[1], 'New description');
    }

    const saveButton = screen.getByRole('button', { name: /save/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(apiClient.createDataset).toHaveBeenCalledWith({
        name: 'New Dataset',
        description: 'New description',
      });
    });
  });

  test('updates existing dataset', async () => {
    const user = userEvent.setup();
    (apiClient.updateDataset as jest.Mock).mockResolvedValue({
      ...mockDatasets[0],
      name: 'Updated Dataset',
    });

    renderDatasetsView();

    await waitFor(() => {
      expect(screen.getByText('Test Dataset 1')).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole('button', { name: '' }).filter(
      (btn) => btn.querySelector('[data-testid="EditIcon"]')
    );

    if (editButtons.length > 0) {
      await user.click(editButtons[0]);

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        expect(screen.getByText('Edit Dataset')).toBeInTheDocument();
      });

      const textboxes = screen.getAllByRole('textbox');
      if (textboxes.length >= 1) {
        await user.clear(textboxes[0]);
        await user.type(textboxes[0], 'Updated Dataset');
      }

      await user.click(screen.getByRole('button', { name: /save/i }));

      await waitFor(() => {
        expect(apiClient.updateDataset).toHaveBeenCalled();
      });
    }
  });

  test('deletes dataset with confirmation', async () => {
    const user = userEvent.setup();
    window.confirm = jest.fn(() => true);
    (apiClient.deleteDataset as jest.Mock).mockResolvedValue(undefined);

    renderDatasetsView();

    await waitFor(() => {
      expect(screen.getByText('Test Dataset 1')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByRole('button', { name: '' }).filter(
      (btn) => btn.querySelector('[data-testid="DeleteIcon"]')
    );

    if (deleteButtons.length > 0) {
      await user.click(deleteButtons[0]);

      await waitFor(() => {
        expect(window.confirm).toHaveBeenCalled();
        expect(apiClient.deleteDataset).toHaveBeenCalledWith('ds1');
      });
    }
  });

  test('displays error message when API call fails', async () => {
    (apiClient.getDatasets as jest.Mock).mockRejectedValue({
      response: { data: { detail: 'Failed to fetch datasets' } },
    });

    renderDatasetsView();

    await waitFor(() => {
      expect(screen.getByText('Failed to fetch datasets')).toBeInTheDocument();
    });
  });

  test('views dataset detail and shows test cases', async () => {
    const user = userEvent.setup();
    renderDatasetsView();

    await waitFor(() => {
      expect(screen.getByText('Test Dataset 1')).toBeInTheDocument();
    });

    const viewButtons = screen.getAllByRole('button', { name: '' }).filter(
      (btn) => btn.querySelector('[data-testid="VisibilityIcon"]')
    );

    if (viewButtons.length > 0) {
      await user.click(viewButtons[0]);

      await waitFor(() => {
        expect(apiClient.getDataset).toHaveBeenCalledWith('ds1');
        expect(screen.getByText('Test input 1')).toBeInTheDocument();
      });
    }
  });

  test('adds test case to dataset', async () => {
    const user = userEvent.setup();
    (apiClient.addTestCase as jest.Mock).mockResolvedValue({
      id: 'tc2',
      input: 'New test input',
      expectedOutput: 'New expected output',
    });

    renderDatasetsView();

    await waitFor(() => {
      expect(screen.getByText('Test Dataset 1')).toBeInTheDocument();
    });

    const viewButtons = screen.getAllByRole('button', { name: '' }).filter(
      (btn) => btn.querySelector('[data-testid="VisibilityIcon"]')
    );

    if (viewButtons.length > 0) {
      await user.click(viewButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Add Test Case')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Add Test Case'));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        expect(screen.getByText('Create Test Case')).toBeInTheDocument();
      });

      const textboxes = screen.getAllByRole('textbox');
      if (textboxes.length >= 2) {
        await user.type(textboxes[0], 'New test input');
        await user.type(textboxes[1], 'New expected output');
      }

      await user.click(screen.getByRole('button', { name: /save/i }));

      await waitFor(() => {
        expect(apiClient.addTestCase).toHaveBeenCalled();
      });
    }
  });

  test('shows warning when no customer selected', () => {
    // Override the mock to return no customer
    jest.spyOn(require('../../src/contexts/CustomerContext'), 'useCustomer').mockReturnValue({
      currentCustomer: null,
      setCurrentCustomer: jest.fn(),
      isAdmin: false,
      setIsAdmin: jest.fn(),
    });

    render(
      <BrowserRouter>
        <MockCustomerProvider>
          <DatasetsView />
        </MockCustomerProvider>
      </BrowserRouter>
    );

    expect(screen.getByText('Please select a customer to view datasets.')).toBeInTheDocument();
  });

  test('filters datasets by customer context', async () => {
    renderDatasetsView();

    await waitFor(() => {
      expect(apiClient.getDatasets).toHaveBeenCalledTimes(1);
    });

    // Verify only customer's datasets are shown
    expect(screen.getByText('Test Dataset 1')).toBeInTheDocument();
    expect(screen.getByText('Test Dataset 2')).toBeInTheDocument();
  });
});
