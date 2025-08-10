// offlineCacheService.js
const fs = require('fs');
const path = require('path');

const CACHE_DIR = path.join(__dirname, '../cache');
if (!fs.existsSync(CACHE_DIR)) fs.mkdirSync(CACHE_DIR, { recursive: true });

function saveChat(userId, chatEntry) {
  const filePath = path.join(CACHE_DIR, `${userId}.jsonl`);
  const line = JSON.stringify(chatEntry) + '\n';
  fs.appendFileSync(filePath, line);
}

function getChatHistory(userId) {
  const filePath = path.join(CACHE_DIR, `${userId}.jsonl`);
  if (!fs.existsSync(filePath)) return [];
  const lines = fs.readFileSync(filePath, 'utf-8').split('\n').filter(Boolean);
  return lines.map(line => JSON.parse(line));
}

module.exports = { saveChat, getChatHistory };
