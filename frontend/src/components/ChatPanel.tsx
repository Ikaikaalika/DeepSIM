import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Send, MessageSquare, Bot, User, Loader } from 'lucide-react';
import { apiService } from '../services/api';
import { LLMResponse, SimulationResults } from '../types';

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  data?: any;
}

interface ChatPanelProps {
  flowsheetId: string | null;
  simulationResults: SimulationResults | null;
}

const ChatPanel: React.FC<ChatPanelProps> = ({ flowsheetId, simulationResults }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      type: 'assistant',
      content: 'Hello! I\'m your AI assistant for DeepSim. I can help you design, modify, and analyze chemical processes. What would you like to work on today?',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = useCallback(async () => {
    const trimmedInput = input.trim();
    
    // Client-side validation
    if (!trimmedInput || isLoading) return;
    
    if (trimmedInput.length > 5000) {
      alert('Message is too long. Please keep it under 5000 characters.');
      return;
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: trimmedInput,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const context = simulationResults ? { simulation_results: simulationResults } : undefined;
      const response: LLMResponse = await apiService.chatWithLLM(
        trimmedInput,
        flowsheetId || undefined,
        context
      );

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.message,
        timestamp: new Date(),
        data: response,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (response.action === 'update_flowsheet' && response.flowsheet_update && flowsheetId) {
        window.location.reload();
      }
    } catch (error) {
      console.error('Chat error:', error);
      
      let errorContent = 'I apologize, but I encountered an error processing your request. Please try again.';
      
      if (error instanceof Error) {
        if (error.message.includes('Network')) {
          errorContent = 'Unable to connect to the server. Please check your network connection.';
        } else if (error.message.includes('validation')) {
          errorContent = 'There was a validation error with your request. Please check your input and try again.';
        }
      }
      
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: errorContent,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    }

    setIsLoading(false);
  }, [input, isLoading, flowsheetId, simulationResults]);

  const handleKeyPress = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    },
    [sendMessage]
  );

  const renderMessage = (message: ChatMessage) => {
    const isUser = message.type === 'user';
    
    return (
      <div key={message.id} className={`flex gap-3 mb-4 ${isUser ? 'flex-row-reverse' : ''}`}>
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-blue-500' : 'bg-gray-500'
        }`}>
          {isUser ? <User size={16} className="text-white" /> : <Bot size={16} className="text-white" />}
        </div>
        
        <div className={`flex-1 ${isUser ? 'text-right' : ''}`}>
          <div className={`inline-block p-3 rounded-lg max-w-[85%] ${
            isUser
              ? 'bg-blue-500 text-white ml-auto'
              : 'bg-gray-100 text-gray-900'
          }`}>
            <div className="text-sm whitespace-pre-wrap">{message.content}</div>
          </div>
          
          {message.data && message.data.analysis && (
            <div className="mt-2 p-3 bg-blue-50 rounded-lg border border-blue-200">
              <h4 className="font-medium text-blue-900 mb-2">Analysis</h4>
              <div className="text-sm text-blue-800 space-y-2">
                {Object.entries(message.data.analysis).map(([key, value]) => (
                  <div key={key}>
                    <span className="font-medium">{key.replace(/_/g, ' ')}:</span>
                    <div className="ml-2">
                      {typeof value === 'object' && value !== null ? (
                        <ul className="list-disc list-inside">
                          {Object.entries(value).map(([subKey, subValue]) => (
                            <li key={subKey}>{subKey}: {String(subValue)}</li>
                          ))}
                        </ul>
                      ) : (
                        String(value)
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {message.data && message.data.recommendations && (
            <div className="mt-2 p-3 bg-green-50 rounded-lg border border-green-200">
              <h4 className="font-medium text-green-900 mb-2">Recommendations</h4>
              <ul className="text-sm text-green-800 list-disc list-inside space-y-1">
                {message.data.recommendations.map((rec: string, index: number) => (
                  <li key={index}>{rec}</li>
                ))}
              </ul>
            </div>
          )}
          
          <div className="text-xs text-gray-500 mt-1">
            {message.timestamp.toLocaleTimeString()}
          </div>
        </div>
      </div>
    );
  };

  const suggestedQuestions = [
    "Create a methanol production process",
    "Add a heater before the reactor",
    "Why is the conversion low?",
    "Increase reactor temperature to 300°C",
    "Analyze the simulation results",
  ];

  return (
    <div className="h-full bg-white flex flex-col">
      <div className="flex items-center gap-2 p-4 border-b border-gray-200">
        <MessageSquare size={20} className="text-gray-700" />
        <h3 className="text-lg font-medium text-gray-900">AI Assistant</h3>
        {!flowsheetId && (
          <span className="ml-auto text-xs text-orange-600 bg-orange-100 px-2 py-1 rounded">
            No flowsheet
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {messages.map(renderMessage)}
        
        {isLoading && (
          <div className="flex gap-3 mb-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-500 flex items-center justify-center">
              <Bot size={16} className="text-white" />
            </div>
            <div className="flex-1">
              <div className="inline-block p-3 rounded-lg bg-gray-100">
                <Loader size={16} className="animate-spin text-gray-600" />
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {messages.length === 1 && (
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Try asking:</h4>
          <div className="space-y-1">
            {suggestedQuestions.map((question, index) => (
              <button
                key={index}
                onClick={() => setInput(question)}
                className="block w-full text-left text-sm text-blue-600 hover:text-blue-800 p-2 rounded hover:bg-blue-50"
              >
                "{question}"
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="p-4 border-t border-gray-200">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me anything about your process..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 resize-none"
            rows={2}
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;