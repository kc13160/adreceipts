# AdReceipts scan

_Xiaomi SIMULATED-PHONE, Android 16, system OS3.0.301.0.SIMULATED - 2026-11-02T17:09:19+00:00_

> **SIMULATED: this report was produced with a fake phone (tests/fake_adb.py). It is not a real device result.**

> Experimental. Not yet tested on a real device. Use at your own risk and back up your data first.

## Summary

Phone: Xiaomi SIMULATED-PHONE, Android 16, system OS3.0.301.0.SIMULATED.

Catalog used: generic/android, xiaomi/hyperos. Run: 20261102-180919.

> Nothing was changed on the phone. scan only reads. You can stop here.

> Your system (HyperOS 3) is not one of the versions the catalog sources describe (HyperOS 1, HyperOS 2). Menu names and ad locations may differ.

## Ad locations

Each place where ads can appear, and what was found. Labels say only what was observed.

| Location | Found | Details | How it is turned off | Proof level |
|---|---|---|---|---|
| Google advertising ID | `not checked` | screen: no screenshot here (not marked safe to capture) | by hand in the phone's menus | documented |
| System ads service (msa) | `ad service active`, `not checked` | com.miui.msa.global is on; screen: no screenshot here (not marked safe to capture) | by hand in the phone's menus | documented |
| Personalized ad recommendations | `not checked` | screen: no screenshot here (not marked safe to capture) | by hand in the phone's menus | documented |
| Security app recommendations | `ad seen` | ad words on screen: Ad | by hand in the phone's menus | documented |
| Cleaner recommendations | `not checked` | screen: no screenshot here (not marked safe to capture) | by hand in the phone's menus | documented |
| Ads in the Downloads app | `not checked` | screen: no screenshot here (not marked safe to capture) | by hand in the phone's menus | documented |
| Ads in the Themes app | `ad seen` | ad words on screen: Sponsored | by hand in the phone's menus | documented |
| Ads in the Music app | `not checked` | screen: no screenshot here (not marked safe to capture) | by hand in the phone's menus | documented |
| Recommendations in Mi Video | `not checked` | screen: no screenshot here (not marked safe to capture) | by hand in the phone's menus | documented |
| Ads in Mi Browser | `not checked` | screen: no screenshot here (not marked safe to capture) | by hand in the phone's menus | documented |
| App suggestions in the app drawer | `not checked` | screen: no screenshot here (not marked safe to capture) | by hand in the phone's menus | documented |
| Suggested apps in home screen folders | `not checked` | screen: no screenshot here (not marked safe to capture) | by hand in the phone's menus | documented |
| Lock screen Wallpaper Carousel | `ad service active`, `not checked` | com.miui.android.fashiongallery is on; screen: no screenshot here (not marked safe to capture) | turn off the app that serves it | documented |
| App Vault panel | `ad service active`, `not checked` | com.mi.globalminusscreen is on; screen: no screenshot here (not marked safe to capture) | by hand in the phone's menus | documented |

## Ad and tracking packages found

| Package | What it is | State | Label | Risk | Proof |
|---|---|---|---|---|---|
| `com.android.providers.downloads.ui` | Downloads app | enabled | `host app, never changed` | forbidden | documented |
| `com.android.thememanager` | Themes app | enabled | `app with ads, on` | advanced | documented |
| `com.mi.globalbrowser` | Mi Browser | enabled | `app with ads, on` | prudent | documented |
| `com.mi.globalminusscreen` | App Vault (panel left of the home screen) | enabled | `ad service active` | prudent | documented |
| `com.miui.analytics` | Xiaomi analytics (usage data sent to Xiaomi) | enabled | `ad service active` | safe | documented |
| `com.miui.android.fashiongallery` | Wallpaper Carousel (lock screen images) | enabled | `ad service active` | safe | documented |
| `com.miui.daemon` | Xiaomi system daemon (collects usage data) | enabled | `ad service active` | prudent | documented |
| `com.miui.hybrid` | Quick Apps (instant mini apps) | enabled | `ad service active` | prudent | documented |
| `com.miui.msa.global` | Xiaomi system ads service (msa) | enabled | `ad service active` | safe | documented |
| `com.miui.player` | Xiaomi Music app | enabled | `app with ads, on` | prudent | documented |
| `com.miui.securitycenter` | Security app (hosts phone protections) | enabled | `host app, never changed` | forbidden | documented |
| `com.miui.videoplayer` | Mi Video app | enabled | `app with ads, on` | prudent | documented |

## Catalog packages not on this phone

- com.miui.cleanmaster
- com.miui.systemAdSolution

## Phone settings read

| Setting | Value | Meaning |
|---|---|---|
| Private DNS mode | off | off, opportunistic (automatic) or hostname (a provider you chose). |
| Private DNS provider hostname | not set | The provider hostname, when the mode is 'hostname'. |

## Unrecognized packages with ad-like names

These are not in the catalog. They are reported only and never offered for action.

- com.google.android.adservices.api

## What this report does not prove

- A screen without an ad at one moment does not prove ads are gone for good.
- This covers ads built into the phone's own apps and screens. It does not remove ads inside other apps or YouTube.
- A DNS filter, if you choose one, blocks some ad domains, not all ads.
- No speed, battery or memory gains are claimed.

## Next steps

- Stop here if you only wanted to look. Nothing was changed.
- To continue: python adreceipts.py backup, then drill, then plan.

---

Generated by AdReceipts 0.1.0. Files stay on this computer.
