# Product Overview

Gen AI Evaluation Platform is a multi-tenant SaaS platform for systematically testing and evaluating generative AI applications.

## Core Capabilities

- **Multi-Tenancy**: Complete data isolation between customer organizations using `customerId` field on all entities
- **Dataset Management**: Create and manage test datasets with input/output pairs for evaluation
- **Application Profiles**: Configure connections to gen AI applications via HTTP/REST or WebSocket
- **Evaluation Engine**: Execute automated evaluations against application profiles using test datasets
- **Metrics & Analytics**: Calculate accuracy, relevance, and latency metrics for AI responses
- **Results Dashboard**: Web interface for viewing, comparing, and analyzing evaluation results

## Key Entities

- **Customer**: Tenant organization (top-level isolation boundary)
- **Application Profile**: Configuration for connecting to a gen AI application
- **Dataset**: Collection of test cases with expected outputs
- **Test Case**: Single input/output pair for evaluation
- **Evaluation Run**: Execution of a dataset against an application profile
- **Response**: Individual AI application response with metrics

## Multi-Tenancy Architecture

All data operations are scoped by `customerId`:
- Database queries automatically filter by customer context
- API endpoints enforce tenant-scoped access
- Users can only access data belonging to their customer organization
- Database indexes on `customerId` ensure efficient tenant isolation
