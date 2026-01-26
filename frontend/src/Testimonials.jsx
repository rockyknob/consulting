
function Testimonials({ testimonials }) {
  return (
    <section className="py-16">
      <h2 className="text-3xl font-bold text-center mb-10">What Our Clients Say</h2>
      <div className="grid md:grid-cols-3 gap-8">
        {testimonials.map((t, i) => (
          <div key={i} className="bg-white shadow p-6 rounded-lg">
            <p className="italic">"{t.quote}"</p>
            <p className="mt-4 font-semibold">{t.author}</p>
            <p className="text-sm text-gray-500">{t.title}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
export default Testimonials
