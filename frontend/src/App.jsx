import React, { useEffect, useState } from 'react'

export default function App() {
  const [data, setData] = useState(null)

  useEffect(() => {
    fetch('http://localhost:8000/api/content')
      .then(res => res.json())
      .then(setData)
      .catch(err => console.error("Error loading content:", err))
  }, [])

  if (!data) return <div className="p-4">Loading...</div>

  return (
    <div className="p-4 space-y-6">
      <section className="text-center bg-blue-50 p-6 rounded-xl shadow">
        <h1 className="text-3xl font-bold">{data.hero.headline}</h1>
        <p className="text-lg text-gray-700 mt-2">{data.hero.subheadline}</p>
        <a href={data.hero.cta_link} className="inline-block mt-4 px-4 py-2 bg-blue-600 text-white rounded-full hover:bg-blue-700">
          {data.hero.cta_button_text}
        </a>
      </section>

      <section id="services">
        <h2 className="text-2xl font-semibold mb-4">Our Services</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {data.services.map((srv, idx) => (
            <div key={idx} className="bg-white p-4 rounded-lg shadow-md">
              <img src={srv.img_placeholder} alt={srv.title} className="mb-2 rounded" />
              <h3 className="font-bold text-lg">{srv.title}</h3>
              <p>{srv.description}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
