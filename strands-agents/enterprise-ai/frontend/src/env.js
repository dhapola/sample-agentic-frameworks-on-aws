// Application Information
const APP_NAME = "Enterprise AI Assistant";
const WELCOME_MESSAGE = "I'm your AI Assistant";

// API Configuration
const API_URL = "http://localhost:5000"; // Flask backend URL


const MAX_LENGTH_INPUT_SEARCH = 500;
const DEFAULT_MODEL = 'us.amazon.nova-lite-v1:0';
// const DEFAULT_MODEL = 'us.anthropic.claude-3-7-sonnet-20250219-v1:0';

export { 
    APP_NAME, 
    WELCOME_MESSAGE, 
    MAX_LENGTH_INPUT_SEARCH,
    API_URL,
    DEFAULT_MODEL
};