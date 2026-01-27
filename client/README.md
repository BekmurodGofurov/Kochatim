# Ko'chatim - Client

This is the React client for the Ko'chatim greenhouse management system.

## Setup

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Environment variables**:
   Create a `.env` file in the root directory (already exists in this setup) and set the backend URL:
   ```env
   VITE_API_BASE_URL=https://api.example.com
   ```

## Development

Run the development server:
```bash
npm run dev
```
The app will be available at `http://localhost:5173`.

## Build

To create a production-ready build:
```bash
npm run build
```
The output will be in the `dist/` directory.

## Features

- **Dashboard**: Visual statistics of plant groups and varieties.
- **Inventory**: Manage plant types and quantities with quality grades.
- **Sales**: Track transaction history and revenue analytics.
- **Uzbek Localization**: Full UI translation for local users.