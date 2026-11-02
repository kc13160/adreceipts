# AdReceipts plan

_2026-11-02T16:50:41+00:00_

> **SIMULATED: this report was produced with a fake phone (tests/fake_adb.py). It is not a real device result.**

> Experimental. Not yet tested on a real device. Use at your own risk and back up your data first.

## Summary

Phone: Xiaomi SIMULATED-PHONE, Android 16, system OS3.0.301.0.SIMULATED. Run: 20261102-175041.

> Only entries rated safe and tested on a real device are pre-selected. Nothing in the catalog is tested yet, so nothing is pre-selected: choose each item yourself.

Approved: yes, at 2026-11-02T16:50:41+00:00

## Changes AdReceipts can make (only after approval)

| ID | Selected | What it is | Risk | Proof | Side effects |
|---|---|---|---|---|---|
| `pkg:com.android.thememanager` | no | Themes app | advanced | documented | You can no longer change themes. Its own settings can turn ads off instead. |
| `pkg:com.mi.globalminusscreen` | no | App Vault (panel left of the home screen) | prudent | documented | The App Vault panel stops working. Its own settings can turn off ads without removing it. |
| `pkg:com.miui.analytics` | yes | Xiaomi analytics (usage data sent to Xiaomi) | safe | documented | None documented in the source. |
| `pkg:com.miui.android.fashiongallery` | yes | Wallpaper Carousel (lock screen images) | safe | documented | The lock screen stops rotating wallpapers from the carousel. |
| `pkg:com.miui.daemon` | no | Xiaomi system daemon (collects usage data) | prudent | documented | Effects of disabling the package are not well documented. One source only revokes its authorization from Settings. |
| `pkg:com.miui.hybrid` | no | Quick Apps (instant mini apps) | prudent | documented | Quick Apps links stop opening. |
| `pkg:com.miui.msa.global` | yes | Xiaomi system ads service (msa) | safe | documented | Xiaomi apps that load ads through this service may stop showing them. |
| `pkg:com.miui.player` | no | Xiaomi Music app | prudent | documented | The whole Music app stops. Its own settings can turn ads off instead. |
| `pkg:com.miui.videoplayer` | no | Mi Video app | prudent | documented | The whole Mi Video app stops. Videos may open in another player. |

## Not offered (refused by guard)

| Package | What it is | Why not |
|---|---|---|
| `com.android.providers.downloads.ui` | Downloads app | protected (catalog/protected.txt); rated 'forbidden' in the catalog |
| `com.mi.globalbrowser` | Mi Browser | holds a role right now (home, phone, SMS, browser, assistant, keyboard, WebView, admin or accessibility) |
| `com.miui.securitycenter` | Security app (hosts phone protections) | protected (catalog/protected.txt); rated 'forbidden' in the catalog |

## Switches to turn off by hand

These switches are inside the phone's menus. Turn them off by hand; AdReceipts does not tap for you.

Google advertising ID (documented):

- Open Settings.
- Open 'Privacy', then 'Ads' (on some phones: 'Google', then 'Ads').
- Tap 'Delete advertising ID' and confirm.

System ads service (msa) (documented):

- Open Settings.
- Open 'Fingerprints, face data and screen lock' (on some phones: 'Passwords & security').
- Open 'Authorization & revocation'.
- Turn off 'msa', wait a few seconds, then confirm with 'Revoke'.

Personalized ad recommendations (documented):

- Open Settings.
- Open 'Fingerprints, face data and screen lock' (or 'Passwords & security').
- Open 'Privacy', then 'Ad services'.
- Turn off 'Personalized ad recommendations'.

Security app recommendations (documented):

- Open the Security app.
- Tap the gear icon at the top right.
- Turn off 'Receive recommendations' (also called 'Show recommendations').

Cleaner recommendations (documented):

- Open the Security app, then 'Cleaner'.
- Open the Cleaner settings.
- Turn off 'Receive recommendations' (also called 'Show recommendations').

Ads in the Downloads app (documented):

- Open the Downloads app.
- Tap the menu icon at the top right, then 'Settings'.
- Turn off 'Show ads' (some versions say 'Show recommended content').

Ads in the Themes app (documented):

- Open the Themes app.
- Tap your account icon at the bottom right, then the gear icon.
- Turn off 'Show ads' and 'Personalized recommendations'.

Ads in the Music app (documented):

- Open the Music app.
- Tap the icon at the top left, then 'Settings'.
- Open 'Advanced settings'.
- Turn off 'Show ads', 'Show online recommendations on startup' and 'Personalized recommendations'.

Recommendations in Mi Video (documented):

- Open Mi Video.
- Tap the profile icon, then the gear icon.
- Turn off 'Personalized recommendations'.

Ads in Mi Browser (documented):

- Open Mi Browser.
- Tap the profile icon at the bottom right, then the gear icon.
- Open 'Advanced' and turn off 'Show ads'.
- Open 'Privacy & security' and turn off 'Personalized services'.

App suggestions in the app drawer (documented):

- Open the app drawer.
- Tap the gear icon at the top right.
- Turn off 'App recommendations' (also called 'App suggestions').

Suggested apps in home screen folders (documented):

- Open a home screen folder that shows suggested apps.
- Look for a recommendations or promoted apps option in that folder and turn it off.
- The exact control differs between phones and regions.

App Vault panel (documented):

- Open App Vault (swipe right from the first home screen).
- Tap the menu icon at the top right, then 'Manage services'.
- Turn off 'App suggestions' and 'Ads'.

## Private DNS (optional)

Private DNS sends every domain name your phone looks up to the provider you choose. It blocks some ad domains, not all ads, and it can block things you want.

- adguard: AdGuard DNS (default servers) (dns.adguard-dns.com) - https://adguard-dns.io/kb/general/dns-providers/
- mullvad: Mullvad DNS (adblock) (adblock.dns.mullvad.net) - https://mullvad.net/en/help/dns-over-https-and-dns-over-tls
- custom: your own provider hostname

Add it with: python adreceipts.py plan --dns <id>   (or --dns custom --dns-host HOST)

## What this does not promise

- A screen without an ad at one moment does not prove ads are gone for good.
- This covers ads built into the phone's own apps and screens. It does not remove ads inside other apps or YouTube.
- A DNS filter, if you choose one, blocks some ad domains, not all ads.
- No speed, battery or memory gains are claimed.

---

Generated by AdReceipts 0.1.0. Files stay on this computer.
