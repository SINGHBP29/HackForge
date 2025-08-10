// server.js
const express = require('express');
const cors = require('cors');

const respondRoute = require('./routes/respond');
const mcpRoutes = require('./routes/mcp');

const app = express();

app.use(cors());

// Debug raw request body - for troubleshooting only
app.use((req, res, next) => {
  let data = '';
  req.on('data', chunk => {
    data += chunk;
  });
  req.on('end', () => {
    console.log('Raw body:', data);
    next();
  });
});

app.use(express.json()); // <-- important: parse JSON before routes

// Routes
app.use('/', respondRoute);
app.use('/mcp', mcpRoutes);

// Health check
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok', message: 'MCP server running with NLP features' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 MCP Server running on port ${PORT}`);
});
