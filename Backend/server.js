// const express = require('express');
// const cors = require('cors');
// const bodyParser = require('body-parser');
// const mcpRoutes = require('./routes/mcp');

// const app = express();
// app.use(cors());
// app.use(bodyParser.json());

// // Routes
// app.use('/mcp', mcpRoutes);

// // Health check endpoint
// app.get('/health', (req, res) => {
//     res.status(200).json({ status: 'ok', message: 'MCP server running' });
// });

// // Start server
// const PORT = process.env.PORT || 3000;
// app.listen(PORT, () => {
//     console.log(`🚀 MCP Server running on port ${PORT}`);
// });
const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const mcpRoutes = require('./routes/mcp');

const app = express();
app.use(cors());
app.use(bodyParser.json());

// Routes
app.use('/mcp', mcpRoutes);

// Health check endpoint
app.get('/health', (req, res) => {
    res.status(200).json({ status: 'ok', message: 'MCP server running with NLP features' });
});

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`🚀 MCP Server running on port ${PORT}`);
});
