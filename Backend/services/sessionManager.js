// services/sessionManager.js
const sessions = {};

function getSession(user_id) {
  if (!sessions[user_id]) {
    sessions[user_id] = {
      moodHistory: [],
      lastQuestionAsked: null,
    };
  }
  return sessions[user_id];
}

function updateSession(user_id, data) {
  if (!sessions[user_id]) getSession(user_id);
  sessions[user_id] = { ...sessions[user_id], ...data };
}

module.exports = { getSession, updateSession };
