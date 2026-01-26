import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import { CustomerProvider } from './contexts/CustomerContext';
import Layout from './components/Layout';
import DashboardView from './views/DashboardView';
import AdminView from './views/AdminView';
import DatasetsView from './views/DatasetsView';
import EvaluationsView from './views/EvaluationsView';
import ResultsView from './views/ResultsView';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <CustomerProvider>
        <Router>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<DashboardView />} />
              <Route path="admin" element={<AdminView />} />
              <Route path="datasets" element={<DatasetsView />} />
              <Route path="evaluations" element={<EvaluationsView />} />
              <Route path="results" element={<ResultsView />} />
            </Route>
          </Routes>
        </Router>
      </CustomerProvider>
    </ThemeProvider>
  );
}

export default App;
