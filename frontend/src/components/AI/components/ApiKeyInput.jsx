const ApiKeyInput = ({ apiKey, setApiKey, onTest, isConnected }) => {
  return (
    <div className="p-4 bg-green-50 border-b border-green-400">
      <p className="text-sm text-green-800 mb-3 flex items-center">
        🔑 <span className="ml-2">Add Groq API Key for complete forest AI responses:</span>
      </p>
      <div className="flex space-x-2 ">
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="gsk_..."
          className="flex-1 px-3 py-2 text-sm border border-green-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
        />
        <button
          onClick={onTest}
          disabled={!apiKey.trim()}
          className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:bg-gray-400 transition-colors"
        >
          Add Key
        </button>
      </div>
      <p className="text-xs text-green-600 mt-2">
        Get free from: <span className="font-mono text-black">console.groq.com</span>
      </p>
      {isConnected && (
        <p className="text-xs text-green-700 mt-1 flex items-center">
          ✅ <span className="ml-1">Connected successfully!</span>
        </p>
      )}
    </div>
  );
};

export default ApiKeyInput;