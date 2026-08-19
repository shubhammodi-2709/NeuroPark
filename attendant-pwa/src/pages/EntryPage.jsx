import { useState } from 'react';
import CameraOCR from '../components/CameraOCR';
import TicketGenerator from '../components/TicketGenerator';

/**
 * EntryPage — the attendant's main workflow: capture plate -> confirm
 * details -> show ticket.
 *
 * WHY three explicit steps instead of one big form: each step depends
 * on the previous one's result (the OCR guess pre-fills the confirm
 * form; the confirmed form feeds ticket generation), and a clear
 * "what step am I on" matters when an attendant runs this dozens of
 * times a shift, often one-handed, sometimes mid-conversation with a driver.
 *
 * NOTE on lot_id / slot_id: these are free-text fields for now because
 * the 'lots' collection isn't seeded until Week 2.2. Once /lots exists,
 * swap this text input for a dropdown populated from GET /lots — the
 * rest of this flow doesn't need to change.
 */
export default function EntryPage() {
  const [step, setStep] = useState('capture'); // 'capture' | 'confirm' | 'ticket'
  const [ocrResult, setOcrResult] = useState(null);
  const [form, setForm] = useState({ vehicle_number: '', lot_id: '', slot_id: '' });
  const [confirmedVehicle, setConfirmedVehicle] = useState(null);

  const handleDetected = (result) => {
    setOcrResult(result);
    setForm((f) => ({ ...f, vehicle_number: result.plate_number || '' }));
    setStep('confirm');
  };

  const handleConfirm = (e) => {
    e.preventDefault();
    setConfirmedVehicle({ ...form });
    setStep('ticket');
  };

  const reset = () => {
    setStep('capture');
    setOcrResult(null);
    setForm({ vehicle_number: '', lot_id: '', slot_id: '' });
    setConfirmedVehicle(null);
  };

  const steps = [
    { key: 'capture', label: 'Capture' },
    { key: 'confirm', label: 'Confirm' },
    { key: 'ticket', label: 'Ticket' },
  ];
  const currentIndex = steps.findIndex((s) => s.key === step);

  return (
    <div className="min-h-screen bg-asphalt-100 flex flex-col">
      <header className="bg-asphalt text-white px-5 py-4">
        <h1 className="font-display uppercase tracking-wide text-lg">
          NeuroPark · Entry
        </h1>
        {/* Step indicator — this genuinely is a sequence (each step
            unlocks the next), so marking progress here encodes real
            information rather than decorating the header. */}
        <div className="flex items-center gap-2 mt-3">
          {steps.map((s, i) => (
            <div
              key={s.key}
              className={`h-1.5 flex-1 rounded-full ${
                i <= currentIndex ? 'bg-signal' : 'bg-white/20'
              }`}
            />
          ))}
        </div>
      </header>

      <main className="flex-1 px-5 py-6 max-w-sm mx-auto w-full">
        {step === 'capture' && <CameraOCR onDetected={handleDetected} />}

        {step === 'confirm' && (
          <form onSubmit={handleConfirm} className="flex flex-col gap-4">
            {ocrResult && !ocrResult.success && (
              <p className="font-body text-sm text-asphalt-400 bg-white rounded-lg px-4 py-3">
                {ocrResult.message}
              </p>
            )}

            <label className="flex flex-col gap-1">
              <span className="font-body text-xs uppercase tracking-wide text-asphalt-400">
                Vehicle number
              </span>
              <input
                required
                value={form.vehicle_number}
                onChange={(e) =>
                  setForm((f) => ({ ...f, vehicle_number: e.target.value.toUpperCase() }))
                }
                placeholder="UP16AB1234"
                className="font-mono text-lg rounded-xl border border-asphalt-100 bg-white px-4 py-3 focus:outline-none focus:ring-2 focus:ring-signal"
              />
            </label>

            <label className="flex flex-col gap-1">
              <span className="font-body text-xs uppercase tracking-wide text-asphalt-400">
                Lot ID
              </span>
              <input
                required
                value={form.lot_id}
                onChange={(e) => setForm((f) => ({ ...f, lot_id: e.target.value.toUpperCase() }))}
                placeholder="LOT001"
                className="font-mono text-lg rounded-xl border border-asphalt-100 bg-white px-4 py-3 focus:outline-none focus:ring-2 focus:ring-signal"
              />
            </label>

            <label className="flex flex-col gap-1">
              <span className="font-body text-xs uppercase tracking-wide text-asphalt-400">
                Slot ID
              </span>
              <input
                required
                value={form.slot_id}
                onChange={(e) => setForm((f) => ({ ...f, slot_id: e.target.value.toUpperCase() }))}
                placeholder="A-12"
                className="font-mono text-lg rounded-xl border border-asphalt-100 bg-white px-4 py-3 focus:outline-none focus:ring-2 focus:ring-signal"
              />
            </label>

            <button
              type="submit"
              className="font-display uppercase tracking-wide text-lg bg-signal text-asphalt rounded-full py-4 mt-2 active:scale-[0.98] transition-transform"
            >
              Generate ticket
            </button>
            <button
              type="button"
              onClick={() => setStep('capture')}
              className="font-body text-sm text-asphalt-400 underline underline-offset-2"
            >
              Retake photo
            </button>
          </form>
        )}

        {step === 'ticket' && confirmedVehicle && (
          <TicketGenerator vehicle={confirmedVehicle} onNewEntry={reset} />
        )}
      </main>
    </div>
  );
}