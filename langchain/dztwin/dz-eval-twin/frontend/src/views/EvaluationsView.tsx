import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  CircularProgress,
  Chip,
  LinearProgress,
} from '@mui/material';
import { Add as AddIcon, PlayArrow as RunIcon } from '@mui/icons-material';
import { EvaluationRun, Dataset, ApplicationProfile } from '../types';
import apiClient from '../services/api';
import { useCustomer } from '../contexts/CustomerContext';

const EvaluationsView: React.FC = () => {
  const { currentCustomer } = useCustomer();
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [profiles, setProfiles] = useState<ApplicationProfile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Run dialog state
  const [runDialogOpen, setRunDialogOpen] = useState(false);
  const [runForm, setRunForm] = useState({
    datasetId: '',
    applicationProfileId: '',
  });

  useEffect(() => {
    if (currentCustomer) {
      loadRuns();
      loadDatasets();
      loadProfiles();
    }
  }, [currentCustomer]);

  const loadRuns = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getEvaluationRuns();
      setRuns(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load evaluation runs');
    } finally {
      setLoading(false);
    }
  };

  const loadDatasets = async () => {
    try {
      const data = await apiClient.getDatasets();
      setDatasets(data);
    } catch (err: any) {
      console.error('Failed to load datasets:', err);
    }
  };

  const loadProfiles = async () => {
    try {
      const data = await apiClient.getApplicationProfiles();
      setProfiles(data);
    } catch (err: any) {
      console.error('Failed to load application profiles:', err);
    }
  };

  const handleStartRun = () => {
    setRunForm({
      datasetId: datasets[0]?.id || '',
      applicationProfileId: profiles[0]?.id || '',
    });
    setRunDialogOpen(true);
  };

  const handleExecuteRun = async () => {
    try {
      setError(null);
      setSuccess(null);
      await apiClient.startEvaluationRun(runForm);
      setRunDialogOpen(false);
      setSuccess('Evaluation run started successfully!');
      loadRuns();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start evaluation run');
    }
  };

  const getStatusColor = (status: string): 'default' | 'primary' | 'success' | 'error' | 'warning' => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'success';
      case 'running':
        return 'primary';
      case 'failed':
        return 'error';
      case 'pending':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getDatasetName = (datasetId: string): string => {
    const dataset = datasets.find((d) => d.id === datasetId);
    return dataset?.name || datasetId;
  };

  const getProfileName = (profileId: string): string => {
    const profile = profiles.find((p) => p.id === profileId);
    return profile?.name || profileId;
  };

  if (!currentCustomer) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom>
          Evaluation Runs
        </Typography>
        <Alert severity="warning">Please select a customer to view evaluation runs.</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Evaluation Runs
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleStartRun}
          disabled={datasets.length === 0 || profiles.length === 0}
        >
          Start Evaluation Run
        </Button>
      </Box>

      {datasets.length === 0 || profiles.length === 0 ? (
        <Paper sx={{ p: 3 }}>
          <Alert severity="info">
            {datasets.length === 0 && profiles.length === 0
              ? 'You need to create at least one dataset and one application profile before starting an evaluation run.'
              : datasets.length === 0
              ? 'You need to create at least one dataset before starting an evaluation run.'
              : 'You need to create at least one application profile before starting an evaluation run.'}
          </Alert>
        </Paper>
      ) : loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
          <CircularProgress />
        </Box>
      ) : runs.length === 0 ? (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            No evaluation runs yet. Start your first evaluation run to test your AI application.
          </Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Status</TableCell>
                <TableCell>Dataset</TableCell>
                <TableCell>Application Profile</TableCell>
                <TableCell>Started</TableCell>
                <TableCell>Duration</TableCell>
                <TableCell>Test Cases</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {runs.map((run) => {
                const duration = run.endTime
                  ? Math.round(
                      (new Date(run.endTime).getTime() - new Date(run.startTime).getTime()) / 1000
                    )
                  : null;

                return (
                  <TableRow key={run.id}>
                    <TableCell>
                      <Chip label={run.status} color={getStatusColor(run.status)} size="small" />
                      {run.status.toLowerCase() === 'running' && (
                        <LinearProgress sx={{ mt: 1 }} />
                      )}
                    </TableCell>
                    <TableCell>{getDatasetName(run.datasetId)}</TableCell>
                    <TableCell>{getProfileName(run.applicationProfileId)}</TableCell>
                    <TableCell>{new Date(run.startTime).toLocaleString()}</TableCell>
                    <TableCell>
                      {duration !== null ? `${duration}s` : run.status === 'running' ? 'In progress...' : '-'}
                    </TableCell>
                    <TableCell>
                      {run.responses.length > 0 ? (
                        <Chip label={run.responses.length} size="small" />
                      ) : (
                        '-'
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Run Dialog */}
      <Dialog open={runDialogOpen} onClose={() => setRunDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <RunIcon sx={{ mr: 1 }} />
            Start Evaluation Run
          </Box>
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Select a dataset and application profile to evaluate. The system will execute all test
            cases in the dataset against the selected application.
          </Typography>
          <TextField
            select
            margin="dense"
            label="Dataset"
            fullWidth
            required
            value={runForm.datasetId}
            onChange={(e) => setRunForm({ ...runForm, datasetId: e.target.value })}
            SelectProps={{ native: true }}
          >
            <option value="">Select a dataset</option>
            {datasets.map((dataset) => (
              <option key={dataset.id} value={dataset.id}>
                {dataset.name} ({dataset.testCases.length} test cases)
              </option>
            ))}
          </TextField>
          <TextField
            select
            margin="dense"
            label="Application Profile"
            fullWidth
            required
            value={runForm.applicationProfileId}
            onChange={(e) => setRunForm({ ...runForm, applicationProfileId: e.target.value })}
            SelectProps={{ native: true }}
          >
            <option value="">Select an application profile</option>
            {profiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.name} ({profile.type})
              </option>
            ))}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRunDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleExecuteRun}
            variant="contained"
            disabled={!runForm.datasetId || !runForm.applicationProfileId}
            startIcon={<RunIcon />}
          >
            Start Run
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default EvaluationsView;
