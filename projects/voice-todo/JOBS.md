# VOICE - speak it, get the list

**Goal:** on a phone, record a quick memo; get an editable to-do list of what you
said. A normal mobile browser, no account, no install, no server cost.

**The bar**
- Works on a phone browser; recording is one tap; the list appears from speech.
- Where a device cannot do speech recognition, the app says so honestly and
  keeps the audio (no silent failure).
- The parser splits real speech correctly: "buy milk and call mom tomorrow at
  five" -> two items, the second with a due date.
- `PHRASES.md`: a table of test utterances and expected parses, all passing.

**Branches**
- **V1 - recorder + transcription**: microphone capture plus on-device speech
  (Web Speech API where available), graceful fallback otherwise (audio kept,
  honest message). Mobile-first, one tap.
- **V2 - parser**: utterance -> items, dates/times in natural language, filler
  removed, conjunctions split. The test table lives with the code.
- **V3 - the app**: list UI (check, edit, reorder, delete), local persistence,
  installable to the home screen, works offline.
- **V4 - export**: copy as text, share sheet, `.ics` for dated items.
