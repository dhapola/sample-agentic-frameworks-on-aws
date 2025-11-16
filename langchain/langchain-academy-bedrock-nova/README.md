![LangChain Academy](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66e9eba1020525eea7873f96_LCA-big-green%20(2).svg)

# LangChain Academy - AWS Bedrock Nova Edition

## Introduction

Welcome to LangChain Academy with AWS Bedrock Nova! This repository contains the complete LangChain Academy course materials, specifically adapted to work with AWS Bedrock Nova models instead of OpenAI. 

**This is a standalone repository** - you don't need to clone the original LangChain Academy repository. All course materials have been modified to use AWS Bedrock Nova models and include the necessary configuration for AWS integration.

The course teaches you how to build agent and multi-agent applications using LangGraph, LangChain's framework for creating controllable and reliable AI workflows. Each module builds progressively on the previous one, taking you from basic concepts to advanced production-ready implementations.

## Course Structure

This course is organized into 7 modules, each focusing on specific aspects of LangGraph development:

### Module 0: Basics
- **Focus**: Foundation setup and basic LangChain concepts
- **Content**: Environment setup, chat models, and basic LangChain operations
- **Key Learning**: Understanding the fundamentals before diving into LangGraph

### Module 1: Simple Graphs
- **Focus**: Introduction to LangGraph fundamentals
- **Content**: 
  - Building simple graphs with nodes and edges
  - Creating basic agents with tool calling
  - Understanding state management
  - Router patterns and conditional logic
  - Agent memory and persistence
- **Key Learning**: Core LangGraph concepts and basic agent construction

### Module 2: Agent Architectures  
- **Focus**: Advanced state management and agent patterns
- **Content**:
  - Complex state schemas and reducers
  - Chatbot implementations with external memory
  - Message trimming and filtering strategies
  - Multiple schema handling
  - Summarization techniques
- **Key Learning**: Building robust, stateful conversational agents

### Module 3: Human-in-the-Loop
- **Focus**: Interactive agents and human feedback integration
- **Content**:
  - Streaming and real-time interactions
  - Breakpoints and interruption handling
  - Dynamic breakpoints based on conditions
  - State editing and human feedback loops
  - Time travel and state rollback
- **Key Learning**: Creating agents that work collaboratively with humans

### Module 4: Multi-Agent Systems
- **Focus**: Complex workflows and agent coordination
- **Content**:
  - Parallelization and concurrent processing
  - Map-reduce patterns for large-scale operations
  - Sub-graphs and modular agent design
  - Research assistant implementations
  - Agent orchestration patterns
- **Key Learning**: Building sophisticated multi-agent systems

### Module 5: Memory & Personalization
- **Focus**: Advanced memory systems and personalization
- **Content**:
  - Persistent memory stores and retrieval
  - Memory schema design for user profiles
  - Collection-based memory organization
  - Personalized agent behaviors
  - Long-term memory management
- **Key Learning**: Creating agents with sophisticated memory capabilities

### Module 6: Deployment & Production
- **Focus**: Production deployment and scaling
- **Content**:
  - LangGraph Cloud deployment
  - Assistant creation and management
  - API integration and connectivity
  - Production configuration
  - Scaling considerations
- **Key Learning**: Taking agents from development to production

## Setup

### Python version

To get the most out of this course, please ensure you're using Python 3.11 or later. 
This version is required for optimal compatibility with LangGraph. If you're on an older version, 
upgrading will ensure everything runs smoothly.
```
python3 --version
```

### Clone this repository
```
git clone <this-repo-url>
cd langchain-academy
```

### Create an environment and install dependencies
#### Mac/Linux/WSL
```
$ python3 -m venv lc-academy-env
$ source lc-academy-env/bin/activate
$ pip install -r requirements.txt
```
#### Windows Powershell
```
PS> python3 -m venv lc-academy-env
PS> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
PS> lc-academy-env\scripts\activate
PS> pip install -r requirements.txt
```

### AWS Bedrock Configuration

This repository has been specifically configured to work with AWS Bedrock Nova models. The key changes include:

- **Dependencies**: `langchain-aws` is included in requirements.txt for Bedrock integration
- **Model Configuration**: All code examples use `ChatBedrock` with Nova Pro models (`us.amazon.nova-pro-v1:0`)
- **Environment Setup**: AWS credentials configuration is built into the setup process

**Prerequisites:**
1. An AWS account with access to Bedrock Nova models
2. Appropriate IAM permissions for Bedrock model access
3. AWS credentials configured (access key or IAM role)

### Setting up environment variables

Create a `.env` file in the root directory with the following variables:

```bash
# LangSmith (for tracing and monitoring)
LANGCHAIN_API_KEY=your_langchain_api_key
LANGCHAIN_TRACING_V2=true

# Tavily (for web search in Module 4)
TAVILY_API_KEY=your_tavily_api_key

# AWS Bedrock Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-west-2
```

**Important**: Replace all placeholder values with your actual API keys and credentials.

### Copy environment variables to studio directories

For convenience, a script has been provided to copy the `.env` file to all studio directories:

```bash
chmod +x copy_env.sh
./copy_env.sh
```

This will copy the `.env` file from the root directory to all studio directories in the project, ensuring LangGraph Studio can access your credentials.

## Getting Started

### Running notebooks
If you don't have Jupyter set up, follow installation instructions [here](https://jupyter.org/install).
```bash
jupyter notebook
```

### API Keys Setup

**LangSmith (Recommended for tracing):**
- Sign up for LangSmith [here](https://smith.langchain.com/)
- LangSmith provides excellent tracing and monitoring for your LangGraph applications
- Set `LANGCHAIN_API_KEY` and `LANGCHAIN_TRACING_V2=true` in your `.env` file
- Learn more about LangSmith [here](https://www.langchain.com/langsmith)

**Tavily API (Required for Module 4):**
- Tavily Search API is used for web search capabilities in research assistant examples
- Sign up for an API key [here](https://tavily.com/) - offers a generous free tier
- Set `TAVILY_API_KEY` in your `.env` file
- Only needed for Module 4 lessons involving web search

**AWS Bedrock:**
- Ensure you have access to Bedrock Nova models in your AWS account
- Configure your AWS credentials (access key/secret key or IAM role)
- Set your preferred AWS region (us-west-2 recommended for Nova model availability)

### Set up LangGraph Studio

* LangGraph Studio is a custom IDE for viewing and testing agents.
* Studio can be run locally and opened in your browser on Mac, Windows, and Linux.
* See documentation [here](https://langchain-ai.github.io/langgraph/concepts/langgraph_studio/#local-development-server) on the local Studio development server and [here](https://langchain-ai.github.io/langgraph/how-tos/local-studio/#run-the-development-server). 
* Graphs for LangGraph Studio are in the `module-x/studio/` folders.
* To start the local development server, run the following command in your terminal in the `/studio` directory each module:

```
langgraph dev
```

You should see the following output:
```
- 🚀 API: http://127.0.0.1:2024
- 🎨 Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- 📚 API Docs: http://127.0.0.1:2024/docs
```

Open your browser and navigate to the Studio UI: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`.

## What's Different in This Bedrock Nova Version

This repository contains several key modifications from the original LangChain Academy course:

### Code Changes
- **Model Integration**: All examples use `ChatBedrock` from `langchain-aws` instead of `ChatOpenAI`
- **Model Configuration**: Configured to use Amazon Nova Pro (`us.amazon.nova-pro-v1:0`) models
- **Dependencies**: Added `langchain-aws` to requirements.txt for Bedrock integration
- **Environment Setup**: AWS credential configuration built into setup process

### Key Benefits of Using Bedrock Nova
- **Enterprise Ready**: Built for enterprise use cases with AWS security and compliance
- **Cost Effective**: Competitive pricing for high-quality language model capabilities  
- **Regional Availability**: Deploy in your preferred AWS region for data residency
- **Integration**: Seamless integration with other AWS services
- **Performance**: Nova Pro offers excellent performance for agent and reasoning tasks

### Files Modified
- `requirements.txt` - Added langchain-aws dependency
- `README.md` - Updated setup instructions for Bedrock
- Code examples in studio directories - Updated to use ChatBedrock
- Environment configuration - Added AWS credential setup

### Getting Help
- For LangGraph questions: [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- For AWS Bedrock questions: [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- For course content questions: Refer to the original [LangChain Academy](https://academy.langchain.com/)