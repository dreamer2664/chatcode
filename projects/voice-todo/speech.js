"use strict";
/* VOICE V1 - recorder + on-device transcription (t-20261011-40df)
 * One tap: record; transcribe with Web Speech where the device has it;
 * where it does not, KEEP THE AUDIO and say so. No account, no server.
 * All browser objects come from `win` so node tests can fake them.
 */

function speechSupport(win) {
  win = win || window;
  return {
    recorder: !!(win.MediaRecorder || (win.navigator && win.navigator.mediaDevices)),
    speech: !!(win.SpeechRecognition || win.webkitSpeechRecognition),
  };
}

/* one-tap session; cb({text, how, audioUrl, kept}) exactly once */
function recordOnce(win, cb) {
  win = win || window;
  var sup = speechSupport(win);
  if (!sup.recorder) {
    cb({ text: null, how: "no-recorder", audioUrl: null, kept: false,
         message: "This browser cannot record audio. Type the item instead." });
    return function () {};
  }
  var SR = win.SpeechRecognition || win.webkitSpeechRecognition;
  var rec = null, mr = null, chunks = [], text = null, done = false, stopRec = null;

  function finish(how, message) {
    if (done) return; done = true;
    var blob = new win.Blob(chunks, { type: "audio/webm" });
    var url = win.URL ? win.URL.createObjectURL(blob) : null;
    cb({ text: text, how: how, audioUrl: url, kept: true,
         message: message || (text ? "transcribed on-device." :
           "No on-device speech support - audio kept, listen below.") });
    if (stopRec) { try { stopRec(); } catch (e) {} }
  }

  win.navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
    mr = new win.MediaRecorder(stream);
    mr.ondataavailable = function (e) { if (e.data && e.data.size) chunks.push(e.data); };
    mr.onstop = function () {
      stream.getTracks().forEach(function (t) { t.stop(); });
      if (!SR) finish("audio-kept");
      else setTimeout(function () { finish(text ? "web-speech" : "audio-kept"); }, 250);
    };
    mr.start();
    if (SR) {
      rec = new SR();
      rec.lang = (win.navigator.language || "en-US");
      rec.interimResults = false;
      rec.onresult = function (ev) {
        var t = "";
        for (var i = 0; i < ev.results.length; i++) t += ev.results[i][0].transcript;
        text = t.trim() || null;
      };
      rec.onerror = function () { /* fall through to audio-kept */ };
      stopRec = function () { try { rec.stop(); } catch (e) {} };
      rec.start();
    }
  }).catch(function () {
    cb({ text: null, how: "mic-denied", audioUrl: null, kept: false,
         message: "Microphone blocked - permission needed. Type the item instead." });
  });

  return function stop() { if (mr && mr.state !== "inactive") mr.stop(); };
}

/* V3 hook: second tap stops (one-tap start, one-tap stop) */
function installHook(win) {
  win = win || window;
  win.voiceTodoStop = null;
  win.voiceTodoTranscribe = function (cb) {
    win.voiceTodoStop = recordOnce(win, function (r) { cb(r.text, r.how, r); });
  };
}

if (typeof module !== "undefined") {
  module.exports = { speechSupport: speechSupport, recordOnce: recordOnce, installHook: installHook };
}
if (typeof window !== "undefined") installHook(window);
