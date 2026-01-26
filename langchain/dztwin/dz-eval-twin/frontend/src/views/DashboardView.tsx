import React from 'react';
import { Box, Typography, Paper } from '@mui/material';

const DashboardView: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      <Paper sx={{ p: 3, mt: 2 }}>
        <Typography variant="body1">
          Overview of recent evaluation runs and summary statistics will be displayed here.
        </Typography>
      </Paper>
    </Box>
  );
};

export default DashboardView;
