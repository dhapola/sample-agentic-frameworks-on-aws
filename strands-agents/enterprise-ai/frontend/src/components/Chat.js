import React, { useLayoutEffect, useRef, useEffect } from "react";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import SendIcon from "@mui/icons-material/Send";
import RefreshIcon from "@mui/icons-material/Refresh";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import Paper from "@mui/material/Paper";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid";
import InputBase from "@mui/material/InputBase";
import Divider from "@mui/material/Divider";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import Button from "@mui/material/Button";
import Grow from "@mui/material/Grow";
import Fade from "@mui/material/Fade";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import QuestionAnswerOutlinedIcon from "@mui/icons-material/QuestionAnswerOutlined";
import TableRowsRoundedIcon from "@mui/icons-material/TableRowsRounded";
import {
  WELCOME_MESSAGE,
  MAX_LENGTH_INPUT_SEARCH,
  APP_NAME,
} from "../env";
import MyChart from "./MyChart.js";
import Answering from "./Answering.js";
import ThoughtsDisplay from "./ThoughtsDisplay.js";
import QueryResultsDisplay from "./QueryResultsDisplay";


import { invokeStreamingApi, generateChartApi } from "../utils/ApiCalls";
import { getThread, getInsights } from "../utils/ApiCalls.js";
import { exportToPdf } from "../utils/pdfExport";
import MarkdownRenderer from "./MarkdownRenderer.js";

const Chat = ({
  userName = "Deepesh",
  chatId,
  selectedModel,
  onStartTyping = () => {},
  hideContent = false,
  onThreadUpdate = () => {},
}) => {
  
  const [enabled, setEnabled] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [loadingThread, setLoadingThread] = React.useState(false);
  const [controlAnswers, setControlAnswers] = React.useState([]);
  const [answers, setAnswers] = React.useState([]);
  const [query, setQuery] = React.useState("");
  const [errorMessage, setErrorMessage] = React.useState("");
  const [height, setHeight] = React.useState(480);
  const [thoughts, setThoughts] = React.useState([]);
  const [showThoughts, setShowThoughts] = React.useState(false);
  const [threadId, setThreadId] = React.useState("");
  const [isFirstMessage, setIsFirstMessage] = React.useState(false);

  const borderRadius = 2;

  const scrollRef = useRef(null);
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [answers]);

  useLayoutEffect(() => {
    function updateSize() {
      
      const myh = window.innerHeight - 150;
      if (myh < 346) {
        setHeight(346);
      } else {
        setHeight(myh);
      }
    }
    window.addEventListener("resize", updateSize);
    updateSize();
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  // Fetch thread data when chatId changes
  useEffect(() => {
    
    const loadThreadData = async () => {
      if (!chatId) return;

      try {
        setLoadingThread(true);
        setErrorMessage("");

        // check if it's new thread. if yes then don't need to fetch thread

        // Fetch thread data from API
        //console.log("d2-fetching thread");
        const response = await getThread(chatId, userName);
        //console.log("d2-received response: " + JSON.stringify(response));

        if (response.status === "success" && response.ui_msgs) {
          // Clear existing answers and control answers
          setAnswers([]);
          setControlAnswers([]);

          // Set thread ID
          setThreadId(response.thread_id);
          
          window.threadId = response.thread_id;
          
          // Process each message in the thread
          response.ui_msgs.forEach((msg, index) => {
            // Add human message
            if (msg.human) {
              setAnswers((prev) => [...prev, { query: msg.human }]);
              setControlAnswers((prev) => [...prev, {}]);
            }

            // Add AI response
            if (msg.ai) {
              const aiResponse = {
                text: msg.ai,
                usage: msg.usage || {},
                totalInputTokens: msg.usage?.input || 0,
                totalOutputTokens: msg.usage?.output || 0,
              };

              // Add query results if available
              if (msg.query_results) {
                try {
                  // Parse the JSON string to get the actual array
                  const parsedResults =
                    typeof msg.query_results === "string"
                      ? JSON.parse(msg.query_results)
                      : msg.query_results;

                  if (
                    Array.isArray(parsedResults) &&
                    parsedResults.length > 0
                  ) {
                    aiResponse.queryResults = parsedResults;
                    console.log("Parsed query results:", parsedResults);

                    // Handle chart data if available
                    if (msg.show_graph) {
                      if (msg.graph_code && msg.graph_code.trim() !== "") {
                        try {
                          // Parse the graph_code if it's a string
                          let chartData;
                          if (typeof msg.graph_code === "string") {
                            chartData = JSON.parse(msg.graph_code);
                          } else {
                            chartData = msg.graph_code;
                          }

                          // Ensure the chart data has the required properties
                          if (
                            chartData &&
                            typeof chartData === "object" &&
                            chartData.chart_type
                          ) {
                            aiResponse.chart = chartData;
                            console.log(
                              "Loaded chart from API response:",
                              aiResponse.chart
                            );
                          } else {
                            console.warn(
                              "Invalid chart data format:",
                              chartData
                            );
                            aiResponse.chart = null;
                          }
                        } catch (error) {
                          console.error("Error parsing graph_code:", error);
                          aiResponse.chart = null;
                        }
                      } else {
                        // No chart data available
                        aiResponse.chart = null;
                      }
                    }
                  } 
                } catch (error) {
                  console.error("Error parsing query_results:", error);
                  console.log("Raw query_results:", msg.query_results);
                  console.log(
                    "Type of query_results:",
                    typeof msg.query_results
                  );
                }
              }

              setAnswers((prev) => [...prev, aiResponse]);
              setControlAnswers((prev) => [
                ...prev,
                { current_tab_view: "answer" },
              ]);
            }
          });
        } else {
          // If thread not found or error, show error message
          console.log("d2-no thread found");
          setErrorMessage("Failed to load chat thread. Please try again.");
        }
      } catch (error) {
        console.error("Error loading thread data:", error);
        setErrorMessage(`Error loading thread: ${error.message}`);
      } finally {
        setLoadingThread(false);
      }
    };

    loadThreadData();
  }, [chatId, userName, hideContent, isFirstMessage]);

  const handleQuery = (event) => {
    // setEnabled(true);
    const inputValue = event.target.value.replace("\n", "");
    
    setQuery(inputValue);
  };

  const handleKeyPress = (event) => {
    
    if (event.code === "Enter" && loading === false && query !== "") {
      if (query === "/tools") {
        handleToolsCommand();
      } else {
        if (answers.length === 0) {
          onThreadUpdate(chatId, threadId, query);
        }
        getAnswer(query);
      }
    }
  };

  const handleToolsCommand = async () => {
    setEnabled(false);
    setLoading(true);
    setErrorMessage("");
    setQuery("");

    try {
      // Add a user message showing the command
      setAnswers((prevState) => [...prevState, { query: "/tools" }]);
      setControlAnswers((prevState) => [...prevState, {}]);

      const toolsMarkdown = await getInsights();

      // Create a formatted response with the tools list
      const toolsResponse = {
        text: toolsMarkdown,
      };

      setControlAnswers((prevState) => [
        ...prevState,
        { current_tab_view: "answer" },
      ]);
      setAnswers((prevState) => [...prevState, toolsResponse]);
    } catch (error) {
      console.error("Error fetching tools:", error);
      setErrorMessage(`Failed to fetch tools: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleClick = async (e) => {
    e.preventDefault();
    if (query !== "") {
      if (query === "/tools") {
        handleToolsCommand();
      } else {
        getAnswer(query);
      }
    }
  };

  const getAnswer = async (my_query) => {
    if (!loading && my_query !== "") {
      // Set flag if this is the first message
      if (answers.length === 0) {
        setIsFirstMessage(false);
      }

      setControlAnswers((prevState) => [...prevState, {}]);
      setAnswers((prevState) => [...prevState, { query: my_query }]);
      setEnabled(false);
      setLoading(true);
      setErrorMessage("");
      setQuery("");

      // Initialize thoughts state for streaming
      setThoughts([]);
      setShowThoughts(true);

      try {

        // Make thread_id available globally for the API call
        window.threadId = threadId;

        // Use the streaming API with the new payload structure
        invokeStreamingApi(
          my_query,
          selectedModel,
          // Thinking callback
          (updatedThoughts) => {
            
            setThoughts([...updatedThoughts]);
          },
          // Final response callback
          async (apiResponse) => {
            // Added async here
            // Hide thoughts when final response arrives
            setShowThoughts(false);

            // Update thread_id if provided in the response
            if (apiResponse.thread_id) {
              setThreadId(apiResponse.thread_id);
              window.threadId = apiResponse.thread_id;

              //TODO - Validate
              // Update thread in sidebar if this was a new chat
              if (isFirstMessage) {
                const threadTitle =
                  apiResponse.thread_title ||
                  my_query.substring(0, 50) +
                    (my_query.length > 50 ? "..." : "");
                onThreadUpdate(chatId, apiResponse.thread_id, threadTitle);
              }
            }

            if (apiResponse.status !== "success") {
              throw new Error(
                apiResponse.error || "Failed to get response from API"
              );
            }

            // Extract the response content
            let responseText = apiResponse.response;
            let queryResults = apiResponse.query_results || [];
            let showGraph = apiResponse.show_graph || false;
            let usage = apiResponse.usage || {
              input: 0,
              output: 0,
              total_tokens: 0,
              latency: 0,
            };

            // Create response object with all the properties expected by the UI
            let json = {
              text: responseText,
              usage: usage,
              totalInputTokens: usage.input || 0,
              totalOutputTokens: usage.output || 0,
              runningTraces: apiResponse.runningTraces || [],
              countRationals: apiResponse.countRationals || 0,
            };

            // Handle query results
            if (queryResults.length > 0) {
              json.queryResults = queryResults;

              // Set chart to loading if show_graph is true
              if (showGraph) {
                json.chart = "loading";
              }
            }

            // Remove thinking tags from response text
            if (json.text) {
              json.text = json.text.replace(/<thinking>.*?<\/thinking>/gis, "");
            }
            console.log("Final response JSON:", json);

            setControlAnswers((prevState) => [
              ...prevState,
              { current_tab_view: "answer" },
            ]);
            setAnswers((prevState) => [...prevState, json]);

            setLoading(false);
            setEnabled(false);

            // Clear first message flag after successful response
            setIsFirstMessage(false);

            // Generate chart if show_graph is true and we have query results
            if (showGraph && queryResults.length > 0) {
              // Add the original query and user_id to the json object before generating chart
              json.originalQuery = my_query;
              json.user_id = userName;
              json.chart = await generateChartApi(json);
              console.log("--------- Answer after chart generation ------");
              console.log(json);
              
            } else {
              console.log("------- Answer without chart-------");
              console.log(json);
              
            }
          }
        );
      } catch (error) {
        console.log("Call failed: ", error);
        setErrorMessage(error.toString());
        setLoading(false);
        setEnabled(false);
        setShowThoughts(false);
        setIsFirstMessage(false);
      }
    }
  };

  const handleRegenerateResponse = (index) => async () => {
    // Get the original query that generated this response
    const originalQuery = answers[index - 1].query;

    if (!originalQuery || loading) return;

    // Remove the current response
    const newAnswers = [...answers];
    const newControlAnswers = [...controlAnswers];

    // Keep only up to the query (remove the response)
    newAnswers.splice(index, 1);
    newControlAnswers.splice(index, 1);

    setAnswers(newAnswers);
    setControlAnswers(newControlAnswers);

    // Set loading state
    setLoading(true);
    setErrorMessage("");

    // Call getAnswer with the original query
    await getAnswer(originalQuery);
  };

  const handleShowTab = (index, type) => () => {
    const updatedItems = [...controlAnswers];
    updatedItems[index] = { ...updatedItems[index], current_tab_view: type };
    setControlAnswers(updatedItems);

    // If user clicks on Chart tab
    if (type === "chart") {
      const answer = answers[index];

      //console.log("Selected answer:", answer);

      // Check if we have query results
      if (answer.queryResults && answer.queryResults.length > 0) {
        // If chart is already available as an object with chart_type, no need to do anything
        if (
          answer.chart &&
          typeof answer.chart === "object" &&
          answer.chart.hasOwnProperty("chart_type")
        ) {
          console.log("Using existing chart data:", answer.chart);
          return;
        }

        // If chart is not available and not loading, generate it
        if (
          (!answer.chart || answer.chart === null) &&
          answer.chart !== "loading"
        ) {
          // Find the original query
          const originalQuery = answers[index - 1]?.query || "Query about data";

          // Set chart to loading state
          const updatedAnswers = [...answers];
          updatedAnswers[index] = {
            ...updatedAnswers[index],
            chart: "loading",
          };
          setAnswers(updatedAnswers);

          // Generate chart
          generateChartApi({
            ...answer,
            originalQuery: originalQuery,
            user_id: userName,
          })
            .then((chartData) => {
              // Update the answer with the chart data
              const newAnswers = [...answers];
              newAnswers[index] = { ...newAnswers[index], chart: chartData };
              console.log("Answer after chart generation:", newAnswers);
              setAnswers(newAnswers);
            })
            .catch((error) => {
              console.error("Error Preparing chart:", error);
              // Update with error state
              const newAnswers = [...answers];
              newAnswers[index] = { ...newAnswers[index], chart: null };
              setAnswers(newAnswers);
            });
        }
      }
    }
  };

  // Handle export to PDF
  const handleExportToPdf = (index) => () => {
    const answer = answers[index];
    if (!answer) return;

    // Prepare data for export
    const exportData = {
      query: answer.query || "No query available",
      answer: answer.answer || "No answer available",
      queryResults: answer.queryResults || [],
      timestamp: answer.timestamp || new Date().toISOString(),
      chart: answer.chart || null,
    };

    // Export to PDF
    exportToPdf(exportData);
  };

  return (
    <Box
      sx={{
        pl: 0,
        pr: 1,
        pt: 2,
        pb: 0,
      }}
    >
      {errorMessage !== "" && (
        <Alert
          severity="error"
          sx={{
            position: "fixed",
            width: "80%",
            top: "65px",
            left: "10%",
            marginLeft: "0",
          }}
          onClose={() => {
            setErrorMessage("");
          }}
        >
          {errorMessage}
        </Alert>
      )}

      {!hideContent && (
        <Box
          id="chatHelper"
          sx={{
            display: "flex",
            flexDirection: "column",
            height: height,
            overflow: "hidden",
            overflowY: "scroll",
            border: 1,
            borderRadius: 3,
            borderColor: "divider",
            mb: 1,
          }}
        >
          {loadingThread ? (
            <Box
              sx={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                height: "100%",
              }}
            >
              <Box sx={{ textAlign: "center" }}>
                <CircularProgress size={40} />
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 2 }}
                >
                  Loading conversation...
                </Typography>
              </Box>
            </Box>
          ) : answers.length > 0 ? (
            <ul style={{ paddingBottom: 14, margin: 0, listStyleType: "none" }}>
              {answers.map((answer, index) => (
                <li key={"meg" + index} style={{ marginBottom: 0 }}>
                  {answer.hasOwnProperty("text") ? (
                    <Box
                      sx={{
                        borderRadius: borderRadius,
                        pl: 1,
                        pr: 1,
                        display: "flex",
                        alignItems: "flex-start",
                        marginBottom: 1,
                      }}
                    >
                      <Box sx={{ pr: 1, pt: 1.5, pl: 0.5 }}>
                        <img
                          src="/images/genai.png"
                          alt="Amazon Bedrock"
                          width={28}
                          height={28}
                        />
                      </Box>
                      <Box sx={{ p: 0, flex: 1 }}>
                        <Box>
                          <Grow
                            in={
                              controlAnswers[index] &&
                              controlAnswers[index].current_tab_view ===
                                "answer"
                            }
                            timeout={{ enter: 600, exit: 0 }}
                            style={{ transformOrigin: "50% 0 0" }}
                            mountOnEnter
                            unmountOnExit
                          >
                            <Box
                              id={"answer" + index}
                              sx={{
                                opacity: 0.8,
                                "&.MuiBox-root": {
                                  animation: "fadeIn 0.8s ease-in-out forwards",
                                },
                                mt: 1,
                              }}
                            >
                              <Typography component="div" variant="body1">
                                <MarkdownRenderer content={answer.text} />
                              </Typography>
                            </Box>
                          </Grow>

                          {answer.hasOwnProperty("queryResults") && (
                            <Grow
                              in={
                                controlAnswers[index] &&
                                controlAnswers[index].current_tab_view ===
                                  "records"
                              }
                              timeout={{ enter: 600, exit: 0 }}
                              style={{ transformOrigin: "50% 0 0" }}
                              mountOnEnter
                              unmountOnExit
                            >
                              <Box
                                sx={{
                                  opacity: 0.8,
                                  "&.MuiBox-root": {
                                    animation:
                                      "fadeIn 0.8s ease-in-out forwards",
                                  },
                                  transform: "translateY(10px)",
                                  "&.MuiBox-root-appear": {
                                    transform: "translateY(0)",
                                  },
                                  mt: 1,
                                }}
                              >
                                <QueryResultsDisplay
                                  index={index}
                                  answer={answer}
                                />
                              </Box>
                            </Grow>
                          )}

                          <Grow
                            in={
                              controlAnswers[index] &&
                              controlAnswers[index].current_tab_view === "chart"
                            }
                            timeout={{ enter: 600, exit: 0 }}
                            style={{ transformOrigin: "50% 0 0" }}
                            mountOnEnter
                            unmountOnExit
                          >
                            <Box
                              sx={{
                                opacity: 0.8,
                                "&.MuiBox-root": {
                                  animation: "fadeIn 0.9s ease-in-out forwards",
                                },
                                transform: "translateY(10px)",
                                "&.MuiBox-root-appear": {
                                  transform: "translateY(0)",
                                },
                                mt: 1,
                              }}
                            >
                              {answer.hasOwnProperty("chart") &&
                              answer.chart &&
                              typeof answer.chart === "object" &&
                              answer.chart.hasOwnProperty("chart_type") ? (
                                <MyChart
                                  caption={answer.chart.caption}
                                  options={
                                    answer.chart.chart_configuration.options
                                  }
                                  series={
                                    answer.chart.chart_configuration.series
                                  }
                                  type={answer.chart.chart_type}
                                />
                              ) : (
                                <Box sx={{ p: 3, textAlign: "center" }}>
                                  {answer.chart === "loading" ? (
                                    <Box
                                      sx={{
                                        display: "flex",
                                        flexDirection: "column",
                                        alignItems: "center",
                                        gap: 2,
                                      }}
                                    >
                                      <CircularProgress size={40} />
                                      <Typography color="text.secondary">
                                        Preparing chart...
                                      </Typography>
                                    </Box>
                                  ) : (
                                    <Typography color="text.secondary">
                                      {answer.queryResults &&
                                      answer.queryResults.length > 0
                                        ? "Click the Chart tab to generate a visualization for this data."
                                        : "No chart data available for this response."}
                                    </Typography>
                                  )}
                                </Box>
                              )}
                            </Box>
                          </Grow>
                        </Box>

                        <Box
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "flex-start",
                            gap: 1,
                            py: 1,
                            mt: 1,
                            // flexWrap: { xs: "wrap", sm: "nowrap" },
                          }}
                        >
                          <Fade timeout={1000} in={true}>
                            <Box sx={{ display: "flex", alignItems: "center" }}>
                              <Button
                                sx={(theme) => ({
                                  pr: 1,
                                  pl: 1,
                                  "&.Mui-disabled": {
                                    borderBottom: 0.5,
                                    color: theme.palette.primary.main,
                                    borderRadius: 0,
                                  },
                                })}
                                data-amplify-analytics-on="click"
                                data-amplify-analytics-name="click"
                                data-amplify-analytics-attrs="button:answer-details"
                                size="small"
                                color="secondaryText"
                                disabled={
                                  controlAnswers[index] &&
                                  controlAnswers[index].current_tab_view ===
                                    "answer"
                                }
                                onClick={handleShowTab(index, "answer")}
                                startIcon={<QuestionAnswerOutlinedIcon />}
                              >
                                Answer
                              </Button>

                              <Button
                                sx={(theme) => ({
                                  pr: 1,
                                  pl: 1,
                                  "&.Mui-disabled": {
                                    borderBottom: 0.5,
                                    color: theme.palette.primary.main,
                                    borderRadius: 0,
                                  },
                                })}
                                data-amplify-analytics-on="click"
                                data-amplify-analytics-name="click"
                                data-amplify-analytics-attrs="button:answer-details"
                                size="small"
                                color="secondaryText"
                                disabled={
                                  controlAnswers[index] &&
                                  controlAnswers[index].current_tab_view ===
                                    "records"
                                }
                                onClick={handleShowTab(index, "records")}
                                startIcon={<TableRowsRoundedIcon />}
                              >
                                Records
                              </Button>

                              <Button
                                sx={(theme) => ({
                                  pr: 1,
                                  pl: 1,
                                  minHeight: { xs: "44px", sm: "36px" },
                                  mb: { xs: 1, sm: 0 },
                                  "&.Mui-disabled": {
                                    borderBottom: 0.5,
                                    color: theme.palette.primary.main,
                                    borderRadius: 0,
                                  },
                                })}
                                data-amplify-analytics-on="click"
                                data-amplify-analytics-name="click"
                                data-amplify-analytics-attrs="button:answer-details"
                                size="small"
                                color="secondaryText"
                                disabled={
                                  controlAnswers[index] &&
                                  controlAnswers[index].current_tab_view ===
                                    "chart"
                                }
                                onClick={handleShowTab(index, "chart")}
                                startIcon={<InsightsOutlinedIcon />}
                              >
                                Chart
                              </Button>

                              <Button
                                variant="outlined"
                                color="secondaryText"
                                size="small"
                                onClick={handleExportToPdf(index)}
                                disabled={loading}
                                startIcon={<FileDownloadIcon />}
                                sx={{
                                  ml: 1,
                                  minHeight: { xs: "44px", sm: "36px" },
                                  mb: { xs: 1, sm: 0 },
                                  borderRadius: 0,
                                  border: 0,
                                }}
                              >
                                Export
                              </Button>

                              <Button
                                variant="outlined"
                                color="primary"
                                size="small"
                                onClick={handleRegenerateResponse(index)}
                                disabled={loading}
                                startIcon={<RefreshIcon />}
                                sx={{
                                  ml: 1,
                                  minHeight: { xs: "44px", sm: "36px" },
                                  mb: { xs: 1, sm: 0, border: 0 },
                                }}
                              >
                                Regenerate
                              </Button>
                            </Box>
                          </Fade>

                          {answer.chart === "loading" && (
                            <Box
                              sx={{
                                display: "flex",
                                alignItems: "center",
                                ml: 1,
                              }}
                            >
                              <CircularProgress size={16} color="primary" />
                              <Typography
                                variant="caption"
                                color="secondaryText"
                                sx={{ ml: 1 }}
                              >
                                Preparing chart...
                              </Typography>
                            </Box>
                          )}

                          {/* Removed the rationale display */}
                        </Box>
                      </Box>
                    </Box>
                  ) : answer.hasOwnProperty("rationaleText") ? (
                    <Grid container justifyContent="flex-start">
                      <Fade timeout={2000} in={true}>
                        <Box
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            mb: 1,
                            pl: 2,
                            py: 1,
                          }}
                        >
                          <Box sx={{ display: "flex", alignItems: "center" }}>
                            <img
                              src="/images/sun.256x256.png"
                              width={22}
                              height={22}
                              style={{ opacity: 0.4 }}
                            />
                          </Box>

                          <Box
                            sx={{
                              pl: 0.5,
                              pr: 2,
                              ml: 1,
                              display: "flex",
                              alignItems: "center",
                              flexGrow: 1,
                            }}
                          >
                            <Typography color="text.secondary" variant="body1">
                              {answer.rationaleText}
                            </Typography>
                          </Box>
                        </Box>
                      </Fade>
                    </Grid>
                  ) : (
                    <Grid container justifyContent="flex-end">
                      <Box
                        sx={(theme) => ({
                          textAlign: "left",
                          borderRadius: borderRadius,
                          fontWeight: 500,
                          pt: 1,
                          pb: 1,
                          pl: 2,
                          pr: 2,
                          mt: 2,
                          mb: 1.5,
                          mr: 1,
                          boxShadow: "rgba(0, 0, 0, 0.05) 0px 4px 12px",
                          background: theme.palette.secondary.main,
                        })}
                      >
                        <Typography variant="body1">{answer.query}</Typography>
                      </Box>
                    </Grid>
                  )}
                </li>
              ))}

              {loading && (
                <>
                  <Box sx={{ p: 0, pl: 1, mb: 2, mt: 1 }}>
                    <ThoughtsDisplay
                      thoughts={thoughts}
                      visible={showThoughts}
                    />
                    <Answering loading={loading} />
                  </Box>
                </>
              )}

              {/* this is the last item that scrolls into
                    view when the effect is run */}
              <li ref={scrollRef} />
            </ul>
          ) : (
            <Box
              id="new_chat_box"
              textAlign={"center"}
              sx={{
                pl: 1,
                pt: 1,
                pr: 1,
                pb: 1,
                height: height,
                display: "flex",
                alignItems: "flex-end",
              }}
            >
              <div style={{ width: "100%" }}>
                <img
                  src="/images/logo-octopus.svg"
                  alt="Agents for Amazon Bedrock"
                  width={"10%"}
                />
                <Typography variant="h5" sx={{ pb: 1, fontWeight: 500 }}>
                  {APP_NAME}
                </Typography>
                <Typography sx={{ pb: 4, fontWeight: 400 }}>
                  Enable generative AI applications to execute multi step
                  business tasks using natural language.
                </Typography>
                <Typography
                  color="primary"
                  sx={{ fontSize: "1.1rem", pb: 1, fontWeight: 500 }}
                >
                  {chatId
                    ? "Type your message below to start a conversation."
                    : WELCOME_MESSAGE}
                </Typography>
              </div>
            </Box>
          )}
        </Box>
      )}

      <Paper
        component="form"
        sx={(theme) => ({
          zIndex: 0,
          p: { xs: 0.5, sm: 1 },
          mb: 2,
          display: "flex",
          alignItems: "center",
          boxShadow:
            "rgba(17, 17, 26, 0.05) 0px 4px 16px, rgba(17, 17, 26, 0.05) 0px 8px 24px, rgba(17, 17, 26, 0.05) 0px 16px 56px",
          border: 1,
          borderColor: "divider",
          borderRadius: 3,
        })}
      >
        <Box sx={{ pt: { xs: 1, sm: 1.5 }, pl: { xs: 0.5, sm: 0.5 } }}>
          <img
            src="/images/AWS_logo_RGB.png"
            alt="Amazon Web Services"
            height={20}
          />
        </Box>
        <InputBase
          required
          id="query"
          name="query"
          placeholder="Type your question..."
          fullWidth
          multiline
          onChange={handleQuery}
          onKeyDown={handleKeyPress}
          value={query}
          variant="outlined"
          inputProps={{
            maxLength: MAX_LENGTH_INPUT_SEARCH,
            style: { fontSize: "0.95rem" },
          }}
          sx={{ pl: 1, pr: 2 }}
        />
        <Divider sx={{ height: 32 }} orientation="vertical" />
        <IconButton
          color="primary"
          sx={{ p: { xs: 1.5, sm: 1 } }}
          aria-label="directions"
          disabled={!enabled}
          onClick={handleClick}
        >
          <SendIcon />
        </IconButton>
      </Paper>
    </Box>
  );
};

export default Chat;
