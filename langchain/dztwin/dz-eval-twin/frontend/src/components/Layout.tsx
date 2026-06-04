import React, { useState, useEffect } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  AppBar,
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Container,
  Switch,
  FormControlLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  AdminPanelSettings as AdminIcon,
  Storage as DatasetIcon,
  PlayArrow as EvaluationIcon,
  Assessment as ResultsIcon,
} from '@mui/icons-material';
import { useCustomer } from '../contexts/CustomerContext';
import { Customer } from '../types';
import apiClient from '../services/api';

const drawerWidth = 240;

const Layout: React.FC = () => {
  const location = useLocation();
  const { currentCustomer, setCurrentCustomer, isAdmin, setIsAdmin } = useCustomer();
  const [authDialogOpen, setAuthDialogOpen] = useState(false);
  const [adminPassword, setAdminPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [customers, setCustomers] = useState<Customer[]>([]);

  // Load customers on mount
  useEffect(() => {
    loadCustomers();
  }, []);

  const loadCustomers = async () => {
    try {
      const data = await apiClient.getCustomers();
      setCustomers(data);
    } catch (err) {
      console.error('Failed to load customers:', err);
    }
  };

  // Simple admin credentials (in production, use proper authentication)
  const ADMIN_PASSWORD = 'admin123';

  const handleAdminToggle = (checked: boolean) => {
    if (checked) {
      // Show auth dialog when enabling admin mode
      setAuthDialogOpen(true);
      setAdminPassword('');
      setAuthError('');
    } else {
      // Disable admin mode directly
      setIsAdmin(false);
    }
  };

  const handleAdminAuth = () => {
    if (adminPassword === ADMIN_PASSWORD) {
      setIsAdmin(true);
      setAuthDialogOpen(false);
      setAdminPassword('');
      setAuthError('');
    } else {
      setAuthError('Invalid admin password');
    }
  };

  const handleAuthCancel = () => {
    setAuthDialogOpen(false);
    setAdminPassword('');
    setAuthError('');
  };

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/' },
    ...(isAdmin ? [{ text: 'Admin', icon: <AdminIcon />, path: '/admin' }] : []),
    { text: 'Datasets', icon: <DatasetIcon />, path: '/datasets' },
    { text: 'Evaluations', icon: <EvaluationIcon />, path: '/evaluations' },
    { text: 'Results', icon: <ResultsIcon />, path: '/results' },
  ];

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}
      >
        <Toolbar variant="dense" sx={{ minHeight: 48 }}>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Gen AI Evaluation Platform
          </Typography>
          
          {/* Customer Selector */}
          {!isAdmin && customers.length > 0 && (
            <FormControl sx={{ minWidth: 200, mr: 2 }} size="small">
              <InputLabel sx={{ color: 'white' }}>Customer</InputLabel>
              <Select
                value={currentCustomer?.id || ''}
                onChange={(e) => {
                  const customer = customers.find(c => c.id === e.target.value);
                  setCurrentCustomer(customer || null);
                }}
                label="Customer"
                displayEmpty
                sx={{ bgcolor: 'white' }}
              >
                <MenuItem value="">
                  <em>Select Customer</em>
                </MenuItem>
                {customers.map((customer) => (
                  <MenuItem key={customer.id} value={customer.id}>
                    {customer.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
          
          <FormControlLabel
            control={
              <Switch
                checked={isAdmin}
                onChange={(e) => handleAdminToggle(e.target.checked)}
                color="secondary"
              />
            }
            label="Admin Mode"
            sx={{ mr: 2 }}
          />
          {currentCustomer && isAdmin && (
            <Typography variant="body2">
              Customer: {currentCustomer.name}
            </Typography>
          )}
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto' }}>
          <List>
            {menuItems.map((item) => (
              <ListItem key={item.text} disablePadding>
                <ListItemButton
                  component={Link}
                  to={item.path}
                  selected={location.pathname === item.path}
                >
                  <ListItemIcon>{item.icon}</ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          bgcolor: 'background.default',
          p: 3,
        }}
      >
        <Toolbar />
        <Container maxWidth="xl">
          <Outlet />
        </Container>
      </Box>

      {/* Admin Authentication Dialog */}
      <Dialog open={authDialogOpen} onClose={handleAuthCancel}>
        <DialogTitle>Admin Authentication</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Enter admin password to enable admin mode
          </Typography>
          {authError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {authError}
            </Alert>
          )}
          <TextField
            autoFocus
            margin="dense"
            label="Admin Password"
            type="password"
            fullWidth
            value={adminPassword}
            onChange={(e) => setAdminPassword(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleAdminAuth();
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleAuthCancel}>Cancel</Button>
          <Button onClick={handleAdminAuth} variant="contained">
            Authenticate
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Layout;
