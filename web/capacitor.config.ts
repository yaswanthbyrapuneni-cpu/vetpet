import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.madinavetpet.app',
  appName: 'Madina Vet Pet',
  webDir: 'dist',
  server: {
    // Points the app at the live deployed site directly — no bundled web
    // assets are used, this is a thin native wrapper around the real app.
    // No domain yet, so this is a plain-HTTP IP:port; cleartext must stay
    // true until that's replaced with a real https:// domain, at which
    // point this whole `server` block should be removed (or updated) and
    // the app rebuilt — every already-installed APK keeps pointing at
    // whatever's baked in here until reinstalled.
    url: 'http://35.254.19.129:18080',
    cleartext: true,
  },
}

export default config
