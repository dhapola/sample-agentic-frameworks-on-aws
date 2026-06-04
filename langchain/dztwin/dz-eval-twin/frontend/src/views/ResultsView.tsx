import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Alert,
  CircularProgress,
  Chip,
  Card,
  CardContent,
  Grid,
  Divider,
  List,
  ListItem,
  ListItemText,
  TextField,
  MenuItem,
} from '@mui/material';
import {
  Visibility as ViewIcon,
  ArrowBack as BackIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { EvaluationRun, Dataset, ApplicationProfile } from '../types';
import apiClient from '../services/api';
import { useCustomer } from '../contexts/CustomerContext';

const ResultsView: React.FC = () => {
  const { currentCustomer, isReady } = useCustomer();
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<EvaluationRun | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [profiles, setProfiles] = useState<ApplicationProfile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<string>('startTime');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  useEffect(() => {
    if (currentCustomer && isReady) {
      loadRuns();
      loadDatasets();
      loadProfiles();
    }
  }, [currentCustomer, isReady]);

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

  const handleViewRun = async (runId: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getEvaluationRun(runId);
      setSelectedRun(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load run details');
    } finally {
      setLoading(false);
    }
  };

  const handleBackToList = () => {
    setSelectedRun(null);
  };

  const getDatasetName = (datasetId: string): string => {
    const dataset = datasets.find((d) => d.id === datasetId);
    return dataset?.name || datasetId;
  };

  const getProfileName = (profileId: string): string => {
    const profile = profiles.find((p) => p.id === profileId);
    return profile?.name || profileId;
  };

  const getFilteredAndSortedRuns = () => {
    let filtered = runs;

    // Filter by status
    if (filterStatus !== 'all') {
      filtered = filtered.filter((run) => run.status.toLowerCase() === filterStatus);
    }

    // Sort
    const sorted = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'startTime':
          return new Date(b.startTime).getTime() - new Date(a.startTime).getTime();
        case 'status':
          return a.status.localeCompare(b.status);
        case 'dataset':
          return getDatasetName(a.datasetId).localeCompare(getDatasetName(b.datasetId));
        default:
          return 0;
      }
    });

    return sorted;
  };

  if (!currentCustomer) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom>
          Results Dashboard
        </Typography>
        <Alert severity="warning">Please select a customer to view results.</Alert>
      </Box>
    );
  }

  // Detail view
  if (selectedRun) {
    const successCount = selectedRun.responses.filter((r) => !r.error).length;

    // Prepare chart data
    const latencyData = selectedRun.responses.map((response, index) => ({
      name: `TC ${index + 1}`,
      latency: response.latency,
    }));

    const metricsData = selectedRun.responses
      .filter((r) => r.individualMetrics)
      .map((response, index) => ({
        name: `TC ${index + 1}`,
        accuracy: response.individualMetrics?.accuracy || 0,
        relevance: response.individualMetrics?.relevance || 0,
      }));

    return (
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <IconButton onClick={handleBackToList} sx={{ mr: 2 }}>
            <BackIcon />
          </IconButton>
          <Typography variant="h4" sx={{ flexGrow: 1 }}>
            Run Details
          </Typography>
          <Chip label={selectedRun.status} color="primary" />
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Summary Cards */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Dataset
                </Typography>
                <Typography variant="h6">{getDatasetName(selectedRun.datasetId)}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Application
                </Typography>
                <Typography variant="h6">{getProfileName(selectedRun.applicationProfileId)}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Success Rate
                </Typography>
                <Typography variant="h6">
                  {selectedRun.metrics
                    ? `${(selectedRun.metrics.successRate * 100).toFixed(1)}%`
                    : 'N/A'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Avg Latency
                </Typography>
                <Typography variant="h6">
                  {selectedRun.metrics ? `${selectedRun.metrics.averageLatency.toFixed(0)}ms` : 'N/A'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Metrics Overview */}
        {selectedRun.metrics && (
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Metrics Overview
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Typography variant="body2" color="text.secondary">
                  Average Accuracy
                </Typography>
                <Typography variant="h6">
                  {(selectedRun.metrics.averageAccuracy * 100).toFixed(1)}%
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="body2" color="text.secondary">
                  Average Relevance
                </Typography>
                <Typography variant="h6">
                  {(selectedRun.metrics.averageRelevance * 100).toFixed(1)}%
                </Typography>
              </Grid>
              <Grid item xs={12} md={4}>
                <Typography variant="body2" color="text.secondary">
                  Median Latency
                </Typography>
                <Typography variant="h6">{selectedRun.metrics.medianLatency.toFixed(0)}ms</Typography>
              </Grid>
              <Grid item xs={12} md={4}>
                <Typography variant="body2" color="text.secondary">
                  P95 Latency
                </Typography>
                <Typography variant="h6">{selectedRun.metrics.p95Latency.toFixed(0)}ms</Typography>
              </Grid>
              <Grid item xs={12} md={4}>
                <Typography variant="body2" color="text.secondary">
                  Test Cases
                </Typography>
                <Typography variant="h6">
                  {successCount} / {selectedRun.metrics.totalTestCases}
                </Typography>
              </Grid>
            </Grid>
          </Paper>
        )}

        {/* Charts */}
        {selectedRun.responses.length > 0 && (
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Latency by Test Case
                </Typography>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={latencyData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis label={{ value: 'ms', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Bar dataKey="latency" fill="#1976d2" />
                  </BarChart>
                </ResponsiveContainer>
              </Paper>
            </Grid>
            {metricsData.length > 0 && (
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Accuracy & Relevance
                  </Typography>
                  <ResponsiveContainer width="100%" height={250}>
                    <LineChart data={metricsData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis domain={[0, 1]} />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="accuracy" stroke="#4caf50" />
                      <Line type="monotone" dataKey="relevance" stroke="#ff9800" />
                    </LineChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid>
            )}
          </Grid>
        )}

        {/* Responses List */}
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Test Case Results ({selectedRun.responses.length})
          </Typography>
          <List>
            {selectedRun.responses.map((response, index) => (
              <React.Fragment key={response.testCaseId}>
                {index > 0 && <Divider />}
                <ListItem>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        {response.error ? (
                          <ErrorIcon color="error" sx={{ mr: 1 }} />
                        ) : (
                          <SuccessIcon color="success" sx={{ mr: 1 }} />
                        )}
                        <Typography variant="subtitle1">Test Case {index + 1}</Typography>
                        <Chip
                          label={`${response.latency.toFixed(0)}ms`}
                          size="small"
                          sx={{ ml: 2 }}
                        />
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                          <strong>Input:</strong> {response.input}
                        </Typography>
                        {response.error ? (
                          <Typography variant="body2" color="error" sx={{ mt: 1 }}>
                            <strong>Error:</strong> {response.error}
                          </Typography>
                        ) : (
                          <Typography variant="body2" sx={{ mt: 1 }}>
                            <strong>Output:</strong> {response.output}
                          </Typography>
                        )}
                        {response.individualMetrics && (
                          <Box sx={{ mt: 1 }}>
                            <Chip
                              label={`Accuracy: ${(response.individualMetrics.accuracy! * 100).toFixed(1)}%`}
                              size="small"
                              sx={{ mr: 1 }}
                            />
                            <Chip
                              label={`Relevance: ${(response.individualMetrics.relevance! * 100).toFixed(1)}%`}
                              size="small"
                            />
                          </Box>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
              </React.Fragment>
            ))}
          </List>
        </Paper>
      </Box>
    );
  }

  // List view
  const filteredRuns = getFilteredAndSortedRuns();

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Results Dashboard
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Filters and Sorting */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <TextField
              select
              fullWidth
              label="Filter by Status"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <MenuItem value="all">All Statuses</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
              <MenuItem value="running">Running</MenuItem>
              <MenuItem value="failed">Failed</MenuItem>
              <MenuItem value="pending">Pending</MenuItem>
            </TextField>
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              select
              fullWidth
              label="Sort by"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <MenuItem value="startTime">Start Time (Newest First)</MenuItem>
              <MenuItem value="status">Status</MenuItem>
              <MenuItem value="dataset">Dataset Name</MenuItem>
            </TextField>
          </Grid>
        </Grid>
      </Paper>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
          <CircularProgress />
        </Box>
      ) : filteredRuns.length === 0 ? (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            {runs.length === 0
              ? 'No evaluation runs yet. Start an evaluation run to see results here.'
              : 'No runs match the selected filters.'}
          </Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Status</TableCell>
                <TableCell>Dataset</TableCell>
                <TableCell>Application</TableCell>
                <TableCell>Started</TableCell>
                <TableCell>Success Rate</TableCell>
                <TableCell>Avg Latency</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredRuns.map((run) => (
                <TableRow key={run.id}>
                  <TableCell>
                    <Chip label={run.status} color="primary" size="small" />
                  </TableCell>
                  <TableCell>{getDatasetName(run.datasetId)}</TableCell>
                  <TableCell>{getProfileName(run.applicationProfileId)}</TableCell>
                  <TableCell>{new Date(run.startTime).toLocaleString()}</TableCell>
                  <TableCell>
                    {run.metrics ? `${(run.metrics.successRate * 100).toFixed(1)}%` : '-'}
                  </TableCell>
                  <TableCell>
                    {run.metrics ? `${run.metrics.averageLatency.toFixed(0)}ms` : '-'}
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => handleViewRun(run.id)}
                      color="primary"
                    >
                      <ViewIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default ResultsView;
