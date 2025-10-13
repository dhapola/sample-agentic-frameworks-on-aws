import React, { useState, useEffect, useRef } from "react";
import {
  Box,
  FormControl,
  Select,
  MenuItem,
  CircularProgress,
  Typography,
} from "@mui/material";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import { getModels } from "../utils/ApiCalls";

function ModelSelector({ selectedModel, onModelChange }) {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const fetchedRef = useRef(false);

  useEffect(() => {
    // Only fetch once, even in StrictMode which runs effects twice
    if (fetchedRef.current) return;

    setLoading(true);

    const loadModels = async () => {
      // Fetch models from the backend API
      const modelsList = await getModels();
      
      try {
        setModels(modelsList);
        // If the currently selected model is not in the list, select the first one
        if (
          modelsList.length > 0 &&
          !modelsList.some((model) => model.id === selectedModel)
        ) {
          // Use a timeout to avoid React warning about state updates during render
          setTimeout(() => {
            onModelChange(modelsList[0].id);
          }, 0);
        }
      } catch (error) {
        setError(error.message);
        setModels([
          {
            id: "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            name: "Claude 3.7 Sonnet",
            provider: "Anthropic",
          },
          {
            id: "claude-3-5-sonnet",
            name: "Claude 3.5 Sonnet",
            provider: "Anthropic",
          },
          {
            id: "claude-3-haiku",
            name: "Claude 3 Haiku",
            provider: "Anthropic",
          },
          { id: "claude-3-opus", name: "Claude 3 Opus", provider: "Anthropic" },
          {
            id: "meta.llama3-70b-instruct-v1:0",
            name: "Llama 3 70B Instruct",
            provider: "Meta",
          },
        ]);
      } finally {
        setLoading(false);
        fetchedRef.current = true;
      }
      
    };
    loadModels();
  }, []); // Remove dependencies to prevent multiple API calls

  // Find the currently selected model name
  var selectedModelName = selectedModel;
  if (models && models.length > 0)
    selectedModelName = models.find(
      (model) => model.id === selectedModel
    )?.name;

  return (
    <Box sx={{ minWidth: 200 }}>
      <FormControl fullWidth size="small">
        {loading ? (
          <Box sx={{ display: "flex", alignItems: "center", color: "#351c75" }}>
            <CircularProgress size={20} sx={{ color: "#351c75", mr: 1 }} />
            Loading models...
          </Box>
        ) : (
          <Select
            labelId="model-select-label"
            id="model-select"
            value={selectedModel}
            onChange={(e) => onModelChange(e.target.value)}
            IconComponent={KeyboardArrowDownIcon}
            displayEmpty
            renderValue={() => (
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <Typography
                  variant="body1"
                  sx={{ color: "#351c75", fontWeight: 500 }}
                >
                  {selectedModelName}
                </Typography>
              </Box>
            )}
            MenuProps={{
              sx: {
                zIndex: 9999, // Ensure dropdown appears above other elements
              },
            }}
            sx={{
              backgroundColor: "white",
              borderRadius: 1,
              padding: "0px 5px", // Reduced vertical padding
              "& .MuiOutlinedInput-notchedOutline": {
                border: "none", // Remove border
              },
              "&:hover .MuiOutlinedInput-notchedOutline": {
                border: "none", // Remove border on hover
              },
              "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
                border: "none", // Remove border when focused
              },
              "& .MuiSvgIcon-root": {
                color: "#351c75",
                fontSize: "1.2rem", // Make arrow icon slightly smaller
              },
            }}
          >
            {models.map((model) => (
              <MenuItem key={model.id} value={model.id}>
                {model.name}
              </MenuItem>
            ))}
          </Select>
        )}
      </FormControl>
      {error && (
        <Box sx={{ color: "error.main", mt: 1, fontSize: "0.75rem" }}>
          Error loading models. Using default list.
        </Box>
      )}
    </Box>
  );
}

export default ModelSelector;
