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
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  CircularProgress,
  Chip,
  Card,
  CardContent,
  Divider,
  List,
  ListItem,
  ListItemText,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  FormHelperText,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Visibility as ViewIcon,
  ArrowBack as BackIcon,
  CloudUpload as UploadIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
import { Dataset, TestCase, ApplicationProfile } from '../types';
import apiClient from '../services/api';
import { useCustomer } from '../contexts/CustomerContext';

const DatasetsView: React.FC = () => {
  const { currentCustomer, isReady } = useCustomer();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [applicationProfiles, setApplicationProfiles] = useState<ApplicationProfile[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Dataset dialog state
  const [datasetDialogOpen, setDatasetDialogOpen] = useState(false);
  const [editingDataset, setEditingDataset] = useState<Dataset | null>(null);
  const [datasetForm, setDatasetForm] = useState({
    applicationProfileId: '',
    name: '',
    description: '',
    file: null as File | null,
  });
  const [fileError, setFileError] = useState<string | null>(null);

  // Test case dialog state
  const [testCaseDialogOpen, setTestCaseDialogOpen] = useState(false);
  const [editingTestCase, setEditingTestCase] = useState<TestCase | null>(null);
  const [testCaseForm, setTestCaseForm] = useState({
    input: '',
    expectedOutput: '',
  });

  useEffect(() => {
    if (currentCustomer && isReady) {
      loadDatasets();
      loadApplicationProfiles();
    }
  }, [currentCustomer, isReady]);

  const loadApplicationProfiles = async () => {
    if (!currentCustomer) return;
    try {
      const data = await apiClient.getApplicationProfiles(currentCustomer.id);
      setApplicationProfiles(data);
    } catch (err: any) {
      console.error('Failed to load application profiles:', err);
    }
  };

  const loadDatasets = async () => {
    if (!currentCustomer) {
      return; // Don't load if no customer selected
    }
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getDatasets();
      setDatasets(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load datasets');
    } finally {
      setLoading(false);
    }
  };

  const loadDatasetDetails = async (id: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getDataset(id);
      setSelectedDataset(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load dataset details');
    } finally {
      setLoading(false);
    }
  };

  // Dataset handlers
  const handleCreateDataset = () => {
    setEditingDataset(null);
    setDatasetForm({ 
      applicationProfileId: '',
      name: '', 
      description: '',
      file: null,
    });
    setFileError(null);
    setDatasetDialogOpen(true);
  };

  const handleEditDataset = (dataset: Dataset) => {
    setEditingDataset(dataset);
    setDatasetForm({
      applicationProfileId: dataset.applicationProfileId,
      name: dataset.name,
      description: dataset.description,
      file: null, // Can't pre-populate file input
    });
    setFileError(null);
    setDatasetDialogOpen(true);
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    setFileError(null);
    
    if (file) {
      // Validate file type
      if (!file.name.endsWith('.csv')) {
        setFileError('Please select a CSV file');
        return;
      }
      
      // Validate file size (10MB max)
      const maxSize = 10 * 1024 * 1024; // 10MB in bytes
      if (file.size > maxSize) {
        setFileError('File size must be less than 10MB');
        return;
      }
      
      setDatasetForm({ ...datasetForm, file });
    }
  };

  const handleSaveDataset = async () => {
    try {
      setError(null);
      setFileError(null);
      
      if (editingDataset) {
        // Update existing dataset (metadata only)
        await apiClient.updateDataset(editingDataset.id, {
          name: datasetForm.name,
          description: datasetForm.description,
        });
      } else {
        // Create new dataset with file upload
        if (!datasetForm.file) {
          setFileError('Please select a CSV file');
          return;
        }
        
        if (!datasetForm.applicationProfileId) {
          setError('Please select an application profile');
          return;
        }
        
        const formData = new FormData();
        formData.append('applicationProfileId', datasetForm.applicationProfileId);
        formData.append('name', datasetForm.name);
        formData.append('description', datasetForm.description);
        formData.append('file', datasetForm.file);
        
        await apiClient.createDatasetWithFile(formData);
      }
      
      setDatasetDialogOpen(false);
      loadDatasets();
      if (selectedDataset && editingDataset?.id === selectedDataset.id) {
        loadDatasetDetails(selectedDataset.id);
      }
    } catch (err: any) {
      setError(err.response?.data?.error?.message || err.response?.data?.detail || 'Failed to save dataset');
    }
  };

  const handleDownloadFile = async (datasetId: string) => {
    try {
      const blob = await apiClient.downloadDatasetFile(datasetId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `dataset_${datasetId}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      setError(err.response?.data?.error?.message || 'Failed to download file');
    }
  };

  const handleDeleteDataset = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this dataset?')) return;
    try {
      setError(null);
      await apiClient.deleteDataset(id);
      if (selectedDataset?.id === id) {
        setSelectedDataset(null);
      }
      loadDatasets();
    } catch (err: any) {
      setError(err.response?.data?.error?.message || err.response?.data?.detail || 'Failed to delete dataset');
    }
  };

  const handleViewDataset = (dataset: Dataset) => {
    setSelectedDataset(dataset);
  };

  const handleBackToList = () => {
    setSelectedDataset(null);
  };

  // Test case handlers
  const handleCreateTestCase = () => {
    setEditingTestCase(null);
    setTestCaseForm({ input: '', expectedOutput: '' });
    setTestCaseDialogOpen(true);
  };

  const handleEditTestCase = (testCase: TestCase) => {
    setEditingTestCase(testCase);
    setTestCaseForm({
      input: testCase.input,
      expectedOutput: testCase.expectedOutput || '',
    });
    setTestCaseDialogOpen(true);
  };

  const handleSaveTestCase = async () => {
    if (!selectedDataset) return;
    try {
      setError(null);
      if (editingTestCase) {
        await apiClient.updateTestCase(selectedDataset.id, editingTestCase.id, testCaseForm);
      } else {
        await apiClient.addTestCase(selectedDataset.id, testCaseForm);
      }
      setTestCaseDialogOpen(false);
      loadDatasetDetails(selectedDataset.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save test case');
    }
  };

  const handleDeleteTestCase = async (testCaseId: string) => {
    if (!selectedDataset) return;
    if (!window.confirm('Are you sure you want to delete this test case?')) return;
    try {
      setError(null);
      await apiClient.deleteTestCase(selectedDataset.id, testCaseId);
      loadDatasetDetails(selectedDataset.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete test case');
    }
  };

  if (!currentCustomer) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom>
          Datasets
        </Typography>
        <Alert severity="warning">Please select a customer to view datasets.</Alert>
      </Box>
    );
  }

  // Detail view
  if (selectedDataset) {
    return (
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <IconButton onClick={handleBackToList} sx={{ mr: 2 }}>
            <BackIcon />
          </IconButton>
          <Typography variant="h4" sx={{ flexGrow: 1 }}>
            {selectedDataset.name}
          </Typography>
          <Button
            variant="outlined"
            startIcon={<EditIcon />}
            onClick={() => handleEditDataset(selectedDataset)}
            sx={{ mr: 1 }}
          >
            Edit
          </Button>
          <Button
            variant="outlined"
            color="error"
            startIcon={<DeleteIcon />}
            onClick={() => handleDeleteDataset(selectedDataset.id)}
          >
            Delete
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Description
            </Typography>
            <Typography variant="body1" paragraph>
              {selectedDataset.description}
            </Typography>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                Test Cases: {selectedDataset.testCases?.length || 0}
              </Typography>
              <Button
                variant="outlined"
                size="small"
                startIcon={<DownloadIcon />}
                onClick={() => handleDownloadFile(selectedDataset.id)}
              >
                Download CSV
              </Button>
            </Box>
          </CardContent>
        </Card>

        <Paper sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6">Test Cases</Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleCreateTestCase}
            >
              Add Test Case
            </Button>
          </Box>

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : (selectedDataset.testCases?.length || 0) === 0 ? (
            <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 3 }}>
              No test cases yet. Add your first test case to get started.
            </Typography>
          ) : (
            <List>
              {(selectedDataset.testCases || []).map((testCase, index) => (
                <React.Fragment key={testCase.id}>
                  {index > 0 && <Divider />}
                  <ListItem
                    secondaryAction={
                      <Box>
                        <IconButton
                          edge="end"
                          onClick={() => handleEditTestCase(testCase)}
                          sx={{ mr: 1 }}
                        >
                          <EditIcon />
                        </IconButton>
                        <IconButton
                          edge="end"
                          onClick={() => handleDeleteTestCase(testCase.id)}
                          color="error"
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Box>
                    }
                  >
                    <ListItemText
                      primary={
                        <Box>
                          <Typography variant="subtitle2" color="text.secondary">
                            Input:
                          </Typography>
                          <Typography variant="body1" sx={{ mb: 1 }}>
                            {testCase.input}
                          </Typography>
                          {testCase.expectedOutput && (
                            <>
                              <Typography variant="subtitle2" color="text.secondary">
                                Expected Output:
                              </Typography>
                              <Typography variant="body1">{testCase.expectedOutput}</Typography>
                            </>
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                </React.Fragment>
              ))}
            </List>
          )}
        </Paper>

        {/* Test Case Dialog */}
        <Dialog open={testCaseDialogOpen} onClose={() => setTestCaseDialogOpen(false)} maxWidth="md" fullWidth>
          <DialogTitle>{editingTestCase ? 'Edit Test Case' : 'Create Test Case'}</DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              margin="dense"
              label="Input"
              type="text"
              fullWidth
              required
              multiline
              rows={3}
              value={testCaseForm.input}
              onChange={(e) => setTestCaseForm({ ...testCaseForm, input: e.target.value })}
            />
            <TextField
              margin="dense"
              label="Expected Output (optional)"
              type="text"
              fullWidth
              multiline
              rows={3}
              value={testCaseForm.expectedOutput}
              onChange={(e) => setTestCaseForm({ ...testCaseForm, expectedOutput: e.target.value })}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setTestCaseDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSaveTestCase} variant="contained">
              Save
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    );
  }

  // List view
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Datasets
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleCreateDataset}
        >
          Create Dataset
        </Button>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
          <CircularProgress />
        </Box>
      ) : datasets.length === 0 ? (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            No datasets found. Create your first dataset to get started.
          </Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Description</TableCell>
                <TableCell>Test Cases</TableCell>
                <TableCell>Created</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {datasets.map((dataset) => (
                <TableRow key={dataset.id}>
                  <TableCell>{dataset.name}</TableCell>
                  <TableCell>{dataset.description}</TableCell>
                  <TableCell>
                    <Chip label={dataset.testCases?.length || 0} size="small" />
                  </TableCell>
                  <TableCell>{new Date(dataset.createdAt).toLocaleDateString()}</TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => handleViewDataset(dataset)}
                      color="primary"
                    >
                      <ViewIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleEditDataset(dataset)}
                      color="primary"
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleDeleteDataset(dataset.id)}
                      color="error"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Dataset Dialog */}
      <Dialog open={datasetDialogOpen} onClose={() => setDatasetDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingDataset ? 'Edit Dataset' : 'Create Dataset'}</DialogTitle>
        <DialogContent>
          {!editingDataset && (
            <FormControl fullWidth margin="dense" required>
              <InputLabel>Application Profile</InputLabel>
              <Select
                value={datasetForm.applicationProfileId}
                label="Application Profile"
                onChange={(e) => setDatasetForm({ ...datasetForm, applicationProfileId: e.target.value })}
              >
                {applicationProfiles.map((profile) => (
                  <MenuItem key={profile.id} value={profile.id}>
                    {profile.name} ({profile.type})
                  </MenuItem>
                ))}
              </Select>
              <FormHelperText>Select the application this dataset will evaluate</FormHelperText>
            </FormControl>
          )}
          
          <TextField
            autoFocus
            margin="dense"
            label="Name"
            type="text"
            fullWidth
            required
            value={datasetForm.name}
            onChange={(e) => setDatasetForm({ ...datasetForm, name: e.target.value })}
          />
          
          <TextField
            margin="dense"
            label="Description"
            type="text"
            fullWidth
            required
            multiline
            rows={3}
            value={datasetForm.description}
            onChange={(e) => setDatasetForm({ ...datasetForm, description: e.target.value })}
          />
          
          {!editingDataset && (
            <Box sx={{ mt: 2 }}>
              <Button
                variant="outlined"
                component="label"
                startIcon={<UploadIcon />}
                fullWidth
                sx={{ mb: 1 }}
              >
                {datasetForm.file ? datasetForm.file.name : 'Upload CSV File'}
                <input
                  type="file"
                  hidden
                  accept=".csv"
                  onChange={handleFileChange}
                />
              </Button>
              <FormHelperText>
                CSV format: Required column 'input', optional 'expected_output' and metadata columns
              </FormHelperText>
              {fileError && (
                <Alert severity="error" sx={{ mt: 1 }}>
                  {fileError}
                </Alert>
              )}
            </Box>
          )}
          
          {editingDataset && (
            <Alert severity="info" sx={{ mt: 2 }}>
              To update test cases, please upload a new CSV file by creating a new dataset.
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDatasetDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveDataset} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DatasetsView;
