
function Clients({ clients }) {
  return (
    <section className="py-16 bg-gray-50">
      <h2 className="text-3xl font-bold text-center mb-10">Our Clients</h2>
      <div className="flex flex-wrap justify-center gap-6">
        {clients.map((c, i) => (
          <img key={i} src={c.logo} alt={c.name} className="h-12" />
        ))}
      </div>
    </section>
  )
}
export default Clients
