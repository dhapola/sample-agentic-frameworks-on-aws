import { BrowserRouter as Router } from 'react-router-dom'
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material'

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
})

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <div>
          <h1>Gen AI Evaluation Platform</h1>
          <p>Frontend application is ready. Components will be added in subsequent tasks.</p>
        </div>
      </Router>
    </ThemeProvider>
  )
}

export default App
