import React, { useEffect, useState, useRef } from 'react';

export default function App() {
  const [data, setData] = useState(null);
  const [selectedService, setSelectedService] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const chatEndRef = useRef(null);

  // 1. Fetch Page Content
  useEffect(() => {
    fetch('https://consulting-juxb.onrender.com/api/v1/content')
      .then(res => res.json())
      .then(setData)
      .catch(err => console.error("Error loading content:", err));
  }, []);

  // 2. Scroll to bottom of chat automatically
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  const handleAiCall = async (e) => {
    e.preventDefault();
    if (!query.trim() || !selectedService) return;

    const userMessage = { role: 'user', content: query };
    setChatHistory(prev => [...prev, userMessage]);
    setQuery("");
    setStatus("AI is thinking...");

    try {
      const res = await fetch('https://consulting-juxb.onrender.com/api/v1/ai-tool', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_query: query,
          service_name: selectedService.title,
          conversation_id: null // Or manage a local state for this
        }),
      });

      const result = await res.json();
      if (!res.ok) throw new Error(result.detail || "Error from AI");

      setChatHistory(prev => [...prev, { role: 'model', content: result.ai_response }]);
      setStatus("");
    } catch (err) {
      setStatus(`Error: ${err.message}`);
    }
  };

  if (!data) return <div className="p-8 font-sans">Initializing ZAlpha...</div>;

  return (
    <div className="p-4 max-w-6xl mx-auto space-y-8 font-sans text-gray-900">
      {/* Hero Section */}
      <section className="text-center bg-gradient-to-br from-blue-50 to-indigo-50 p-10 rounded-3xl shadow-sm">
        <h1 className="text-4xl font-extrabold tracking-tight">{data.hero.headline}</h1>
        <p className="text-xl text-gray-600 mt-4 max-w-2xl mx-auto">{data.hero.subheadline}</p>
        <button className="mt-8 px-8 py-3 bg-blue-600 text-white font-bold rounded-full hover:shadow-lg transition">
          {data.hero.cta_button_text}
        </button>
      </section>

      {/* Services Grid */}
      <section>
        <h2 className="text-3xl font-bold mb-6">Our Services</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {data.services.map((srv, idx) => (
            <div 
              key={idx} 
              onClick={() => setSelectedService(srv)}
              className={`p-6 rounded-2xl border-2 transition cursor-pointer hover:border-blue-500 shadow-sm ${selectedService?.title === srv.title ? 'border-blue-600 bg-blue-50' : 'border-gray-100 bg-white'}`}
            >
              <h3 className="font-bold text-xl">{srv.title}</h3>
              <p className="text-gray-600 mt-2 text-sm">{srv.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Detail & AI Trigger (Only shows if service selected) */}
      {selectedService && (
        <section className="bg-white border border-gray-100 p-8 rounded-3xl shadow-sm animate-fade-in">
          <h2 className="text-2xl font-bold text-blue-600">{selectedService.title}</h2>
          <p className="mt-4 text-gray-700">{selectedService.description}</p>
          <button 
            onClick={() => setIsModalOpen(true)}
            className="mt-6 flex items-center gap-2 bg-purple-600 text-white px-6 py-3 rounded-xl font-bold hover:bg-purple-700 transition"
          >
            <span>✨</span> Consult with AI Assistant
          </button>
        </section>
      )}

      {/* AI Modal (Pure React State) */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white w-full max-w-lg rounded-3xl shadow-2xl flex flex-col max-h-[85vh]">
            <div className="p-6 border-b flex justify-between items-center">
              <div>
                <h2 className="font-bold text-lg">AI Assistant</h2>
                <p className="text-xs text-gray-500">{selectedService?.title}</p>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="text-gray-400 hover:text-black text-2xl">&times;</button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {chatHistory.length === 0 && <p className="text-center text-gray-400 text-sm italic">Hello! Ask me anything about {selectedService?.title}.</p>}
              {chatHistory.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] p-3 rounded-2xl text-sm ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'}`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            <form onSubmit={handleAiCall} className="p-6 border-t bg-gray-50 rounded-b-3xl">
              <div className="flex gap-2">
                <input 
                  type="text" 
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Type your question..."
                  className="flex-1 p-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button type="submit" className="bg-blue-600 text-white px-5 py-3 rounded-xl font-bold">Send</button>
              </div>
              {status && <p className="mt-2 text-xs text-blue-600 font-medium">{status}</p>}
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
