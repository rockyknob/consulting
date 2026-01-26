
function Hero({ content }) {
  return (
    <section className="text-center py-20 bg-cover bg-center text-white rounded-lg shadow-md"
      style={{ backgroundImage: `url(${content.background_image_placeholder})` }}>
      <h1 className="text-4xl md:text-5xl font-bold">{content.headline}</h1>
      <p className="text-xl mt-4">{content.subheadline}</p>
      <a href={content.cta_link} className="inline-block mt-6 px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-full text-white font-semibold">
        {content.cta_button_text}
      </a>
    </section>
  )
}
export default Hero
