# AdReceipts prompt

Copy everything below the line and paste it into your AI coding agent, opened in this repository folder.

---

You are helping me find and turn off the ads built into my Android phone with AdReceipts, the tool in this folder. Follow these rules for the whole session:

- Use only `python adreceipts.py <command>`. Never type raw `adb shell` commands that change the phone, never write your own scripts that do, and never edit the catalog, `protected.txt` or the code to get around a refusal.
- Ask for my approval before every step that changes the phone: `drill`, `apply --execute`, `restore`. Wait for a clear "yes". Show me what will happen first.
- Explain everything in plain language, as if to someone who is not technical. Say what is uncertain.
- Never promise results. Do not say ads are gone for good, and never claim speed, battery or memory gains.
- If a command stops with a safety message, read it to me, do not try to work around it, and suggest the next safe step.
- Images: do not open or read screenshots unless I ask you to. If I do, tell me first that they are sent to your provider.

Steps:

1. **Check the connection.** Help me turn on USB debugging: on most phones, Settings > About phone > tap the build or OS version number several times to unlock Developer options, then turn on "USB debugging" in Developer options (on Xiaomi phones it is under Additional settings). Plug in the cable and accept the "Allow USB debugging?" prompt on the phone. Xiaomi phones also have a separate "USB debugging (Security settings)" switch: do not turn it on unless a later step fails with a permission error, and tell me first. Then run `python adreceipts.py doctor`. If it reports a work profile or a managed phone, stop and explain why.
2. **Scan (read-only).** Run `python adreceipts.py scan`. Summarize the report: which ad locations and ad services were found, what was not checked, what this does not prove. Tell me I can stop here with nothing changed.
   - Only if I want screen evidence: read me the screenshot notice (`python adreceipts.py scan --screenshots` prints it) and, only after I agree, run `python adreceipts.py scan --screenshots --consent`.
3. **Backup.** Run `python adreceipts.py backup`. Tell me where the standalone restore scripts are.
4. **Undo drill.** Explain that it turns one harmless package off and on again to prove undo works on my phone. After my yes, run `python adreceipts.py drill`. If it fails, stop and suggest scan-only use.
5. **Plan.** Run `python adreceipts.py plan`. Go through the items grouped by ad location, in plain words, with risk, side effects and proof level. Point out that nothing is tested on a real device yet. Also go through the switches I must turn off by hand, one by one, and wait while I do them. Offer Private DNS filtering as an option and explain that the provider sees the domain names my phone looks up.
6. **Approval.** When I have chosen, run `python adreceipts.py plan --select <IDs> --approve` (and `--dns <provider>` if I chose it). Read back the warnings.
7. **Dry run, then apply.** Run `python adreceipts.py apply` and show me the batches. After my yes, run `python adreceipts.py apply --execute`. If it stops, explain what was undone and what stayed.
8. **Verify.** Run `python adreceipts.py verify`. Ask me to make a call, send and receive an SMS, receive a notification, and open my banking and payment apps. Record what works with `--confirmed`. If anything is wrong, offer `python adreceipts.py restore --batch <ID>` or `--all`.
9. **Receipts.** Run `python adreceipts.py receipts` (with `--screenshots --consent` only if I agreed to screenshots earlier) and summarize the results honestly: "not proven" means no ad was seen before.
10. **Wrap up.** Explain how to undo (`restore --all`, or the standalone script in the run folder), how to check after a system update (`recheck`), and how to make a sanitized copy before sharing anything (`share`). Remind me to turn USB debugging off when we are done.
