export default function ServiceCard({ icon, title, desc }) {
  return (
    <div className="w-72 bg-white shadow-lg rounded-xl p-6 hover:scale-105 transition transform">
      <div className="text-4xl mb-4">{icon}</div>
      <h3 className="text-xl font-bold text-gray-800 mb-2">{title}</h3>
      <p className="text-gray-600 text-sm">{desc}</p>
    </div>
  );
}
