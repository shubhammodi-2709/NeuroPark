import { useRef, useState, useCallback, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * CameraOCR — opens the rear camera, lets the attendant snap a photo
 * of the plate, and sends it to the backend's /ocr/read-plate endpoint.
 *
 * WHY we capture a single still frame via <canvas> instead of streaming
 * video to the server: EasyOCR needs one sharp frame, not a stream, and
 * sending one JPEG keeps mobile data usage and server load low — this
 * runs on an attendant's phone in a parking lot, often on mobile data,
 * not a reliable office wifi connection.
 *
 * onDetected(result) is called with the exact shape the backend
 * returns: { success, plate_number, confidence, raw_detections, message }
 */
export default function CameraOCR({ onDetected }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  const [cameraError, setCameraError] = useState(null);
  const [capturing, setCapturing] = useState(false);
  const [ocrError, setOcrError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function startCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 } },
          audio: false,
        });
        if (cancelled) {
          // Component unmounted while permission dialog was open —
          // stop the stream immediately instead of leaking the camera.
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
      } catch (err) {
        // WHY we distinguish NotAllowedError specifically: it's by far
        // the most common failure (attendant taps "block" by habit),
        // and the fix (browser settings) is different from every other
        // camera error, so a generic message would send them down the
        // wrong troubleshooting path.
        setCameraError(
          err.name === 'NotAllowedError'
            ? 'Camera access was denied. Enable camera permission for this site in your browser settings, then reload the page.'
            : `Could not access the camera: ${err.message}`
        );
      }
    }

    startCamera();

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const capture = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current) return;
    setOcrError(null);
    setCapturing(true);

    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);

    canvas.toBlob(
      async (blob) => {
        if (!blob) {
          setOcrError('Could not capture a frame from the camera. Try again.');
          setCapturing(false);
          return;
        }

        const formData = new FormData();
        formData.append('file', blob, 'plate.jpg');

        try {
          const res = await fetch(`${API_BASE}/ocr/read-plate`, {
            method: 'POST',
            body: formData,
          });

          if (!res.ok) {
            const errBody = await res.json().catch(() => ({}));
            throw new Error(errBody.detail || `Server returned ${res.status}`);
          }

          const result = await res.json();
          onDetected(result);
        } catch (err) {
          setOcrError(
            `Plate reading failed: ${err.message}. Check that the backend is ` +
              `running at ${API_BASE}, or enter the plate number manually below.`
          );
        } finally {
          setCapturing(false);
        }
      },
      'image/jpeg',
      0.9
    );
  }, [onDetected]);

  // WHY a manual-entry escape hatch exists on every failure path: a
  // broken camera or a down backend should never fully block an
  // attendant from checking a vehicle in — that's a business-critical
  // path, not a nice-to-have.
  const skipToManualEntry = () => {
    onDetected({
      success: false,
      plate_number: null,
      confidence: 0,
      raw_detections: [],
      message: 'Entered manually — OCR skipped.',
    });
  };

  if (cameraError) {
    return (
      <div className="rounded-2xl border-2 border-stop bg-white p-6 text-center">
        <p className="font-body text-sm text-stop mb-4">{cameraError}</p>
        <button
          onClick={skipToManualEntry}
          className="font-display uppercase tracking-wide text-sm bg-asphalt text-white rounded-full px-6 py-3"
        >
          Enter plate manually instead
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="relative overflow-hidden rounded-2xl bg-asphalt aspect-[4/3]">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="h-full w-full object-cover"
        />
        {/* Viewfinder guide — helps the attendant frame the plate
            consistently, which measurably improves OCR accuracy without
            needing a full CV preprocessing pipeline (dropped per the
            project's tech constraints). */}
        <div className="pointer-events-none absolute inset-x-8 top-1/2 -translate-y-1/2 h-20 rounded-lg border-2 border-signal/80" />
        <canvas ref={canvasRef} className="hidden" />
      </div>

      {ocrError && (
        <p className="font-body text-sm text-stop bg-stop/10 rounded-lg px-4 py-3">
          {ocrError}
        </p>
      )}

      <button
        onClick={capture}
        disabled={capturing}
        className="font-display uppercase tracking-wide text-lg bg-signal text-asphalt rounded-full py-4 disabled:opacity-60 active:scale-[0.98] transition-transform"
      >
        {capturing ? 'Reading plate…' : 'Capture plate'}
      </button>

      <button
        onClick={skipToManualEntry}
        className="font-body text-sm text-asphalt-400 underline underline-offset-2"
      >
        Skip — enter manually
      </button>
    </div>
  );
}