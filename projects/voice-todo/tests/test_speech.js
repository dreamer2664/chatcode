"use strict";
/* VOICE V1 tests with fake browser objects. Run: node tests/test_speech.js */
const assert = require("assert");
const { speechSupport, recordOnce } = require("../speech.js");

let fails = 0;
function check(name, fn) {
  return fn().then(() => console.log("PASS", name))
              .catch((e) => { fails++; console.log("FAIL", name, "-", e.message); });
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

function fakeWin(opts) {
  opts = opts || {};
  const win = {
    Blob: function (chunks) { this.chunks = chunks; },
    URL: { createObjectURL: () => "blob:fake" },
    navigator: {
      language: "en-US",
      mediaDevices: {
        getUserMedia: () => (opts.denyMic ? Promise.reject(new Error("denied"))
          : Promise.resolve({ getTracks: () => [{ stop() {} }] })),
      },
    },
  };
  win.MediaRecorder = function () {
    this.state = "inactive";
    this.start = () => {
      this.state = "recording";
      setTimeout(() => this.ondataavailable && this.ondataavailable({ data: { size: 3 } }), 5);
    };
    this.stop = () => { this.state = "inactive"; this.onstop && this.onstop(); };
  };
  if (opts.speech) {
    win.SpeechRecognition = function () {
      this.start = () => setTimeout(() => this.onresult &&
        this.onresult({ results: [[{ transcript: "buy milk" }]] }), 10);
      this.stop = () => {};
    };
  }
  return win;
}

(async () => {
  await check("support detection honest", async () => {
    assert.strictEqual(speechSupport(fakeWin({ speech: true })).speech, true);
    assert.strictEqual(speechSupport(fakeWin({})).speech, false);
    assert.strictEqual(speechSupport({ navigator: {} }).recorder, false);
  });

  await check("with Web Speech: transcript + audio kept", async () => {
    let out = null;
    const stop = recordOnce(fakeWin({ speech: true }), (r) => { out = r; });
    await wait(30); stop();
    await wait(400);
    assert(out, "callback fired");
    assert.strictEqual(out.text, "buy milk");
    assert.strictEqual(out.how, "web-speech");
    assert.strictEqual(out.kept, true);
    assert.strictEqual(out.audioUrl, "blob:fake");
  });

  await check("without Web Speech: audio kept, honest message", async () => {
    let out = null;
    const stop = recordOnce(fakeWin({}), (r) => { out = r; });
    await wait(30); stop();
    await wait(100);
    assert(out, "callback fired");
    assert.strictEqual(out.text, null);
    assert.strictEqual(out.how, "audio-kept");
    assert(/audio kept/i.test(out.message));
  });

  await check("no recorder: no silent failure", async () => {
    let out = null;
    recordOnce({ navigator: {} }, (r) => { out = r; });
    await wait(20);
    assert.strictEqual(out.how, "no-recorder");
    assert.strictEqual(out.kept, false);
    assert(/type the item/i.test(out.message));
  });

  await check("mic denied: honest, no crash", async () => {
    let out = null;
    recordOnce(fakeWin({ denyMic: true, speech: true }), (r) => { out = r; });
    await wait(20);
    assert.strictEqual(out.how, "mic-denied");
    assert(/permission/i.test(out.message));
  });

  if (fails) { console.log(fails + " failure(s)"); process.exit(1); }
  console.log("OK: all speech checks passed");
})();
