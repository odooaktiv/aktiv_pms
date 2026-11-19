/*
 * Environment config. Loaded before taskpane.js.
 *
 * For local testing this file is the only thing you should need to touch —
 * manifest.xml still needs its URLs pointed at the same origin by hand.
 */
window.AKTIV_CONFIG = {
  // Must match the origin serving these files AND the AppDomain + all URLs in
  // manifest.xml. Defaults to location.origin if omitted.
  ADDIN_ORIGIN: "https://portal.aktivsoftware.com/addin",

  // Shown on Odoo's "Let <name> access your Odoo database?" screen, and becomes
  // the API key label under Settings > Users > API Keys.
  FRIENDLY_NAME: "Aktiv for Outlook",

  // Odoo prefixes this -> odoo.plugin.outlook
  SCOPE: "outlook",

  // Office.auth.getAccessTokenAsync() requires a real Azure AD app registration
  // wired to <WebApplicationInfo> in the manifest. Until that exists, the licence
  // check cannot succeed and would block the whole panel — so bypass it while you
  // test the Odoo handshake, which is the part that actually has unknowns in it.
  //
  // NEVER ship a build with this true. Gate it in CI if you can.
  DEV_SKIP_LICENSE: true,
};
