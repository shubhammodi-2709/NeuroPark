/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Token system: parking-signage vernacular, not a generic dark
        // theme or cream/serif default. "asphalt" is the ink/surface
        // family, "signal" is the one accent — used sparingly, the way
        // a hazard stripe or lot-full sign uses yellow against grey.
        asphalt: {
          DEFAULT: '#14171A',
          50: '#F4F5F6',
          100: '#E8E9EB',
          400: '#6B7280',
          900: '#14171A',
        },
        signal: '#FFC300', // safety-yellow — primary actions only
        go: '#1F8A57',     // confirmed / success states
        stop: '#D93025',   // errors — camera denied, OCR/network failures
      },
      fontFamily: {
        // Oswald: condensed, descended from the road-sign gothic faces
        // used on real highway/parking signage — used for headers and
        // labels, never body copy, so it stays a signal not noise.
        display: ['Oswald', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
        // Plate numbers and ticket data get a monospace face — reads
        // like a gate readout or ticket printer, not prose.
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
};