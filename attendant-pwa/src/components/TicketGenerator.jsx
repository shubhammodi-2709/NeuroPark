import { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * TicketGenerator — calls POST /qr/generate once vehicle details are
 * confirmed, then renders the result as a torn-stub ticket.
 *
 * WHY the ticket shows plate/lot/slot/time even though the QR image
 * itself encodes nothing but a UUID (see backend qr_service.py): the
 * printed/displayed details are for the attendant and driver's eyes
 * only, fetched fresh from this one API response — the QR code stays
 * meaningless on its own, so a lost or photographed ticket reveals
 * nothing.
 */
export default function TicketGenerator({ vehicle, onNewEntry }) {
  const [ticket, setTicket] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchTicket() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/qr/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(vehicle),
        });

        if (!res.ok) {
          const errBody = await res.json().catch(() => ({}));
          throw new Error(errBody.detail || `Server returned ${res.status}`);
        }

        const data = await res.json();
        if (!cancelled) setTicket(data);
      } catch (err) {
        if (!cancelled) {
          setError(
            `Could not generate the ticket: ${err.message}. Check the backend ` +
              `is running — no entry has been recorded yet, so it's safe to retry.`
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchTicket();
    return () => {
      cancelled = true;
    };
  }, [vehicle]);

  if (loading) {
    return (
      <div className="text-center py-16">
        <p className="font-display uppercase tracking-wide text-asphalt-400">
          Generating ticket…
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border-2 border-stop bg-white p-6 text-center">
        <p className="font-body text-sm text-stop mb-4">{error}</p>
        <button
          onClick={onNewEntry}
          className="font-display uppercase tracking-wide text-sm bg-asphalt text-white rounded-full px-6 py-3"
        >
          Start over
        </button>
      </div>
    );
  }

  const generatedTime = new Date(ticket.generated_at).toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });

  return (
    <div className="flex flex-col gap-6 items-center">
      {/* Signature element: a ticket-stub silhouette with a hazard-
          stripe header and a perforated tear-line — echoes the printed
          parking tickets this digital flow is replacing. */}
      <div className="w-full max-w-sm rounded-2xl bg-white shadow-lg overflow-hidden">
        <div
          className="h-3 w-full"
          style={{
            backgroundImage:
              'repeating-linear-gradient(135deg, #FFC300 0 14px, #14171A 14px 28px)',
          }}
        />

        <div className="px-6 pt-5 pb-4 text-center">
          <p className="font-display uppercase tracking-widest text-xs text-asphalt-400">
            NeuroPark · Entry Ticket
          </p>
          <p className="font-mono text-2xl font-bold text-asphalt mt-1">
            {ticket.vehicle_number}
          </p>
        </div>

        <div className="px-6 grid grid-cols-2 gap-y-3 text-left font-body text-sm border-t border-dashed border-asphalt-100 pt-4 pb-5">
          <span className="text-asphalt-400">Lot</span>
          <span className="text-right font-mono">{ticket.lot_id}</span>
          <span className="text-asphalt-400">Slot</span>
          <span className="text-right font-mono">{ticket.slot_id}</span>
          <span className="text-asphalt-400">Entry time</span>
          <span className="text-right font-mono">{generatedTime}</span>
        </div>

        {/* Simulated perforation between the stub body and the QR tear-off */}
        <div className="relative">
          <div className="absolute -left-3 -top-3 w-6 h-6 rounded-full bg-asphalt-100" />
          <div className="absolute -right-3 -top-3 w-6 h-6 rounded-full bg-asphalt-100" />
          <div className="border-t-2 border-dashed border-asphalt-100" />
        </div>

        <div className="flex flex-col items-center gap-2 px-6 py-6 bg-asphalt-50">
          <img
            src={ticket.qr_image_base64}
            alt={`QR ticket for ${ticket.vehicle_number}`}
            className="w-44 h-44"
          />
          <p className="font-body text-xs text-asphalt-400 text-center">
            Scan this code at exit to calculate the fee.
          </p>
        </div>
      </div>

      <button
        onClick={onNewEntry}
        className="font-display uppercase tracking-wide text-lg bg-asphalt text-white rounded-full px-8 py-4 active:scale-[0.98] transition-transform"
      >
        New entry
      </button>
    </div>
  );
}