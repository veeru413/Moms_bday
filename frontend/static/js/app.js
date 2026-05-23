/* ============================================================
   SAVITRI'S 50th — app.js
   Change API_BASE to your deployed server URL before sharing
============================================================ */
const API_BASE = "https://moms-bday-ep58.onrender.com";

/* ── Screen routing ─────────────────────────────────────── */
function show(id) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("on"));
  const el = document.getElementById(id);
  el.classList.add("on");
  // scroll back to top in case of overflow
  el.scrollTop = 0;
}

/* ══════════════════════════════════════════════════════════
   PARTICLE SPARKLES  (tiny gold + rose dots floating around)
══════════════════════════════════════════════════════════ */
(function() {
  const c   = document.getElementById("bgCanvas");
  const ctx = c.getContext("2d");
  const PAL = ["#f9d45c","#fff3b0","#e8607a","#d4427a","#fce98a","#ffffff","#ffb3c6"];
  let W, H, pts;

  function init() {
    W = c.width  = window.innerWidth;
    H = c.height = window.innerHeight;
    pts = Array.from({length: 90}, () => ({
      x: Math.random()*W, y: Math.random()*H,
      r: Math.random()*2.2+0.4,
      vx:(Math.random()-0.5)*0.28, vy:(Math.random()-0.5)*0.28,
      a: Math.random(), da:(Math.random()*0.007+0.002)*(Math.random()>.5?1:-1),
      col: PAL[Math.floor(Math.random()*PAL.length)]
    }));
  }

  function tick() {
    ctx.clearRect(0,0,W,H);
    for (const p of pts) {
      ctx.save();
      ctx.globalAlpha = Math.max(0,Math.min(1,p.a));
      ctx.fillStyle = p.col;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, 6.283);
      ctx.fill();
      ctx.restore();
      p.x += p.vx; p.y += p.vy;
      p.a += p.da;
      if (p.a<=0||p.a>=1) p.da*=-1;
      if (p.x<0||p.x>W) p.vx*=-1;
      if (p.y<0||p.y>H) p.vy*=-1;
    }
    requestAnimationFrame(tick);
  }

  window.addEventListener("resize", init);
  init();
  tick();
})();

/* ══════════════════════════════════════════════════════════
   FLOATING EMOJIS
══════════════════════════════════════════════════════════ */
(function() {
  const box   = document.getElementById("floaters");
  const EMOJIS = ["🎈","🎉","🎊","🌸","✨","⭐","💛","❤️","💜","🌺","🎂","🥂","🌟","🎀"];

  function spawn() {
    const el = document.createElement("span");
    el.className = "floater";
    el.textContent = EMOJIS[Math.floor(Math.random()*EMOJIS.length)];
    const size = 1.4 + Math.random()*1.6;
    const dur  = 13 + Math.random()*14;
    el.style.cssText = `
      left: ${Math.random()*100}vw;
      font-size: ${size}rem;
      animation-duration: ${dur}s;
      animation-delay: ${Math.random()*3}s;
    `;
    box.appendChild(el);
    setTimeout(() => el.remove(), (dur+3)*1000);
  }

  // burst on load
  for (let i=0;i<14;i++) setTimeout(spawn, i*350);
  setInterval(spawn, 2000);
})();

/* ══════════════════════════════════════════════════════════
   CAMERA
══════════════════════════════════════════════════════════ */
let camStream = null;
const video     = document.getElementById("video");
const snapCanvas= document.getElementById("snap-canvas");
const snapCtx   = snapCanvas.getContext("2d");

document.getElementById("btn-start").addEventListener("click", async () => {
  show("s-camera");
  try {
    camStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width:{ideal:640}, height:{ideal:480} }
    });
    video.srcObject = camStream;
    document.getElementById("cam-badge").textContent = "✦ SMILE — TAP CAPTURE ✦";
  } catch(e) {
    alert("Camera access was denied.\n\nPlease allow camera permission in your browser settings and try again.");
    show("s-welcome");
  }
});

document.getElementById("btn-cam-back").addEventListener("click", () => {
  stopCam();
  show("s-welcome");
});

function stopCam() {
  if (camStream) { camStream.getTracks().forEach(t=>t.stop()); camStream=null; }
}

/* ── Capture ─────────────────────────────────────────────── */
document.getElementById("btn-capture").addEventListener("click", async () => {
  snapCanvas.width  = video.videoWidth  || 640;
  snapCanvas.height = video.videoHeight || 480;
  snapCtx.drawImage(video, 0, 0);
  const dataUrl = snapCanvas.toDataURL("image/jpeg", 0.92);
  stopCam();

  show("s-proc");
  await runSteps();

  try {
    const res  = await fetch(`${API_BASE}/api/recognize`, {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify({image: dataUrl})
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    displayResult(await res.json());
  } catch(err) {
    alert(`Could not reach the server.\n\nMake sure your backend is running at:\n${API_BASE}\n\nError: ${err.message}`);
    show("s-welcome");
  }
});

/* ── Step animation ──────────────────────────────────────── */
const delay = ms => new Promise(r=>setTimeout(r,ms));
async function runSteps() {
  for (const id of ["p1","p2","p3"]) {
    const el = document.getElementById(id);
    el.classList.add("active");
    await delay(950);
    el.classList.remove("active");
    el.classList.add("done");
  }
  await delay(400);
}

/* ══════════════════════════════════════════════════════════
   DISPLAY RESULT
══════════════════════════════════════════════════════════ */
function displayResult(data) {
  // text
  document.getElementById("result-name").textContent =
    data.matched ? `Welcome, ${data.name}! 🎉` : "Welcome, Honoured Guest! 🎉";
  document.getElementById("result-msg").textContent = data.message;

  // image
  const cardUrl = `${API_BASE}${data.card_url}`;
  document.getElementById("invite-img").src = cardUrl;

  // download button — blob approach so it actually downloads instead of opening
  const dlBtn = document.getElementById("btn-dl");
  dlBtn.href  = cardUrl;
  dlBtn.setAttribute("download", `birthday_invite_${data.name||"guest"}.png`);

  // override click to force download via blob
  dlBtn.onclick = async function(e) {
    e.preventDefault();
    try {
      const resp  = await fetch(cardUrl);
      const blob  = await resp.blob();
      const burl  = URL.createObjectURL(blob);
      const a     = Object.assign(document.createElement("a"),
                    {href:burl, download:`birthday_invite_${data.name||"guest"}.png`});
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(()=>URL.revokeObjectURL(burl), 5000);
    } catch {
      window.open(cardUrl,"_blank");
    }
  };

  show("s-result");
  launchConfetti();
}

/* ── Confetti burst ──────────────────────────────────────── */
function launchConfetti() {
  const zone = document.getElementById("confetti-zone");
  zone.innerHTML = "";
  const BITS = ["🎊","🎉","✨","⭐","💛","🌸","🎀","🌟","🎈","❤️"];

  // inject keyframe once
  if (!document.getElementById("cfall")) {
    const s = document.createElement("style");
    s.id = "cfall";
    s.textContent = `
      @keyframes cfall {
        0%   {transform:translateY(-10px) rotate(0deg)   scale(1);   opacity:1;}
        100% {transform:translateY(200px) rotate(720deg) scale(0.2); opacity:0;}
      }`;
    document.head.appendChild(s);
  }

  for (let i=0;i<28;i++) {
    const el = document.createElement("span");
    el.textContent = BITS[Math.floor(Math.random()*BITS.length)];
    const size = 0.8 + Math.random()*1.5;
    const dur  = 1.0 + Math.random()*1.4;
    el.style.cssText = `
      position:absolute;
      font-size:${size}rem;
      left:${Math.random()*100}%;
      top:0;
      animation:cfall ${dur}s ease-out ${Math.random()*0.5}s forwards;
      pointer-events:none;
    `;
    zone.appendChild(el);
  }
  setTimeout(()=>{ zone.innerHTML=""; }, 3500);
}

/* ── Retry ───────────────────────────────────────────────── */
document.getElementById("btn-retry").addEventListener("click", () => {
  document.querySelectorAll(".pstep").forEach(e=>e.classList.remove("active","done"));
  document.getElementById("invite-img").src = "";
  show("s-welcome");
});