# Gen AI Evaluation Platform - Frontend

React TypeScript frontend for the Gen AI Evaluation Platform.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API base URL if different from default
```

3. Start the development server:
```bash
npm run dev
```

The application will be available at http://localhost:3000

## Testing

Run all tests:
```bash
npm test
```

Run tests in watch mode:
```bash
npm run test:watch
```

Run tests with coverage:
```bash
npm run test:coverage
```

## Building

Build for production:
```bash
npm run build
```

Preview production build:
```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── main.tsx             # Application entry point
│   ├── App.tsx              # Root component
│   ├── components/          # Reusable UI components
│   ├── views/               # Page-level components
│   ├── services/            # API client services
│   ├── types/               # TypeScript type definitions
│   ├── contexts/            # React contexts
│   └── utils/               # Utility functions
├── tests/
│   ├── unit/                # Unit tests
│   ├── properties/          # Property-based tests
│   └── setup.ts             # Test setup
├── public/                  # Static assets
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## Technology Stack

- **React 18**: UI library
- **TypeScript**: Type-safe JavaScript
- **Material-UI**: Component library
- **Vite**: Build tool and dev server
- **React Router**: Client-side routing
- **Axios**: HTTP client
- **Recharts**: Data visualization
- **Jest**: Testing framework
- **React Testing Library**: Component testing
- **fast-check**: Property-based testing
