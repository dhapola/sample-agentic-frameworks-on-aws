import React, { useEffect, useRef } from 'react';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Fade from '@mui/material/Fade';
import PsychologyRoundedIcon from '@mui/icons-material/PsychologyRounded';

const ThoughtsDisplay = ({ thoughts, visible }) => {
  // Create a ref for the container element
  const thoughtsContainerRef = useRef(null);
  

// console.log('updatedThoughts =>' + updatedThoughts);
//             updatedThoughts = updatedThoughts.replace(/<\/?thinking>/g, "");

  // Combine all thought contents into a single string
  const combinedThoughts = thoughts
    .map(thought => thought.content)
    .join('');
  
  // Auto-scroll to bottom when thoughts are updated
  useEffect(() => {
    if (thoughtsContainerRef.current && visible) {
      const container = thoughtsContainerRef.current;
      container.scrollTop = container.scrollHeight;
    }
  }, [thoughts, visible]); // Re-run when thoughts or visibility changes
    
  return (
    <Fade in={visible} timeout={500}>
      <Paper 
        elevation={1}
        ref={thoughtsContainerRef}
        sx={{
          p: 2,
          mb: 2,
          borderRadius: 2,
          backgroundColor: 'rgba(0, 0, 0, 0.03)',
          borderLeft: '4px solid #A4E9DB',
          maxHeight: '200px',
          overflow: 'auto'
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <PsychologyRoundedIcon sx={{ mr: 1, color: 'text.secondary' }} />
          <Typography variant="subtitle2" color="text.secondary">
            Thinking...
          </Typography>
        </Box>
        <Box>
          <Typography 
            variant="body2" 
            color="text.secondary"
            sx={{ 
              fontFamily: 'monospace', 
              whiteSpace: 'pre-wrap'
            }}
          >
            {combinedThoughts}
          </Typography>
        </Box>
      </Paper>
    </Fade>
  );
};

export default ThoughtsDisplay;
