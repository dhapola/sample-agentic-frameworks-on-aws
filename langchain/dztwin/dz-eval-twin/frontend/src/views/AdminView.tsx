import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  CircularProgress,
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';
import { Customer, ApplicationProfile } from '../types';
import apiClient from '../services/api';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const AdminView: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [profiles, setProfiles] = useState<ApplicationProfile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Customer dialog state
  const [customerDialogOpen, setCustomerDialogOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [customerForm, setCustomerForm] = useState({
    name: '',
    contactEmail: '',
    contactPhone: '',
  });

  // Profile dialog state
  const [profileDialogOpen, setProfileDialogOpen] = useState(false);
  const [editingProfile, setEditingProfile] = useState<ApplicationProfile | null>(null);
  const [profileForm, setProfileForm] = useState({
    customerId: '',
    name: '',
    type: '',
    endpoint: '',
    timeout: '30',
  });

  useEffect(() => {
    loadCustomers();
    loadProfiles();
  }, []);

  const loadCustomers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getCustomers();
      setCustomers(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load customers');
    } finally {
      setLoading(false);
    }
  };

  const loadProfiles = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getApplicationProfiles();
      setProfiles(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load application profiles');
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  // Customer handlers
  const handleCreateCustomer = () => {
    setEditingCustomer(null);
    setCustomerForm({ name: '', contactEmail: '', contactPhone: '' });
    setCustomerDialogOpen(true);
  };

  const handleEditCustomer = (customer: Customer) => {
    setEditingCustomer(customer);
    setCustomerForm({
      name: customer.name,
      contactEmail: customer.contactEmail,
      contactPhone: customer.contactPhone || '',
    });
    setCustomerDialogOpen(true);
  };

  const handleSaveCustomer = async () => {
    try {
      setError(null);
      if (editingCustomer) {
        await apiClient.updateCustomer(editingCustomer.id, customerForm);
      } else {
        await apiClient.createCustomer(customerForm);
      }
      setCustomerDialogOpen(false);
      loadCustomers();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save customer');
    }
  };

  const handleDeleteCustomer = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this customer?')) return;
    try {
      setError(null);
      await apiClient.deleteCustomer(id);
      loadCustomers();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete customer');
    }
  };

  // Profile handlers
  const handleCreateProfile = () => {
    setEditingProfile(null);
    setProfileForm({
      customerId: customers[0]?.id || '',
      name: '',
      type: 'chatbot',
      endpoint: '',
      timeout: '30',
    });
    setProfileDialogOpen(true);
  };

  const handleEditProfile = (profile: ApplicationProfile) => {
    setEditingProfile(profile);
    setProfileForm({
      customerId: profile.customerId,
      name: profile.name,
      type: profile.type,
      endpoint: profile.connectionConfig.endpoint,
      timeout: String(profile.connectionConfig.timeout || 30),
    });
    setProfileDialogOpen(true);
  };

  const handleSaveProfile = async () => {
    try {
      setError(null);
      const profileData = {
        name: profileForm.name,
        type: profileForm.type,
        connectionConfig: {
          endpoint: profileForm.endpoint,
          timeout: parseInt(profileForm.timeout),
        },
      };

      if (editingProfile) {
        await apiClient.updateApplicationProfile(editingProfile.id, profileData);
      } else {
        await apiClient.createApplicationProfile(profileForm.customerId, profileData);
      }
      setProfileDialogOpen(false);
      loadProfiles();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save application profile');
    }
  };

  const handleDeleteProfile = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this application profile?')) return;
    try {
      setError(null);
      await apiClient.deleteApplicationProfile(id);
      loadProfiles();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete application profile');
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Admin Panel
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Paper sx={{ mt: 2 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="Customers" />
          <Tab label="Application Profiles" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6">Customers</Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleCreateCustomer}
            >
              Add Customer
            </Button>
          </Box>

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Email</TableCell>
                    <TableCell>Phone</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {customers.map((customer) => (
                    <TableRow key={customer.id}>
                      <TableCell>{customer.name}</TableCell>
                      <TableCell>{customer.contactEmail}</TableCell>
                      <TableCell>{customer.contactPhone || '-'}</TableCell>
                      <TableCell>{new Date(customer.createdAt).toLocaleDateString()}</TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          onClick={() => handleEditCustomer(customer)}
                          color="primary"
                        >
                          <EditIcon />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleDeleteCustomer(customer.id)}
                          color="error"
                        >
                          <DeleteIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                  {customers.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} align="center">
                        No customers found
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6">Application Profiles</Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleCreateProfile}
              disabled={customers.length === 0}
            >
              Add Profile
            </Button>
          </Box>

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Customer</TableCell>
                    <TableCell>Endpoint</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {profiles.map((profile) => {
                    const customer = customers.find((c) => c.id === profile.customerId);
                    return (
                      <TableRow key={profile.id}>
                        <TableCell>{profile.name}</TableCell>
                        <TableCell>{profile.type}</TableCell>
                        <TableCell>{customer?.name || profile.customerId}</TableCell>
                        <TableCell>{profile.connectionConfig.endpoint}</TableCell>
                        <TableCell align="right">
                          <IconButton
                            size="small"
                            onClick={() => handleEditProfile(profile)}
                            color="primary"
                          >
                            <EditIcon />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => handleDeleteProfile(profile.id)}
                            color="error"
                          >
                            <DeleteIcon />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                  {profiles.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} align="center">
                        No application profiles found
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </TabPanel>
      </Paper>

      {/* Customer Dialog */}
      <Dialog open={customerDialogOpen} onClose={() => setCustomerDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingCustomer ? 'Edit Customer' : 'Create Customer'}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Name"
            type="text"
            fullWidth
            required
            value={customerForm.name}
            onChange={(e) => setCustomerForm({ ...customerForm, name: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Email"
            type="email"
            fullWidth
            required
            value={customerForm.contactEmail}
            onChange={(e) => setCustomerForm({ ...customerForm, contactEmail: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Phone"
            type="tel"
            fullWidth
            value={customerForm.contactPhone}
            onChange={(e) => setCustomerForm({ ...customerForm, contactPhone: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCustomerDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveCustomer} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Profile Dialog */}
      <Dialog open={profileDialogOpen} onClose={() => setProfileDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingProfile ? 'Edit Application Profile' : 'Create Application Profile'}</DialogTitle>
        <DialogContent>
          <TextField
            select
            margin="dense"
            label="Customer"
            fullWidth
            required
            disabled={!!editingProfile}
            value={profileForm.customerId}
            onChange={(e) => setProfileForm({ ...profileForm, customerId: e.target.value })}
            SelectProps={{ native: true }}
          >
            <option value="">Select a customer</option>
            {customers.map((customer) => (
              <option key={customer.id} value={customer.id}>
                {customer.name}
              </option>
            ))}
          </TextField>
          <TextField
            margin="dense"
            label="Name"
            type="text"
            fullWidth
            required
            value={profileForm.name}
            onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })}
          />
          <TextField
            select
            margin="dense"
            label="Type"
            fullWidth
            required
            value={profileForm.type}
            onChange={(e) => setProfileForm({ ...profileForm, type: e.target.value })}
            SelectProps={{ native: true }}
          >
            <option value="chatbot">Chatbot</option>
            <option value="rag">RAG System</option>
            <option value="agent">Agentic AI</option>
            <option value="workflow">Workflow</option>
          </TextField>
          <TextField
            margin="dense"
            label="Endpoint URL"
            type="url"
            fullWidth
            required
            value={profileForm.endpoint}
            onChange={(e) => setProfileForm({ ...profileForm, endpoint: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Timeout (seconds)"
            type="number"
            fullWidth
            value={profileForm.timeout}
            onChange={(e) => setProfileForm({ ...profileForm, timeout: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setProfileDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveProfile} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AdminView;
