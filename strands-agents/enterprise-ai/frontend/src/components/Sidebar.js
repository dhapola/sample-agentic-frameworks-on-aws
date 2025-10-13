import React, { useState } from 'react';
import { styled } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import AddIcon from '@mui/icons-material/Add';
import ChatIcon from '@mui/icons-material/Chat';
import SearchIcon from '@mui/icons-material/Search';
import SettingsIcon from '@mui/icons-material/Settings';
import InputBase from '@mui/material/InputBase';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Tooltip from '@mui/material/Tooltip';
import CircularProgress from '@mui/material/CircularProgress';
import { v4 as uuidv4 } from 'uuid';

const drawerWidth = {
  xs: '100%',
  sm: 240,
  md: 280
};

const DrawerHeader = styled('div')(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-end',
  padding: theme.spacing(0, 1),
  minHeight: '48px',
}));

const Search = styled('div')(({ theme }) => ({
  position: 'relative',
  borderRadius: theme.shape.borderRadius,
  backgroundColor: theme.palette.mode === 'light' ? '#f5f5f5' : '#424242',
  '&:hover': {
    backgroundColor: theme.palette.mode === 'light' ? '#e0e0e0' : '#505050',
  },
  marginBottom: theme.spacing(1),
  width: '100%',
}));

const SearchIconWrapper = styled('div')(({ theme }) => ({
  padding: theme.spacing(0, 2),
  height: '100%',
  position: 'absolute',
  pointerEvents: 'none',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
}));

const StyledInputBase = styled(InputBase)(({ theme }) => ({
  color: 'inherit',
  width: '100%',
  '& .MuiInputBase-input': {
    padding: theme.spacing(1, 1, 1, 0),
    paddingLeft: `calc(1em + ${theme.spacing(4)})`,
    width: '100%',
  },
}));

const Sidebar = ({ 
  open, 
  handleDrawerClose, 
  handleDrawerOpen, 
  chatThreads = [], 
  activeChatId,
  onNewChat,
  onSelectChat,
  onSearchThreads,
  onDeleteThread,
  loading = false
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedGroups, setExpandedGroups] = useState({
    'Today': true,
    'Yesterday': true
  });
  const [settingsOpen, setSettingsOpen] = useState(false);
  
  const handleSearch = (e) => {
    const query = e.target.value;
    setSearchQuery(query);
    onSearchThreads(query);
  };

  const toggleGroup = (groupName) => {
    setExpandedGroups(prev => ({
      ...prev,
      [groupName]: !prev[groupName]
    }));
  };

  const handleDeleteThread = (e, threadId) => {
    e.stopPropagation(); // Prevent triggering the ListItemButton click
    if (onDeleteThread) {
      onDeleteThread(threadId);
    }
  };
  
  const handleSettingsClick = () => {
    setSettingsOpen(true);
    console.log("Settings button clicked");
    // You can add additional logic here, such as opening a settings dialog
    alert("Settings functionality will be implemented here");
  };

  // Group chat threads by date
  const groupThreadsByDate = (threads) => {
    const groups = {};
    
    threads.forEach(thread => {
      const date = new Date(thread.timestamp);
      const today = new Date();
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      
      let dateKey;
      
      if (date.toDateString() === today.toDateString()) {
        dateKey = 'Today';
      } else if (date.toDateString() === yesterday.toDateString()) {
        dateKey = 'Yesterday';
      } else {
        // Format as Month Day, Year (e.g., June 5, 2025)
        dateKey = date.toLocaleDateString('en-US', { 
          month: 'long', 
          day: 'numeric',
          year: 'numeric'
        });
      }
      
      if (!groups[dateKey]) {
        groups[dateKey] = [];
      }
      
      groups[dateKey].push(thread);
    });
    
    // Sort threads within each group by timestamp (newest first)
    Object.keys(groups).forEach(key => {
      groups[key].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    });
    
    return groups;
  };

  return (
    <>
      <Drawer
        sx={{
          width: { xs: '100%', sm: drawerWidth.sm, md: drawerWidth.md },
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: { xs: '100%', sm: drawerWidth.sm, md: drawerWidth.md },
            boxSizing: 'border-box',
            marginTop: '0px',
            position: { xs: 'fixed', sm: 'fixed' },
            height: '100%',
            zIndex: { xs: 1300, sm: 1200 },
            paddingBottom: '48px' // Add padding to make room for the bottom bar
          },
        }}
        variant="persistent"
        anchor="left"
        open={open}
      >
        <DrawerHeader>
          <Box sx={{ display: 'flex', width: '100%', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="subtitle2" sx={{ pl: 1, fontSize: { xs: '0.9rem', sm: '0.8rem' } }}>
              Conversations
            </Typography>
            <IconButton 
              onClick={handleDrawerClose} 
              size="medium"
              sx={{ 
                width: { xs: 44, sm: 40 }, 
                height: { xs: 44, sm: 40 }
              }}
            >
              <ChevronLeftIcon />
            </IconButton>
          </Box>
        </DrawerHeader>
        
        <Box sx={{ px: { xs: 2, sm: 1.5 }, pb: 1 }}>
          <Button 
            variant="outlined" 
            fullWidth 
            startIcon={<AddIcon />}
            onClick={onNewChat}
            sx={(theme) => ({ 
              mb: 2, 
              py: { xs: 1, sm: 0.75 },
              fontSize: { xs: '0.95rem', sm: '0.9rem' },
              backgroundColor: 'transparent',
              border: `1px solid ${theme.palette.primary.main}`,
              color: theme.palette.primary.main,
              '&:hover': {
                backgroundColor: 'rgba(53, 28, 117, 0.04)',
                border: `1px solid ${theme.palette.primary.main}`,
              }
            })}
          >
            New Chat
          </Button>
          
          <Search>
            <SearchIconWrapper>
              <SearchIcon />
            </SearchIconWrapper>
            <StyledInputBase
              placeholder="Search chats…"
              inputProps={{ 
                'aria-label': 'search',
                style: { fontSize: '0.95rem' }
              }}
              value={searchQuery}
              onChange={handleSearch}
            />
          </Search>
        </Box>
        
        <Divider />
        
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 4 }}>
            <CircularProgress size={32} />
          </Box>
        ) : chatThreads.length === 0 ? (
          <Box sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              No conversations yet. Start a new chat!
            </Typography>
          </Box>
        ) : (
          Object.entries(groupThreadsByDate(chatThreads)).map(([dateGroup, threads]) => {
            // Initialize group as expanded if not in state
            if (expandedGroups[dateGroup] === undefined) {
              setExpandedGroups(prev => ({
                ...prev,
                [dateGroup]: true // Default to expanded
              }));
            }
            
            const isExpanded = expandedGroups[dateGroup] !== false;
            
            return (
              <React.Fragment key={dateGroup}>
                <Box 
                  onClick={() => toggleGroup(dateGroup)}
                  sx={{ 
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    px: 2, 
                    py: { xs: 1, sm: 0.5 }, 
                    backgroundColor: 'rgba(0, 0, 0, 0.04)',
                    cursor: 'pointer',
                    '&:hover': {
                      backgroundColor: 'rgba(0, 0, 0, 0.08)',
                    },
                    minHeight: { xs: 44, sm: 36 }
                  }}
                >
                  <Typography 
                    variant="caption" 
                    sx={{ 
                      color: 'text.secondary',
                      fontSize: { xs: '0.8rem', sm: '0.7rem' },
                      fontWeight: 500,
                    }}
                  >
                    {dateGroup}
                  </Typography>
                  {isExpanded ? 
                    <ExpandLessIcon fontSize="small" sx={{ color: 'text.secondary', fontSize: { xs: '1.2rem', sm: '1rem' } }} /> : 
                    <ExpandMoreIcon fontSize="small" sx={{ color: 'text.secondary', fontSize: { xs: '1.2rem', sm: '1rem' } }} />
                  }
                </Box>
                
                {isExpanded && (
                  <List sx={{ px: 1 }}>
                    {threads.map((thread) => (
                      <ListItem key={thread.id} disablePadding>
                        <ListItemButton 
                          selected={thread.id === activeChatId}
                          onClick={() => onSelectChat(thread.id)}
                          sx={(theme) => ({
                            borderRadius: 1,
                            mb: 0.5,
                            py: { xs: 1.5, sm: 1 },
                            '&.Mui-selected': {
                              
                              border: 1,
                              borderColor: theme.palette.primary.main
                            },
                            position: 'relative',
                            pr: 6, // Add padding for delete button
                            '& .delete-button': {
                              display: { xs: 'flex', sm: 'none' },
                              opacity: { xs: 0.6, sm: 0 },
                              transition: 'opacity 0.2s ease-in-out'
                            },
                            '&:hover .delete-button': {
                              display: 'flex',
                              opacity: 0.6
                            },
                            '&:active .delete-button': {
                              display: 'flex',
                              opacity: 0.6
                            }
                          })}
                        >
                          <ListItemIcon sx={{ minWidth: { xs: 40, sm: 36 } }}>
                            <ChatIcon fontSize="small" />
                          </ListItemIcon>
                          <ListItemText 
                            primary={thread.title} 
                            primaryTypographyProps={{
                              noWrap: true,
                              fontSize: { xs: '0.95rem', sm: '0.9rem' }
                            }}
                            
                          />
                          <Tooltip title="Delete thread">
                            <IconButton 
                              className="delete-button"
                              size="small"
                              onClick={(e) => handleDeleteThread(e, thread.id)}
                              sx={{ 
                                position: 'absolute',
                                right: 8,
                                width: { xs: 36, sm: 32 },
                                height: { xs: 36, sm: 32 },
                                '&:hover': {
                                  opacity: 1,
                                  color: 'error.main'
                                }
                              }}
                            >
                              <DeleteOutlineIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </ListItemButton>
                      </ListItem>
                    ))}
                  </List>
                )}
              </React.Fragment>
            );
          })
        )}
        
        {/* Fixed bottom bar with settings */}
        <Box
          sx={(theme) => ({
            position: 'fixed',
            bottom: 0,
            width: { xs: '100%', sm: drawerWidth.sm, md: drawerWidth.md },
            borderTop: `1px solid ${theme.palette.divider}`,
            backgroundColor: 'background.paper',
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
            padding: '8px 16px',
            zIndex: 1250
          })}
        >
          <Tooltip title="Settings">
            <IconButton
              size="small"
              onClick={handleSettingsClick}
              sx={(theme) => ({
                color: theme.palette.primary.main,
              })}
            >
              <SettingsIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </Drawer>
      
      {!open && (
        <IconButton
          color="primary"
          aria-label="open drawer"
          onClick={handleDrawerOpen}
          edge="start"
          sx={{ 
            position: 'fixed', 
            ml: 0.1,
            mt: 0.4,
            left: { xs: 4, sm: 8 }, 
            top: { xs: 6, sm: 6 }, 
            zIndex: 1300,
            width: { xs: 32, sm: 32 },
            height: { xs: 32, sm: 32 },
            backgroundColor: 'white',
            boxShadow: 'none',
            border: '1px solid #351c75',
            '&:hover': {
              backgroundColor: 'rgba(255, 255, 255, 0.9)',
            },
            '& .MuiSvgIcon-root': {
              marginLeft: '2px' // Add left margin to the icon
            }
          }}
        >
          <ChevronRightIcon fontSize="small" />
        </IconButton>
      )}
    </>
  );
};

export default Sidebar;
