# Frontend - Gen AI Evaluation Platform

React TypeScript frontend with Material-UI.

## Quick Start

```bash
# Setup
npm install
cp .env.example .env

# Run dev server
npm run dev
```

App runs at http://localhost:3000

## Testing

```bash
npm test                  # Run all tests
npm run test:watch        # Watch mode
npm run test:coverage     # With coverage
```

## Building

```bash
npm run build            # Production build
npm run preview          # Preview build
```

## Project Structure

```
frontend/
├── src/
│   ├── main.tsx         # Entry point
│   ├── App.tsx          # Root component
│   ├── components/      # Reusable UI components
│   ├── views/           # Page-level components
│   ├── services/        # API client
│   ├── types/           # TypeScript types
│   ├── contexts/        # React contexts
│   └── utils/           # Utilities
└── tests/
    ├── unit/            # Unit tests
    └── properties/      # Property-based tests
```

## Environment Variables

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Technology

- React 18.3.1 + TypeScript 5.7.3
- Material-UI 6.3.1
- Vite 6.0.7
- Jest 29.7.0 + React Testing Library
- fast-check 3.24.2 (property-based testing)
