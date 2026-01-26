
function Services({ services }) {
  return (
    <section id="services" className="py-16">
      <h2 className="text-3xl font-bold text-center mb-10">Our Services</h2>
      <div className="grid md:grid-cols-3 gap-8">
        {services.map((s, i) => (
          <div key={i} className="bg-white shadow-md p-6 rounded-lg text-center">
            <img src={s.img_placeholder} alt={s.title} className="mx-auto mb-4 rounded" />
            <h3 className="text-xl font-semibold mb-2"><i className={`${s.icon} text-blue-600 mr-2`}></i>{s.title}</h3>
            <p>{s.description}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
export default Services
