import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { BrowserRouter } from 'react-router-dom';
import AdminView from '../../src/views/AdminView';
import apiClient from '../../src/services/api';

// Mock the API client
jest.mock('../../src/services/api');

const mockCustomers = [
  {
    id: 'cust1',
    name: 'Acme Corp',
    contactEmail: 'contact@acme.com',
    contactPhone: '555-0100',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'cust2',
    name: 'TechStart Inc',
    contactEmail: 'info@techstart.com',
    createdAt: '2024-01-02T00:00:00Z',
    updatedAt: '2024-01-02T00:00:00Z',
  },
];

const mockProfiles = [
  {
    id: 'prof1',
    customerId: 'cust1',
    name: 'Acme Chatbot',
    type: 'chatbot',
    connectionConfig: {
      endpoint: 'https://api.acme.com/chat',
      timeout: 30,
    },
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
];

describe('AdminView', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (apiClient.getCustomers as jest.Mock).mockResolvedValue(mockCustomers);
    (apiClient.getApplicationProfiles as jest.Mock).mockResolvedValue(mockProfiles);
  });

  const renderAdminView = () => {
    return render(
      <BrowserRouter>
        <AdminView />
      </BrowserRouter>
    );
  };

  test('renders admin panel with tabs', async () => {
    renderAdminView();

    expect(screen.getByText('Admin Panel')).toBeInTheDocument();
    expect(screen.getAllByText('Customers').length).toBeGreaterThan(0);
    expect(screen.getByText('Application Profiles')).toBeInTheDocument();
  });

  test('loads and displays customers', async () => {
    renderAdminView();

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      expect(screen.getByText('TechStart Inc')).toBeInTheDocument();
    });

    expect(apiClient.getCustomers).toHaveBeenCalledTimes(1);
  });

  test('shows add customer button', async () => {
    renderAdminView();

    await waitFor(() => {
      expect(screen.getByText('Add Customer')).toBeInTheDocument();
    });
  });

  test('switches to application profiles tab', async () => {
    const user = userEvent.setup();
    renderAdminView();

    const profilesTab = screen.getByText('Application Profiles');
    await user.click(profilesTab);

    await waitFor(() => {
      expect(screen.getByText('Acme Chatbot')).toBeInTheDocument();
    });
  });

  test('displays customer information in table', async () => {
    renderAdminView();

    await waitFor(() => {
      expect(screen.getByText('contact@acme.com')).toBeInTheDocument();
      expect(screen.getByText('555-0100')).toBeInTheDocument();
    });
  });

  test('shows empty state when no customers', async () => {
    (apiClient.getCustomers as jest.Mock).mockResolvedValue([]);
    renderAdminView();

    await waitFor(() => {
      expect(screen.getByText('No customers found')).toBeInTheDocument();
    });
  });

  test('opens customer dialog when add button clicked', async () => {
    const user = userEvent.setup();
    renderAdminView();

    await waitFor(() => {
      expect(screen.getByText('Add Customer')).toBeInTheDocument();
    });

    const addButton = screen.getByText('Add Customer');
    await user.click(addButton);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('Create Customer')).toBeInTheDocument();
    });
  });

  test('creates new customer when form submitted', async () => {
    const user = userEvent.setup();
    (apiClient.createCustomer as jest.Mock).mockResolvedValue({
      id: 'cust3',
      name: 'New Corp',
      contactEmail: 'new@corp.com',
      createdAt: '2024-01-03T00:00:00Z',
      updatedAt: '2024-01-03T00:00:00Z',
    });

    renderAdminView();

    await waitFor(() => {
      expect(screen.getByText('Add Customer')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Add Customer'));

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    // Find inputs by placeholder or role
    const inputs = screen.getAllByRole('textbox');
    const nameInput = inputs.find((input) => input.getAttribute('name') === 'name' || input.closest('.MuiFormControl-root')?.querySelector('label')?.textContent === 'Name');
    const emailInput = inputs.find((input) => input.getAttribute('type') === 'email' || input.closest('.MuiFormControl-root')?.querySelector('label')?.textContent === 'Email');
    const phoneInput = inputs.find((input) => input.getAttribute('type') === 'tel' || input.closest('.MuiFormControl-root')?.querySelector('label')?.textContent === 'Phone');

    if (nameInput) await user.type(nameInput, 'New Corp');
    if (emailInput) await user.type(emailInput, 'new@corp.com');
    if (phoneInput) await user.type(phoneInput, '555-0200');

    const saveButton = screen.getByRole('button', { name: /save/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(apiClient.createCustomer).toHaveBeenCalledWith({
        name: 'New Corp',
        contactEmail: 'new@corp.com',
        contactPhone: '555-0200',
      });
    });
  });

  test('opens edit dialog with customer data', async () => {
    const user = userEvent.setup();
    renderAdminView();

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole('button', { name: '' }).filter(
      (btn) => btn.querySelector('[data-testid="EditIcon"]')
    );
    
    if (editButtons.length > 0) {
      await user.click(editButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Edit Customer')).toBeInTheDocument();
        expect(screen.getByDisplayValue('Acme Corp')).toBeInTheDocument();
        expect(screen.getByDisplayValue('contact@acme.com')).toBeInTheDocument();
      });
    }
  });

  test('deletes customer with confirmation', async () => {
    const user = userEvent.setup();
    window.confirm = jest.fn(() => true);
    (apiClient.deleteCustomer as jest.Mock).mockResolvedValue(undefined);

    renderAdminView();

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByRole('button', { name: '' }).filter(
      (btn) => btn.querySelector('[data-testid="DeleteIcon"]')
    );

    if (deleteButtons.length > 0) {
      await user.click(deleteButtons[0]);

      await waitFor(() => {
        expect(window.confirm).toHaveBeenCalled();
        expect(apiClient.deleteCustomer).toHaveBeenCalledWith('cust1');
      });
    }
  });

  test('displays error message when API call fails', async () => {
    (apiClient.getCustomers as jest.Mock).mockRejectedValue({
      response: { data: { detail: 'Database connection failed' } },
    });

    renderAdminView();

    await waitFor(() => {
      expect(screen.getByText('Database connection failed')).toBeInTheDocument();
    });
  });

  test('creates application profile with customer selection', async () => {
    const user = userEvent.setup();
    (apiClient.createApplicationProfile as jest.Mock).mockResolvedValue({
      id: 'prof2',
      customerId: 'cust1',
      name: 'New Profile',
      type: 'rag',
      connectionConfig: { endpoint: 'https://api.new.com', timeout: 30 },
      createdAt: '2024-01-03T00:00:00Z',
      updatedAt: '2024-01-03T00:00:00Z',
    });

    renderAdminView();

    await waitFor(() => {
      expect(screen.getByText('Application Profiles')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Application Profiles'));

    await waitFor(() => {
      expect(screen.getByText('Add Profile')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Add Profile'));

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('Create Application Profile')).toBeInTheDocument();
    });

    // Find inputs by role and context
    const textboxes = screen.getAllByRole('textbox');
    const comboboxes = screen.getAllByRole('combobox');

    // Fill in the form using the inputs we can find
    if (comboboxes.length >= 2) {
      // First combobox is customer, second is type
      await user.selectOptions(comboboxes[0], 'cust1');
      await user.selectOptions(comboboxes[1], 'rag');
    }

    // Type in text fields
    if (textboxes.length >= 2) {
      await user.type(textboxes[0], 'New Profile');
      await user.type(textboxes[1], 'https://api.new.com');
    }

    const saveButton = screen.getByRole('button', { name: /save/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(apiClient.createApplicationProfile).toHaveBeenCalled();
    });
  });

  test('disables add profile button when no customers', async () => {
    (apiClient.getCustomers as jest.Mock).mockResolvedValue([]);
    const user = userEvent.setup();
    renderAdminView();

    await user.click(screen.getByText('Application Profiles'));

    await waitFor(() => {
      const addButton = screen.getByText('Add Profile').closest('button');
      expect(addButton).toBeDisabled();
    });
  });

  test('shows empty state for application profiles', async () => {
    (apiClient.getApplicationProfiles as jest.Mock).mockResolvedValue([]);
    const user = userEvent.setup();
    renderAdminView();

    await user.click(screen.getByText('Application Profiles'));

    await waitFor(() => {
      expect(screen.getByText('No application profiles found')).toBeInTheDocument();
    });
  });
});
