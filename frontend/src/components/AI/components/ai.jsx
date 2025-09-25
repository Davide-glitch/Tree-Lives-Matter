import React, { useState, useEffect, useRef } from 'react';
import { groqService } from '../services/groqService';
import { storageService } from '../services/storageService';
import ApiKeyInput from './ApiKeyInput';
import SuggestedQuestions from './SuggestedQuestions';
import Message from './Message';
import ChatInput from './ChatInput';
import TypingIndicator from './TypingIndicator';
import { Trees, Settings, MapPin, Key, X, CheckCircle, AlertCircle } from 'lucide-react';

const ForestChatbot = ({ userLocation }) => {
  const [apiKey, setApiKey] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [showApiInput, setShowApiInput] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [hasShownLocationSuggestion, setHasShownLocationSuggestion] = useState(false);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const messagesEndRef = useRef(null);

  // Debug logging
  useEffect(() => {
    console.log('🔍 Debug - showApiInput state:', showApiInput);
    console.log('🔍 Debug - isConnected:', isConnected);
    console.log('🔍 Debug - apiKey length:', apiKey.length);
  }, [showApiInput, isConnected, apiKey]);

  // Initialize chatbot
  useEffect(() => {
    console.log('🚀 Initializing ForestChatbot...');
    
    const savedApiKey = storageService.getApiKey();
    const savedHistory = storageService.getChatHistory();

    if (savedApiKey) {
      console.log('📝 Found saved API key');
      setApiKey(savedApiKey);
      groqService.setApiKey(savedApiKey);
      testConnection(savedApiKey);
    } else {
      console.log('⚠ No saved API key found');
      // Show API input immediately if no key is saved
      setTimeout(() => setShowApiInput(true), 2000);
    }

    if (savedHistory.length > 0) {
      console.log('💬 Loading chat history:', savedHistory.length, 'messages');
      const historyWithDates = savedHistory.map(msg => ({
        ...msg,
        timestamp: new Date(msg.timestamp)
      }));
      setMessages(historyWithDates);
    } else {
      console.log('🆕 Starting fresh chat');
      setMessages([{
        id: 1,
        type: 'bot',
        content: '🌲 *Welcome to EcoForest AI!\n\nI\'m your intelligent assistant for forest conservation and environmental awareness!\n\nWhat I can help you with:\n🌍 Forest importance and biodiversity\n🛡 Deforestation causes and solutions\n📍 Forest locations and protected areas\n🌱 Conservation efforts and how to help\n🗺 Location-based forest information\n\nTo unlock full AI capabilities:* Click the ⚙ Settings button to add your Groq API key!\n\nWhat would you like to learn about forests today?',
        timestamp: new Date()
      }]);
    }
  }, []);

  // Handle location updates
  useEffect(() => {
    if (userLocation && !hasShownLocationSuggestion) {
      const locationMessage = `📍 **Location Detected:**\nCoordinates: ${userLocation.latitude.toFixed(6)}, ${userLocation.longitude.toFixed(6)}\nAccuracy: ±${Math.round(userLocation.accuracy)}m\nDetected: ${userLocation.timestamp}\n\n🌲 **Would you like me to help you discover:**\n• Forest areas near your location\n• Tourist attractions and nature spots\n• Protected areas and national parks\n• Hiking trails and eco-tourism options\n\nJust ask me about forests or tourism in your area! 🗺️`;
      
      setTimeout(() => {
        addMessage('bot', locationMessage);
        setHasShownLocationSuggestion(true);
      }, 2000);
    }
  }, [userLocation, hasShownLocationSuggestion]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Save chat history
  useEffect(() => {
    if (messages.length > 0) {
      storageService.saveChatHistory(messages);
    }
  }, [messages]);

  const testConnection = async (key = apiKey) => {
    try {
      groqService.setApiKey(key);
      await groqService.testConnection();
      setIsConnected(true);
      storageService.setApiKey(key);
      return true;
    } catch (error) {
      setIsConnected(false);
      throw error;
    }
  };

  const handleTestApiKey = async () => {
    try {
      await testConnection();
      setShowApiInput(false);
      addMessage('bot', '🎉 Great! Groq AI connected successfully! Now I can provide comprehensive information about forests and conservation efforts worldwide! 🌍🌲');
    } catch (error) {
      alert(`API Connection Error: ${error.message}`);
    }
  };

  const addMessage = (type, content) => {
    const newMessage = {
      id: Date.now(),
      type,
      content,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const handleSend = async () => {
    if (!inputValue.trim()) return;

    const userMessage = inputValue.trim();
    addMessage('user', userMessage);
    setInputValue('');
    setIsTyping(true);

    try {
      if (isConnected) {
        const conversationHistory = messages.map(msg => ({
          role: msg.type === 'user' ? 'user' : 'assistant',
          content: msg.content
        }));

        // Add location context to the message if available
        let contextualMessage = userMessage;
        if (userLocation && (userMessage.toLowerCase().includes('near') || 
                            userMessage.toLowerCase().includes('area') || 
                            userMessage.toLowerCase().includes('around') ||
                            userMessage.toLowerCase().includes('local'))) {
          contextualMessage += `\n\n[User Location Context: Latitude ${userLocation.latitude.toFixed(6)}, Longitude ${userLocation.longitude.toFixed(6)}, detected at ${userLocation.timestamp}]`;
        }

        const response = await groqService.sendMessage(
          [...conversationHistory, { role: 'user', content: contextualMessage }]
        );
        
        addMessage('bot', response);
      } else {
        // Local fallback responses with location awareness
        const response = getLocalResponse(userMessage);
        setTimeout(() => {
          addMessage('bot', response);
        }, 1000);
      }
    } catch (error) {
      addMessage('bot', `❌ Sorry, I encountered an error: ${error.message}\n\nPlease check your API key or try again later.`);
    } finally {
      setIsTyping(false);
    }
  };

  const getLocalResponse = (message) => {
    const lowerMessage = message.toLowerCase();
    
    // Location-based responses
    if (userLocation && (lowerMessage.includes('near') || lowerMessage.includes('area') || lowerMessage.includes('around'))) {
      return `🗺️ I can see you're at coordinates ${userLocation.latitude.toFixed(6)}, ${userLocation.longitude.toFixed(6)}!\n\nFor detailed information about forests, parks, and tourist attractions in your specific area, please connect your Groq API key. I'll be able to provide:\n• Nearby national parks and forests\n• Local hiking trails\n• Protected areas around you\n• Tourist attractions and eco-spots\n\nConnect your API for location-specific recommendations! 🌲📍`;
    }
    
    if (lowerMessage.includes('important') || lowerMessage.includes('why')) {
      return "🌍 Forests are crucial for our planet! They:\n• Produce oxygen and absorb CO2\n• Provide habitat for 80% of land animals\n• Regulate water cycles\n• Prevent soil erosion\n• Support indigenous communities\n\nFor detailed AI responses, please connect your Groq API key! 🔑";
    }
    
    if (lowerMessage.includes('deforestation')) {
      return "🪓 Deforestation is caused by:\n• Agriculture expansion\n• Logging for timber\n• Urban development\n• Mining activities\n• Infrastructure projects\n\nConnect Groq API for detailed solutions and information! 🌱";
    }
    
    if (lowerMessage.includes('help') || lowerMessage.includes('protect')) {
      return "🌱 You can help protect forests by:\n• Supporting sustainable products\n• Reducing paper use\n• Donating to conservation organizations\n• Planting trees locally\n• Spreading awareness\n\nConnect to Groq for personalized action plans! 💚";
    }

    if (lowerMessage.includes('forest') || lowerMessage.includes('tourism') || lowerMessage.includes('tourist')) {
      const locationText = userLocation ? `\n\n📍 I can see you're located at ${userLocation.latitude.toFixed(6)}, ${userLocation.longitude.toFixed(6)}. ` : '';
      return `🌲 That's a great question about forests and tourism!${locationText}For comprehensive AI-powered responses about forest locations, tourist attractions, and personalized recommendations, please add your Groq API key in the settings. I can provide much more detailed and location-specific information with AI enabled! 🚀`;
    }
    
    return "🌲 That's a great question about forests! For comprehensive AI-powered responses about forest conservation, deforestation, and forest information, please add your Groq API key in the settings. I can provide much more detailed and personalized information with AI enabled! 🚀";
  };

  // Updated suggested questions with location-aware options
  const getLocationAwareSuggestions = () => {
    const baseSuggestions = [
      "Why are forests important for our planet?",
      "What are the main causes of deforestation?",
      "How can I help protect forests?"
    ];

    if (userLocation) {
      return [
        "What forests and parks are near my location?",
        "Show me tourist attractions around my area",
        "Are there any protected areas near me?",
        ...baseSuggestions
      ];
    }

    return baseSuggestions;
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-red-700">
      {/* Header */}
      <div className="bg-gradient-to-r from-green-600 to-red-600 text-white p-4 shadow-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="bg-white/20 p-2 rounded-full">
              <Trees className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm opacity-90 flex items-center">
                <span className={`w-2 h-2 rounded-full mr-2 ${isConnected ? 'bg-red-300' : 'bg-yellow-300'}`}></span>
                {isConnected ? 'AI Connected' : 'Local Mode'}
                {userLocation && (
                  <>
                    <MapPin className="h-3 w-3 ml-2 mr-1" />
                    <span className="text-xs">Location Available</span>
                  </>
                )}
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowApiInput(!showApiInput)}
            className="p-2 hover:bg-white/20 rounded-full transition-colors"
            title="API Settings"
          >
            <Settings className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* API Key Input */}
      {showApiInput && (
        <ApiKeyInput
          apiKey={apiKey}
          setApiKey={setApiKey}
          onTest={handleTestApiKey}
          isConnected={isConnected}
        />
      )}

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <Message key={message.id} message={message} />
        ))}
        {isTyping && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Questions */}
      <SuggestedQuestions
        onQuestionSelect={setInputValue}
        show={messages.length <= 2}
        suggestions={getLocationAwareSuggestions()}
      />

      {/* Chat Input */}
      <ChatInput
        inputValue={inputValue}
        setInputValue={setInputValue}
        onSend={handleSend}
        disabled={isTyping}
      />
    </div>
  );
};

export default ForestChatbot;