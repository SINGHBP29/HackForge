# 🧠 MindCare MCP Server

A **Mental Health Support & Counseling** backend built for the Puch AI Hackathon.  
It provides confidential and empathetic responses to users, detects mood & sentiment, understands context via NLP, and suggests resources like coping tips, mindfulness exercises, and crisis helplines.

---

## 🚀 Features

- **Accurate Mood Detection**  
  Classifies user messages into moods like happy, sad, anxious, neutral, or crisis, enabling personalized, empathetic responses.

- **Sentiment Analysis**  
  Analyzes emotional intensity and polarity to detect subtle nuances in user feelings, improving response relevance.

- **Natural Language Processing (NLP)**  
  Extracts keywords, topics, and entities using Compromise.js, allowing for context-aware conversations.

- **Crisis Detection & Emergency Response**  
  Identifies high-risk phrases related to self-harm or suicide and provides immediate, clear helpline information.

- **Multilingual Support Ready**  
  Currently supports English, with easy scalability to regional languages and dialects.

- **Voice Interaction Compatibility**  
  Designed to integrate with voice-to-text services for hands-free user experiences.

- **Quick Reply & Guided Conversation**  
  Offers interactive quick-reply buttons to guide users towards mindfulness exercises, motivational content, or direct help.

- **Customizable & Extensible**  
  Modular codebase allowing easy addition of new moods, languages, or integration with other AI tools.

- **Privacy-Centric**  
  No user data is stored permanently, ensuring confidentiality and trust.

- **Health Monitoring Endpoint**  
  `/health` endpoint for uptime monitoring and system health checks.

- **Scalable Cloud Deployment**  
  Easily deployable on platforms like Vercel, Cloudflare Workers, or AWS for global accessibility.

- **Lightweight & Fast**  
  Minimal dependencies and efficient code ensure low latency, crucial for real-time user interaction.

- **Developer-Friendly**  
  Well-structured project with clear separation of concerns, making collaboration and maintenance seamless.

---

## 📂 Project Structure
```

backend/
│── server.js               # Main entry point
│── routes/
│   └── mcp.js              # MCP API routes
│── services/
│   ├── moodDetection.js    # Mood classification logic
│   ├── response.js         # Predefined reply templates
│   └── nlpService.js       # NLP + sentiment analysis helpers
└── package.json

````

---

## 📦 Required Libraries

This project uses the following Node.js packages:

| Library          | Purpose |
|------------------|---------|
| `express`        | Web framework to create API endpoints |
| `cors`           | Enables cross-origin requests |
| `body-parser`    | Parses incoming JSON request bodies |
| `sentiment`      | Analyzes sentiment polarity and score |
| `compromise`     | Lightweight NLP for text analysis |
| `nodemon`        | Development tool for live reloading (optional) |

---

## ⚡ Getting Started

### 1️⃣ Clone the repository
```bash
git clone https://github.com/your-username/mindcare-mcp.git
cd mindcare-mcp/backend
````

### 2️⃣ Install dependencies

```bash
npm install express cors body-parser sentiment compromise
npm install --save-dev nodemon
```

### 3️⃣ Start the server

#### Development mode (auto-reload on changes)

```bash
npm run dev
```

#### Production mode

```bash
npm start
```

### 4️⃣ Server will be running at:

```
http://localhost:3000
```

---

## 📡 API Endpoints

### **Health Check**

```bash
GET /health
```

**Response**

```json
{
  "status": "ok",
  "message": "MCP server running"
}
```

### **Send a message**

```bash
POST /mcp/respond
Content-Type: application/json

{
  "user_id": "test123",
  "language": "en",
  "message_text": "I feel very anxious about my exams"
}
```

**Response Example**

```json
{
  "user_id": "test123",
  "mood": "anxious",
  "sentiment_score": -2,
  "topics": ["exams"],
  "reply_text": "😌 Take a deep breath. Try a 5-minute mindfulness exercise?",
  "quick_replies": ["Mindfulness Exercise", "Helpline"]
}
```

---

## 🛠 Tech Stack

* **Backend:** Node.js, Express
* **NLP:** Compromise.js
* **Sentiment Analysis:** Sentiment.js
* **API Middleware:** CORS, Body-Parser
* **Dev Tools:** Nodemon

---

## 🌍 Impact

By lowering barriers to mental health support and enabling early crisis detection, **MindCare MCP Server** empowers communities with a safe, private, and responsive support system.

---

## 📜 License

MIT License — free to use, modify, and share.

```