import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.madinavetpet.app',
  appName: 'Madina Vet Pet',
  webDir: 'dist',
  server: {
    // Points the app at the live deployed site directly — no bundled web
    // assets are used, this is a thin native wrapper around the real app.
    // sslip.io is a free public DNS service that resolves <ip-with-dashes>.sslip.io
    // straight back to that IP — a real, publicly resolvable hostname, so
    // Caddy can obtain a genuine trusted Let's Encrypt certificate for it
    // with no purchased domain needed. This matters beyond convenience: a
    // real browser tab (used for payment) upgrades any bare-IP navigation to
    // HTTPS first and fails outright rather than falling back to HTTP, which
    // broke the Razorpay payment-link callback until this existed. Every
    // already-installed APK keeps pointing at whatever's baked in here until
    // reinstalled — update this and rebuild if the VM's IP ever changes.
    url: 'https://35-254-19-129.sslip.io',
  },
}

export default config
