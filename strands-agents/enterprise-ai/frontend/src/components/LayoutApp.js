import React from "react";
import { useEffect } from "react";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";
import GlobalStyles from "@mui/material/GlobalStyles";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import "@fontsource/roboto/300.css";
import "@fontsource/roboto/400.css";
import "@fontsource/roboto/500.css";
import "@fontsource/roboto/700.css";
import Chat from "./Chat";
import Sidebar from "./Sidebar";
import ModelSelector from "./ModelSelector";
import { Slide } from "react-slideshow-image";
import "react-slideshow-image/dist/styles.css";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import { DEFAULT_MODEL } from "../env";
import { createThread, getAllThreads, deleteThread } from "../utils/ApiCalls";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";

function LayoutApp() {
  const [userName, setUserName] = React.useState("Deepesh");
  const [open, setOpen] = React.useState(false);
  const [drawerOpen, setDrawerOpen] = React.useState(true);
  const [selectedModel, setSelectedModel] = React.useState(DEFAULT_MODEL);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const [snackbar, setSnackbar] = React.useState({
    open: false,
    message: "",
    severity: "info",
  });

  const [chatThreads, setChatThreads] = React.useState([]);
  const [activeChatId, setActiveChatId] = React.useState(null);
  const [filteredThreads, setFilteredThreads] = React.useState([]);

  // Load chat threads from API
  useEffect(() => {
    const loadThreads = async () => {
      try {
        setLoading(true);
        const response = await getAllThreads(userName);

        if (response.status === "success" && response.threads) {
          // Transform the API response to match our thread format
          const threads = response.threads.map((thread) => ({
            id: thread.thread_id,
            title: thread.thread_title,
            timestamp: thread.updated_at || thread.created_at,
            messageCount: thread.message_count || 0,
          }));

          setChatThreads(threads);
          setFilteredThreads(threads);

          // Set active chat ID to the first thread if available
          if (threads.length > 0 && !activeChatId) {
            setActiveChatId(threads[0].id);
            setIsNewChat(false); // Show the latest thread instead of new chat screen
          }
        } else {
          // If no threads are returned, initialize with a welcome thread
          if (!response.threads || response.threads.length === 0) {
            setIsNewChat(true); // Show new chat screen when no threads exist
          }
        }
      } catch (err) {
        console.error("Failed to load threads:", err);
        setError("Failed to load chat threads. Please try again later.");
        setSnackbar({
          open: true,
          message: "Failed to load chat threads. Please try again later.",
          severity: "error",
        });

        // Show new chat screen if API fails
        setIsNewChat(true);
      } finally {
        setLoading(false);
      }
    };

    loadThreads();
  }, [userName]);

  // Sort and filter threads when they change
  useEffect(() => {
    // Sort threads by timestamp before filtering
    const sortedThreads = [...chatThreads].sort(
      (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
    );

    setFilteredThreads(sortedThreads);
  }, [chatThreads]);

  const defaultTheme = createTheme({
    palette: {
      primary: {
        main: "#351c75",
      },
      secondary: {
        main: "#d9d2e9",
      },
    },
    typography: {
      fontSize: 14,
      fontFamily: [
        "Roboto",
        "-apple-system",
        "BlinkMacSystemFont",
        '"Segoe UI"',
        "Arial",
        "sans-serif",
      ].join(","),
      h6: {
        fontSize: "1.1rem",
        "@media (max-width:600px)": {
          fontSize: "1rem",
        },
      },
    },
    components: {
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            textTransform: "none",
            minHeight: 36,
            "@media (max-width:600px)": {
              minHeight: 44,
            },
          },
        },
      },
      MuiIconButton: {
        styleOverrides: {
          root: {
            "@media (max-width:600px)": {
              padding: 8,
            },
          },
        },
      },
    },
  });

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const handleProfileClick = () => {
    console.log("Profile icon clicked");
    // Placeholder function for profile icon click
    // You can implement your profile functionality here
    alert("Profile functionality will be implemented here");
  };

  const handleDrawerOpen = () => {
    setDrawerOpen(true);
  };

  const handleDrawerClose = () => {
    setDrawerOpen(false);
  };

  const handleSnackbarClose = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  // Check if the device is mobile
  const isMobile = React.useMemo(() => {
    if (typeof window !== "undefined") {
      return window.innerWidth < 600;
    }
    return false;
  }, []);

  const [isNewChat, setIsNewChat] = React.useState(false);

  // Close drawer by default on mobile
  React.useEffect(() => {
    if (isMobile) {
      setDrawerOpen(false);
    }
  }, [isMobile]);

  const handleNewChat = async () => {
    // receive response and set variables
    var new_thread = await createThread();

    const created_thread = {
      id: new_thread.id,
      title: new_thread.title,
      timestamp: new_thread.timestamp,
      messageCount: 0,
    };

    setChatThreads([created_thread, ...chatThreads]);
    setIsNewChat(false);
    setActiveChatId(new_thread.id);
    updateChatTitle(new_thread.id, new_thread.title);

    // On mobile, close the drawer after selecting a new chat
    if (isMobile) {
      setDrawerOpen(false);
    }
  };

  const handleSelectChat = (chatId) => {
    setIsNewChat(false);
    setActiveChatId(chatId);

    // On mobile, close the drawer after selecting a chat
    if (isMobile) {
      setDrawerOpen(false);
    }
  };

  const handleSearchThreads = (query) => {
    if (!query) {
      setFilteredThreads(chatThreads);
      return;
    }

    const filtered = chatThreads.filter((thread) =>
      thread.title.toLowerCase().includes(query.toLowerCase())
    );
    setFilteredThreads(filtered);
  };

  const updateChatTitle = (chatId, title) => {
    setChatThreads((prevThreads) =>
      prevThreads.map((thread) =>
        thread.id === chatId ? { ...thread, title } : thread
      )
    );
  };

  const handleThreadUpdate = (oldChatId, newThreadId, threadTitle) => {
    setChatThreads((prevThreads) =>
      prevThreads.map((thread) =>
        thread.id === oldChatId
          ? { ...thread, id: newThreadId, title: threadTitle }
          : thread
      )
    );
    setActiveChatId(newThreadId);
  };

  const handleDeleteThread = async (threadId) => {
    try {
      // Call the API to delete the thread
      await deleteThread(threadId, userName);

      // If deleting the active thread, select another thread
      if (threadId === activeChatId) {
        const otherThreads = chatThreads.filter((t) => t.id !== threadId);
        if (otherThreads.length > 0) {
          setActiveChatId(otherThreads[0].id);
        } else {
          // If no threads left, create a new one
          chatThreads.length = 0;
          filteredThreads.length = 0;
          handleNewChat();
        }
      }

      // Remove the thread from the list
      setChatThreads((prevThreads) =>
        prevThreads.filter((thread) => thread.id !== threadId)
      );

      setSnackbar({
        open: true,
        message: "Thread deleted successfully",
        severity: "success",
      });
    } catch (err) {
      console.error("Failed to delete thread:", err);
      setSnackbar({
        open: true,
        message: "Failed to delete thread. Please try again.",
        severity: "error",
      });
    }
  };

  return (
    <ThemeProvider theme={defaultTheme}>
      <GlobalStyles
        styles={{ ul: { margin: 0, padding: 0, listStyle: "none" } }}
      />
      <CssBaseline />

      <Box
        sx={{
          display: "flex",
          paddingTop: "0px",
          width: "100%",
          position: "relative",
          minHeight: "100vh",
          flexDirection: { xs: "column", sm: "row" },
        }}
      >
        <Sidebar
          open={drawerOpen}
          handleDrawerClose={handleDrawerClose}
          handleDrawerOpen={handleDrawerOpen}
          chatThreads={filteredThreads}
          activeChatId={activeChatId}
          onNewChat={handleNewChat}
          onSelectChat={handleSelectChat}
          onSearchThreads={handleSearchThreads}
          onDeleteThread={handleDeleteThread}
          loading={loading}
        />

        <Box
          component="main"
          sx={{
            flexGrow: 1,
            transition: (theme) =>
              theme.transitions.create("margin", {
                easing: theme.transitions.easing.sharp,
                duration: theme.transitions.duration.leavingScreen,
              }),
            marginLeft: {
              xs: 0, // No margin on mobile regardless of drawer state
              sm: drawerOpen ? 0 : "-240px",
              md: drawerOpen ? 0 : "-280px",
            },
            width: "100%",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
          }}
        >
          {/* Horizontal bar with model selector */}
          <Box
            sx={(theme) => ({
              width: "100%",
              borderBottom: `1px solid ${theme.palette.primary.main}`,
              borderTop: "none",
              borderLeft: "none",
              borderRight: "none",
              padding: "6px 16px", // Reduced padding to decrease height
              paddingLeft: { xs: "40px", sm: "40px" }, // Reduced left padding to match smaller drawer button
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              position: "relative", // Add position relative
              zIndex: 1100, // Lower z-index than drawer open button
            })}
          >
            <ModelSelector
              selectedModel={selectedModel}
              onModelChange={(model) => setSelectedModel(model)}
            />

            <IconButton
              onClick={handleProfileClick}
              sx={(theme) => ({
                color: theme.palette.primary.main,
                backgroundColor: "white",
                marginLeft: "auto",
                "&:hover": {
                  backgroundColor: "rgba(255, 255, 255, 0.9)",
                },
              })}
            >
              <AccountCircleIcon fontSize="medium" />
            </IconButton>
          </Box>

          <Container
            disableGutters
            maxWidth="lg"
            component="main"
            sx={{
              width: "100%",
              height: "100%",
              px: { xs: 1, sm: 2 },
            }}
          >
            <Chat
              userName={userName}
              chatId={activeChatId}
              selectedModel={selectedModel}
              onStartTyping={() => {
                // Only switch to chat mode, don't trigger API calls for new chats
                setIsNewChat(false);
              }}
              onThreadUpdate={handleThreadUpdate}
              sx={{}}
            />
          </Container>
        </Box>
      </Box>

      <Dialog
        fullWidth={true}
        maxWidth={"xl"}
        open={open}
        onClose={handleClose}
      >
        <DialogTitle>Amazon Bedrock</DialogTitle>
        <DialogContent>
          <Slide
            autoplay={false}
            transitionDuration={500}
            onChange={function noRefCheck() {}}
            onStartChange={function noRefCheck() {}}
          >
            <div className="each-slide-effect">
              <img
                src="/images/gen-ai-assistant-diagram.png"
                width={"100%"}
                alt="Powered By AWS"
              />
            </div>
            <div className="each-slide-effect">
              <img
                src="/images/gen-ai-assistant-bedrock.png"
                width={"100%"}
                alt="Powered By AWS"
              />
            </div>
            <div className="each-slide-effect">
              <img
                src="/images/gen-ai-assistant-agent.png"
                width={"100%"}
                alt="Powered By AWS"
              />
            </div>
            <div className="each-slide-effect">
              <img
                src="/images/gen-ai-assistant-agent-flow.png"
                width={"100%"}
                alt="Powered By AWS"
              />
            </div>
          </Slide>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Close</Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          onClose={handleSnackbarClose}
          severity={snackbar.severity}
          sx={{ width: "100%" }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </ThemeProvider>
  );
}

export default LayoutApp;
