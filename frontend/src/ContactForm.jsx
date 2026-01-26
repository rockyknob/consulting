
import { useForm } from 'react-hook-form'

function ContactForm() {
  const { register, handleSubmit, reset } = useForm()

  const onSubmit = async (data) => {
    const res = await fetch('http://localhost:8000/api/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (res.ok) {
      alert('Thank you for your inquiry!')
      reset()
    } else {
      alert('Something went wrong.')
    }
  }

  return (
    <section className="py-16" id="contact">
      <h2 className="text-3xl font-bold text-center mb-8">Contact Us</h2>
      <form onSubmit={handleSubmit(onSubmit)} className="max-w-2xl mx-auto grid gap-4">
        <input {...register("name", { required: true })} placeholder="Name" className="border p-2 rounded" />
        <input {...register("email", { required: true })} placeholder="Email" type="email" className="border p-2 rounded" />
        <input {...register("company")} placeholder="Company (Optional)" className="border p-2 rounded" />
        <input {...register("phone")} placeholder="Phone (Optional)" className="border p-2 rounded" />
        <input {...register("subject", { required: true })} placeholder="Subject" className="border p-2 rounded" />
        <textarea {...register("message", { required: true })} placeholder="Message" className="border p-2 rounded" rows="5" />
        <button type="submit" className="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700">Submit</button>
      </form>
    </section>
  )
}
export default ContactForm
