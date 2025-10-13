import { API_URL } from "../env";

const API_INFO = "api/insights";
const API_MODELS = "api/models";
const API_THREADS = "api/threads";
const API_THREAD = "api/thread";
const API_ANSWER = "api/answer";
const API_CHART = "api/chart";

/**
 * Invokes the streaming API to get real-time thoughts and final response
 *
 * @param {string} query - The user's query
 * @param {string} selectedModel - The selected model ID
 * @param {Function} onThinking - Callback for thinking updates
 * @param {Function} onFinalResponse - Callback for final response
 * @returns {Function} - Function to close the connection
 */
export const invokeStreamingApi = (
  query,
  selectedModel,
  onThinking,
  onFinalResponse
) => {
  // Create URL for POST request
  const url = `${API_URL}/${API_ANSWER}`;

  // Create payload with required fields
  const payload = {
    human: query,
    thread_id: window.threadId || "", // Get thread_id from global state
    user: "Deepesh",
    model_id: selectedModel || "claude-3-5-sonnet",
  };

  // Make POST request with fetch
  fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      // Create a reader for the response body stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      const thoughts = [];
      let heartbeatTimeout;

      // Reset heartbeat timeout
      const resetHeartbeatTimeout = () => {
        if (heartbeatTimeout) {
          clearTimeout(heartbeatTimeout);
        }

        // Close connection if no heartbeat received in 30 seconds
        heartbeatTimeout = setTimeout(() => {
          console.error(
            "No heartbeat received for 30 seconds, closing connection"
          );
          reader.cancel();
          onFinalResponse({
            status: "error",
            error: "Connection timeout - no response from server",
            thread_id: window.threadId || "",
          });
        }, 30000);
      };

      // Start the heartbeat timeout
      resetHeartbeatTimeout();

      // Process the stream
      const processStream = () => {
        reader
          .read()
          .then(({ done, value }) => {
            if (done) {
              console.log("Stream complete");
              if (heartbeatTimeout) {
                clearTimeout(heartbeatTimeout);
              }
              return;
            }

            // Decode the chunk and add it to our buffer
            buffer += decoder.decode(value, { stream: true });

            // Process complete events in the buffer
            const lines = buffer.split("\n\n");
            buffer = lines.pop(); // Keep the last incomplete chunk in the buffer

            lines.forEach((line) => {
              if (line.startsWith("data: ")) {
                try {
                  const data = JSON.parse(line.substring(6));

                  // Reset heartbeat timeout on any message
                  resetHeartbeatTimeout();

                  if (data.type === "heartbeat") {
                    // Heartbeat received, do nothing but keep connection alive
                    return;
                  } else if (
                    data.type === "thinking" ||
                    data.type === "tool_use"
                  ) {
                    thoughts.push(data);
                    onThinking(thoughts);
                  } else if (data.type === "final") {
                    if (heartbeatTimeout) {
                      clearTimeout(heartbeatTimeout);
                    }
                    reader.cancel();

                    // Handle the new response schema with ui_msgs array
                    if (
                      data.ui_msgs &&
                      Array.isArray(data.ui_msgs) &&
                      data.ui_msgs.length > 0
                    ) {
                      // Get the latest message from the ui_msgs array
                      const latestMessage =
                        data.ui_msgs[data.ui_msgs.length - 1];

                      // Parse query_results if it's a string
                      let queryResults = [];
                      if (latestMessage.query_results) {
                        try {
                          queryResults =
                            typeof latestMessage.query_results === "string"
                              ? JSON.parse(latestMessage.query_results)
                              : latestMessage.query_results;

                          // Ensure it's an array
                          if (!Array.isArray(queryResults)) {
                            console.warn(
                              "query_results is not an array after parsing:",
                              queryResults
                            );
                            queryResults = [];
                          }
                          console.log(
                            "Parsed query_results in ApiCalls:",
                            queryResults
                          );
                        } catch (error) {
                          console.error(
                            "Error parsing query_results in API response:",
                            error
                          );
                          console.log(
                            "Raw query_results:",
                            latestMessage.query_results
                          );
                          queryResults = [];
                        }
                      }

                      // Create a response object with the content and any additional data
                      const responseObj = {
                        status: data.status || "success",
                        response: latestMessage.ai,
                        thread_id: data.thread_id || "",
                        query_results: queryResults,
                        show_graph: latestMessage.show_graph || false,
                        usage: latestMessage.usage || {
                          input: 0,
                          output: 0,
                          total_tokens: 0,
                          latency: 0,
                        },
                      };

                      onFinalResponse(responseObj);
                    } else {
                      // Fallback to old format if ui_msgs is not available
                      const responseObj = {
                        status: "success",
                        response: data.content,
                        thread_id: data.thread_id || "",
                      };

                      // Add query results if available
                      if (data.query_results) {
                        responseObj.query_results = data.query_results;
                      }

                      // Add show_graph flag if available
                      if (data.show_graph !== undefined) {
                        responseObj.show_graph = data.show_graph;
                      }

                      onFinalResponse(responseObj);
                    }
                  } else if (data.type === "error") {
                    if (heartbeatTimeout) {
                      clearTimeout(heartbeatTimeout);
                    }
                    reader.cancel();

                    // Check if the error is in the new format with ui_msgs
                    if (
                      data.ui_msgs &&
                      Array.isArray(data.ui_msgs) &&
                      data.ui_msgs.length > 0
                    ) {
                      const latestMessage =
                        data.ui_msgs[data.ui_msgs.length - 1];
                      onFinalResponse({
                        status: "error",
                        error: latestMessage.error || "Unknown error occurred",
                      });
                    } else {
                      onFinalResponse({
                        status: "error",
                        error: data.content || "Unknown error occurred",
                      });
                    }
                  }
                } catch (error) {
                  console.error("Error parsing event data:", error, line);
                }
              }
            });

            // Continue reading
            processStream();
          })
          .catch((error) => {
            console.error("Error reading stream:", error);
            if (heartbeatTimeout) {
              clearTimeout(heartbeatTimeout);
            }
            onFinalResponse({
              status: "error",
              error: "Connection error while streaming response",
            });
          });
      };

      processStream();
    })
    .catch((error) => {
      console.error("Fetch error:", error);
      onFinalResponse({
        status: "error",
        error: `Failed to connect to server: ${error.message}`,
        thread_id: window.threadId || "",
      });
    });

  // Return a function to cancel the request if needed
  return () => {
    console.log("Request cancelled by user");
  };
};

/**
 * Invokes the backend API to generate a chart based on query results
 *
 * @param {Object} answer - The answer object containing query text and results
 * @returns {Promise<Object>} - The chart configuration
 */
export const generateChartApi = async (answer) => {
  try {
    // Only proceed if we have query results
    if (!answer.queryResults || answer.queryResults.length === 0) {
      return null;
    }

    // Find the original user query from the answers array
    // This assumes that the answer object has access to the original query
    const userQuery = answer.originalQuery ;

    console.log("Preparing chart for answer:", answer);
    const response = await fetch(`${API_URL}/${API_CHART}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: userQuery,
        queryResults: answer.queryResults,
        user_id: answer.user_id || "Deepesh",
        thread_id: window.threadId ,
      }),
    });

    if (!response.ok) {
      throw new Error(
        `Chart API request failed with status ${response.status}`
      );
    }

    const data = await response.json();
    console.log("chart preparation code:", data);

    // Check if the response contains graph_code
    if (
      data.graph_code &&
      typeof data.graph_code === "string" &&
      data.graph_code.trim() !== ""
    ) {
      try {
        return JSON.parse(data.graph_code);
      } catch (parseError) {
        console.error("Error parsing graph_code:", parseError);
      }
    }

    // Fallback to old format
    if (data.chart && typeof data.chart === "string") {
      try {
        return JSON.parse(data.chart);
      } catch (parseError) {
        console.error("Error parsing chart data:", parseError);
      }
    }

    // If we have a direct chart object
    if (data.chart && typeof data.chart === "object") {
      return data.chart;
    }

    return null;
  } catch (error) {
    console.error("Error generating chart:", error);
    return null;
  }
};

// move code to create a new thread
export const createThread = async (answer) => {
  const payload = {
    human: "New Chat",
    user: "x",
  };

  // Make POST request with fetch
  const url = `${API_URL}/${API_THREAD}`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! Status: ${response}`);
  }

  const newThreadData = await response.json();

  const new_thread = {
    id: newThreadData.thread_id,
    title: newThreadData.thread_title,
    timestamp: new Date().toISOString(),
    messageCount: 0,
  };
  return new_thread;
};

export const getInsights = async () => {
  const response = await fetch(`${API_URL}/${API_INFO}`);
  if (!response.ok) {
    throw new Error(`Error fetching tools: ${response.statusText}`);
  }
  const toolsData = await response.json();

  // Format the tools list for display
  let toolsMarkdown = "### Available Tools\n\n";

  toolsData.forEach((category) => {
    toolsMarkdown += `#### ${category.type}\n\n`;
    category.tools.forEach((tool) => {
      toolsMarkdown += `- **${tool}**\n`;
    });
    toolsMarkdown += "\n";
  });

  return toolsMarkdown;
};

/**
 * Fetches all chat threads for a user
 *
 * @param {string} user - User ID (default: "Deepesh")
 * @param {number} page - Page number for pagination (default: 1)
 * @param {number} pageSize - Number of threads per page (default: 10)
 * @returns {Promise<Object>} - Promise resolving to the API response
 */
export const getAllThreads = async (
  user = "Deepesh",
  page = 1,
  pageSize = 10
) => {
  try {
    const response = await fetch(
      `${API_URL}/${API_THREADS}?user=${user}&page=${page}&page_size=${pageSize}`
    );

    if (!response.ok) {
      throw new Error(`Error fetching threads: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching threads:", error);
    throw error;
  }
};

/**
 * Fetches a specific thread by ID
 *
 * @param {string} threadId - Thread ID
 * @param {string} user - User ID (default: "Deepesh")
 * @returns {Promise<Object>} - Promise resolving to the API response
 */
export const getThread = async (threadId, user = "Deepesh") => {
  try {
    const response = await fetch(
      `${API_URL}/${API_THREAD}/${threadId}?user=${user}`
    );

    if (!response.ok) {
      throw new Error(`Error fetching thread: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`Error fetching thread ${threadId}:`, error);
    throw error;
  }
};

/**
 * Deletes a specific thread by ID
 *
 * @param {string} threadId - Thread ID
 * @param {string} user - User ID (default: "Deepesh")
 * @returns {Promise<Object>} - Promise resolving to the API response
 */
export const deleteThread = async (threadId, user = "Deepesh") => {
  const url = `${API_URL}/${API_THREAD}/${threadId}?user=${user}`;

  try {
    const response = await fetch(url, {
      method: "DELETE",
    });

    if (!response.ok) {
      throw new Error(`Error deleting thread: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`Error deleting thread ${threadId}:`, error);
    throw error;
  }
};

export const getModels = async () => {
  try {
    const response = await fetch(`${API_URL}/${API_MODELS}`);

    if (!response.ok) {
      throw new Error(`Failed to fetch models: ${response.status}`);
    }

    const data = await response.json();

    // Use all models from the API response without filtering
    const modelsList = data.models.map((model) => ({
      id: model.id,
      name: model.name,
    }));

    return modelsList;
  } catch (err) {
    console.error("Error fetching models:", err);
    throw err;
  }
};
