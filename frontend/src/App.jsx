import React, { useEffect, useState } from 'react'

export default function App() {
  const [data, setData] = useState(null)

  useEffect(() => {
    fetch('http://localhost:8000/api/content')
      .then(res => res.json())
      .then(fetchedData => {
        setData(fetchedData);
        // This is the bridge: script.js can now see the services data
        window.customPackagesData = fetchedData.services; 
      })
      .catch(err => console.error("Error loading content:", err))
  }, [])

  if (!data) return <div className="p-4">Loading...</div>

  return (
    <div className="p-4 space-y-6">
      {/* Existing Hero Section */}
      <section className="text-center bg-blue-50 p-6 rounded-xl shadow">
        <h1 className="text-3xl font-bold">{data.hero.headline}</h1>
        <p className="text-lg text-gray-700 mt-2">{data.hero.subheadline}</p>
        <a href={data.hero.cta_link} className="inline-block mt-4 px-4 py-2 bg-blue-600 text-white rounded-full">
          {data.hero.cta_button_text}
        </a>
      </section>

      {/* --- ADDED FOR SCRIPT.JS: Service Details Area --- */}
      <div id="service-details-display-area" style={{ display: 'none' }}>
        <h2 id="details-title"></h2>
        <p id="details-description"></p>
        <ul id="details-activities-list"></ul>
        <ul id="details-documents-list"></ul>
        <div id="ai-tool-trigger-card" className="cursor-pointer bg-purple-100 p-4 rounded">
          Consult with AI Assistant
        </div>
      </div>

      {/* Existing Services Section */}
      <section id="services">
        <h2 className="text-2xl font-semibold mb-4">Our Services</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {data.services.map((srv, idx) => (
            <div key={idx} className="package-select-item bg-white p-4 rounded-lg shadow-md cursor-pointer" data-index={idx}>
              <h3 className="font-bold text-lg">{srv.title}</h3>
              <p>{srv.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* --- ADDED FOR SCRIPT.JS: AI Modal --- */}
      <div id="ai-tool-modal" className="modal-overlay" style={{ display: 'none' }}>
        <div className="modal-content bg-white p-6 rounded shadow-lg">
          <span id="ai-tool-close" className="cursor-pointer text-xl">&times;</span>
          <h2 id="ai-tool-title"></h2>
          <p id="ai-service-subtitle"></p>
          <div id="ai-chat-history" className="h-64 overflow-y-auto border p-2 my-2"></div>
          <div id="ai-prompt-suggestions" className="flex gap-2 my-2"></div>
          
          <form id="ai-query-form">
            <input type="text" id="ai-query-input" className="border p-2 w-full" />
            <button type="submit" id="ai-query-submit" className="bg-blue-500 text-white px-4 py-2 mt-2">Send</button>
          </form>
          
          <div id="ai-tool-status"></div>
          <div className="mt-4 flex gap-4">
            <button id="ai-new-chat-btn" className="text-sm underline">New Chat</button>
            <button id="ai-export-pdf-btn" className="text-sm underline">Export PDF</button>
          </div>
        </div>
      </div>
    </div>
  );
}
