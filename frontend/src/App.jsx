import ServiceCard from "./components/ServiceCard";

function App() {
  return (
    <div>
      <section className="bg-gradient-to-b from-white to-green-50 py-24 text-center px-6">
        <h1 className="text-5xl font-bold text-gray-800 mb-4">
          Unlock Your Business Potential Through <br /> Strategic Innovation
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto mb-6">
          Partnering with leaders to solve their toughest challenges and capture their greatest opportunities.
        </p>
        <button className="bg-blue-500 text-white px-6 py-3 rounded-full hover:bg-blue-600 transition">
          Discover Our Solutions
        </button>
      </section>

      <section className="py-16 bg-white text-center">
        <h2 className="text-3xl font-semibold text-green-700 mb-10">Our Services</h2>
        <div className="flex flex-wrap justify-center gap-8 px-4">
          <ServiceCard icon="💡" title="Strategic Transformation" desc="Navigate market shifts and achieve sustainable growth efficiently." />
          <ServiceCard icon="🚀" title="Digital Acceleration" desc="Utilize data, AI, and tech to optimize operations." />
          <ServiceCard icon="📈" title="Performance Improvement" desc="Unlock hidden value, streamline and re-engineer processes." />
        </div>
      </section>

      <section className="bg-gray-50 py-12 text-center">
        <p className="italic text-gray-700 max-w-3xl mx-auto mb-4">
          “SynergyPro’s insights into digital transformation were instrumental in reshaping our customer experience
          and driving significant growth. Their team is world-class.”
        </p>
        <p className="font-bold text-gray-900">Eleanor Vance</p>
        <p className="text-sm text-gray-500">Chief Technology Officer, Global Tech Corp</p>
      </section>
    </div>
  );
}

export default App;
