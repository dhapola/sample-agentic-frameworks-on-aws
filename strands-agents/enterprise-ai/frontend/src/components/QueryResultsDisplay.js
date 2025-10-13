import React from "react";
import { Box, Typography } from "@mui/material";
import TableView from "./TableView";

const QueryResultsDisplay = ({ index, answer }) => {
  // Check multiple possible property names for query results
  const queryResults = answer.queryResults || answer.query_results || answer.results || answer.data;
  
  if (!queryResults) {
    return (
      <Box sx={{ textAlign: "center", p: 3 }}>
        <Typography color="text.secondary">
          No Data Records
        </Typography>
      </Box>
    );
  }

  if (!Array.isArray(queryResults)) {
    return (
      <Box sx={{ textAlign: "center", p: 3 }}>
        <Typography color="text.secondary">
          No Data Records
        </Typography>
      </Box>
    );
  }

  if (queryResults.length === 0) {
    return (
      <Box sx={{ textAlign: "center", p: 3 }}>
        <Typography color="text.secondary">
          No Data Records
        </Typography>
      </Box>
    );
  }
  
  return (
    <Box>
      <Box key={"table_" + index}>
        <TableView query_results={queryResults} />
      </Box>
    </Box>
  );
};

export default QueryResultsDisplay;
