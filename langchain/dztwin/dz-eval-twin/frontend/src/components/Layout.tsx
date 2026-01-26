import React from 'react';
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
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  AdminPanelSettings as AdminIcon,
  Storage as DatasetIcon,
  PlayArrow as EvaluationIcon,
  Assessment as ResultsIcon,
} from '@mui/icons-material';
import { useCustomer } from '../contexts/CustomerContext';

const drawerWidth = 240;

const Layout: React.FC = () => {
  const location = useLocation();
  const { currentCustomer, isAdmin } = useCustomer();

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
        <Toolbar>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Gen AI Evaluation Platform
          </Typography>
          {currentCustomer && (
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
    </Box>
  );
};

export default Layout;
