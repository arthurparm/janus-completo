const express = require('express');
const cors = require('cors');
const { EventEmitter } = require('events');

const app = express();
const PORT = 8000;

// Middleware
app.use(cors());
app.use(express.json());

// Mock data
const mockConversations = [
  {
    id: '9',
    title: 'Conversa de Teste',
    last_message: 'Olá, tudo bem?',
    updated_at: new Date().toISOString(),
    message_count: 1,
    tags: ['teste'],
    status: 'active'
  }
];

const mockMessages = {
  '9': [
    {
      role: 'user',
      content: 'Olá, tudo bem?',
      timestamp: new Date().toISOString()
    }
  ]
};

// Health check
app.get('/healthz', (req, res) => {
  console.log('[MockServer] Health check request');
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Get conversation history
app.get('/api/v1/chat/:conversationId', (req, res) => {
  const { conversationId } = req.params;
  console.log(`[MockServer] Get conversation: ${conversationId}`);
  
  const messages = mockMessages[conversationId] || [];
  res.json({ messages });
});

// Send message (traditional API)
app.post('/api/v1/chat/:conversationId', (req, res) => {
  const { conversationId } = req.params;
  const { message } = req.body;
  
  console.log(`[MockServer] Send message to ${conversationId}:`, message);
  
  // Add user message
  if (!mockMessages[conversationId]) {
    mockMessages[conversationId] = [];
  }
  mockMessages[conversationId].push({
    role: 'user',
    content: message,
    timestamp: new Date().toISOString()
  });
  
  // Simulate AI response
  setTimeout(() => {
    const aiResponse = {
      role: 'assistant',
      content: 'Olá! Estou bem, obrigado. Como posso te ajudar hoje?',
      timestamp: new Date().toISOString()
    };
    
    mockMessages[conversationId].push(aiResponse);
    
    res.json({
      assistant_message: aiResponse,
      citations: []
    });
  }, 1000);
});

// SSE Streaming endpoint
app.get('/api/v1/chat/stream/:conversationId', (req, res) => {
  const { conversationId } = req.params;
  const message = req.query.message;
  
  console.log(`[MockServer] SSE stream for ${conversationId}:`, message);
  
  // Set up SSE headers
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Cache-Control',
  });
  
  // Add user message
  if (!mockMessages[conversationId]) {
    mockMessages[conversationId] = [];
  }
  mockMessages[conversationId].push({
    role: 'user',
    content: message,
    timestamp: new Date().toISOString()
  });
  
  // Send events
  res.write('event: start\ndata: {}\n\n');
  res.write('event: ack\ndata: {}\n\n');
  
  // Simulate streaming response
  const response = 'Olá! Estou bem, obrigado. Como posso te ajudar hoje?';
  const words = response.split(' ');
  let wordIndex = 0;
  
  const sendWord = () => {
    if (wordIndex < words.length) {
      const partial = words.slice(0, wordIndex + 1).join(' ');
      res.write(`event: partial\ndata: {"text": "${partial}"}\n\n`);
      wordIndex++;
      setTimeout(sendWord, 200);
    } else {
      // Send final event
      const finalMessage = {
        conversation_id: conversationId,
        provider: 'mock',
        model: 'mock-v1',
        citations: []
      };
      res.write(`event: done\ndata: ${JSON.stringify(finalMessage)}\n\n`);
      
      // Add to mock messages
      mockMessages[conversationId].push({
        role: 'assistant',
        content: response,
        timestamp: new Date().toISOString()
      });
      
      setTimeout(() => {
        res.end();
      }, 100);
    }
  };
  
  setTimeout(sendWord, 500);
});

// Get conversations list
app.get('/api/v1/conversations', (