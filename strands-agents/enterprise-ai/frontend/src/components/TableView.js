import React from "react";
import { Box, Typography } from "@mui/material";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";

function TableView(props) {
  const { query_results } = props;

  // Validate that query_results is an array and not empty
  if (!Array.isArray(query_results) || query_results.length === 0) {
    return (
      <Box sx={{ textAlign: "center", p: 3 }}>
        <Typography color="text.secondary">
          No Data Records
        </Typography>
      </Box>
    );
  }

  // Check if the first row has valid data structure
  const firstRow = query_results[0];
  if (!firstRow || typeof firstRow !== 'object') {
    return (
      <Box sx={{ textAlign: "center", p: 3 }}>
        <Typography color="text.secondary">
          No Data Records
        </Typography>
      </Box>
    );
  }

  // Get column headers from the first row
  const columns = Object.keys(firstRow);
  if (columns.length === 0) {
    return (
      <Box sx={{ textAlign: "center", p: 3 }}>
        <Typography color="text.secondary">
          No Data Records
        </Typography>
      </Box>
    );
  }

  return (
    <TableContainer sx={{ border: 0, width: "100%" }}>
      <Table
        sx={{
          border: 0,
          boxShadow: "rgba(0, 0, 0, 0.05) 0px 4px 12px",
          borderTopRightRadius: 16,
          borderTopLeftRadius: 16,
          width: "100%",
        }}
        aria-label="query results table"
      >
        <TableHead>
          <TableRow>
            <TableCell sx={{ fontWeight: 'bold' }}>#</TableCell>
            {columns.map((columnName, index) => (
              <TableCell
                key={"header_" + index}
                sx={{ p: 1, pr: 2, fontWeight: 'bold' }}
                align={typeof firstRow[columnName] === "number" ? "right" : "left"}
              >
                {columnName}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>

        <TableBody>
          {query_results.map((row, rowIndex) => (
            <TableRow
              key={"row_" + rowIndex}
              sx={{ "&:last-child td, &:last-child th": { border: 0 } }}
            >
              <TableCell sx={{ p: 1, m: 0, fontWeight: 'bold' }} align="right">
                {rowIndex + 1}
              </TableCell>
              {columns.map((columnName, colIndex) => (
                <TableCell
                  key={"cell_" + rowIndex + "_" + colIndex}
                  sx={{ p: 1, pr: 2, m: 0 }}
                  component={colIndex === 0 ? "th" : ""}
                  scope={colIndex === 0 ? "row" : ""}
                  align={typeof row[columnName] === "number" ? "right" : "left"}
                >
                  {row[columnName] !== null && row[columnName] !== undefined 
                    ? String(row[columnName]) 
                    : '-'}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

export default TableView;
