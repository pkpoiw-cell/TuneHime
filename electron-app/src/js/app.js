// AI Live Tuner — Frontend Application
(() => {
  'use strict';

  // ---------------------------------------------------------------
  // Activation system
  // ---------------------------------------------------------------
  let activationStatus = null;

  async function checkActivation() {
    if (!window.electronAPI) return;

    try {
      activationStatus = await window.electronAPI.getActivationStatus();
      console.log('Activation status:', activationStatus);

      const overlay = document.getElementById('activation-overlay');
      const app = document.querySelector('.app');
      const trialBadge = document.getElementById('trial-badge');
      const trialBadgeText = document.getElementById('trial-badge-text');
      const activatedBadge = document.getElementById('activated-badge');
      const trialSection = document.getElementById('trial-section');
      const expiredSection = document.getElementById('expired-section');
      const skipSection = document.getElementById('skip-section');

      if (activationStatus.status === 'activated') {
        // 已激活 - 隐藏覆盖层，显示激活标签
        overlay.style.display = 'none';
        app.classList.remove('locked');
        activatedBadge.style.display = 'flex';
        trialBadge.style.display = 'none';
      } else if (activationStatus.status === 'expired') {
        // 试用期已过期 - 显示激活页面，锁定功能
        overlay.style.display = 'flex';
        app.classList.add('locked');
        trialSection.style.display = 'none';
        expiredSection.style.display = 'block';
        skipSection.style.display = 'none';
        trialBadge.style.display = 'none';
        activatedBadge.style.display = 'none';
      } else {
        // 试用期内 - 显示激活页面但允许跳过
        overlay.style.display = 'flex';
        app.classList.remove('locked');
        trialSection.style.display = 'block';
        expiredSection.style.display = 'none';
        skipSection.style.display = 'block';
        trialBadge.style.display = 'flex';
        trialBadgeText.textContent = `试用 ${activationStatus.remainingDays} 天`;
        activatedBadge.style.display = 'none';
      }
    } catch (err) {
      console.error('Activation check failed:', err);
    }
  }

  function setupActivationUI() {
    const activationBtn = document.getElementById('activation-btn');
    const activationInput = document.getElementById('activation-input');
    const activationMessage = document.getElementById('activation-message');
    const skipBtn = document.getElementById('skip-btn');
    const overlay = document.getElementById('activation-overlay');
    const app = document.querySelector('.app');
    const activatedBadge = document.getElementById('activated-badge');
    const trialBadge = document.getElementById('trial-badge');

    // 激活按钮点击
    activationBtn.addEventListener('click', async () => {
      const code = activationInput.value.trim();
      if (!code) {
        activationMessage.textContent = '请输入激活码';
        activationMessage.className = 'activation-message error';
        return;
      }

      activationBtn.disabled = true;
      activationBtn.textContent = '验证中...';

      try {
        const result = await window.electronAPI.activate(code);
        if (result.success) {
          activationMessage.textContent = '激活成功！';
          activationMessage.className = 'activation-message success';
          setTimeout(() => {
            overlay.style.display = 'none';
            app.classList.remove('locked');
            trialBadge.style.display = 'none';
            activatedBadge.style.display = 'flex';
          }, 1000);
        } else {
          activationMessage.textContent = result.error || '激活码无效';
          activationMessage.className = 'activation-message error';
        }
      } catch (err) {
        activationMessage.textContent = '验证失败，请重试';
        activationMessage.className = 'activation-message error';
      }

      activationBtn.disabled = false;
      activationBtn.textContent = '激活';
    });

    // 输入框回车
    activationInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') activationBtn.click();
    });

    // 输入框自动格式化 (XXXX-XXXX-XXXX-XXXX)
    activationInput.addEventListener('input', (e) => {
      let value = e.target.value.replace(/[^A-Za-z0-9]/g, '').toUpperCase();
      if (value.length > 16) value = value.slice(0, 16);
      const parts = value.match(/.{1,4}/g) || [];
      e.target.value = parts.join('-');
    });

    // 跳过按钮（试用期内）
    skipBtn.addEventListener('click', () => {
      overlay.style.display = 'none';
    });
  }

  // ---------------------------------------------------------------
  // WebSocket connection
  // ---------------------------------------------------------------
  let ws = null;
  let wsPort = 9876;

  function connectWS() {
    if (ws && ws.readyState === WebSocket.OPEN) return;
    ws = new WebSocket(`ws://127.0.0.1:${wsPort}`);
    ws.onopen = () => {
      console.log('WS connected');
      document.getElementById('engine-status').textContent = '专业引擎 · 在线';
      send({ type: 'get_devices' });
    };
    ws.onclose = () => {
      document.getElementById('engine-status').textContent = '已断开';
      setTimeout(connectWS, 2000);
    };
    ws.onerror = () => {};
    ws.onmessage = (e) => {
      try { handleMessage(JSON.parse(e.data)); } catch {}
    };
  }

  function send(msg) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    }
  }

  // ---------------------------------------------------------------
  // Message handler
  // ---------------------------------------------------------------
  const smoothLevel = { value: 0 };
  const smoothCents = { value: 0 };
  let currentNote = '--';
  let currentFreq = 0;
  let spectrumData = new Float32Array(40);

  function handleMessage(msg) {
    switch (msg.type) {
      case 'status':
        updateFeedback(msg);
        break;
      case 'devices':
        populateDevices(msg.input || [], msg.output || []);
        break;
      case 'test_status':
        document.getElementById('test-status').textContent = msg.text;
        break;
      case 'route_status':
        document.getElementById('route-status').textContent = msg.text;
        break;
      case 'auto_status':
        document.getElementById('auto-status').innerHTML =
          `<span class="float">♪</span> ${msg.text}`;
        break;
      case 'key_detected':
        document.getElementById('param-root').value = msg.root;
        document.getElementById('param-scale').value = msg.scale === 'major' ? '大调' : msg.scale === 'minor' ? '小调' : '半音阶';
        document.getElementById('engine-status').textContent =
          `已识别: ${msg.root} ${msg.scale === 'major' ? '大调' : '小调'}`;
        break;
    }
  }

  function updateFeedback(msg) {
    const pitch = msg.frequency;
    document.getElementById('fb-pitch').textContent =
      pitch ? `${pitch.toFixed(1)} Hz` : '-- Hz';
    document.getElementById('fb-target').textContent = msg.target || '--';
    document.getElementById('fb-shift').textContent =
      `${(msg.semitones || 0).toFixed(2)} st`;

    if (msg.target) currentNote = msg.target;
    if (pitch) currentFreq = pitch;
    if (msg.cents !== undefined) smoothCents.target = msg.cents;
    if (msg.level !== undefined) smoothLevel.target = msg.level;
    if (msg.spectrum) spectrumData = new Float32Array(msg.spectrum);
    if (msg.auto_status) {
      document.getElementById('auto-status').innerHTML =
        `<span class="float">♪</span> ${msg.auto_status}`;
    }
  }

  // ---------------------------------------------------------------
  // Device list
  // ---------------------------------------------------------------
  function populateDevices(inputs, outputs) {
    const inputSel = document.getElementById('input-device');
    const outputSel = document.getElementById('output-device');
    inputSel.innerHTML = inputs.map(n => `<option>${n}</option>`).join('');
    outputSel.innerHTML = outputs.map(n => `<option>${n}</option>`).join('');
  }

  // ---------------------------------------------------------------
  // Tabs
  // ---------------------------------------------------------------
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(`panel-${tab.dataset.tab}`).classList.add('active');
    });
  });

  // ---------------------------------------------------------------
  // Window controls
  // ---------------------------------------------------------------
  document.getElementById('btn-minimize')?.addEventListener('click', () => window.electronAPI?.minimize());
  document.getElementById('btn-maximize')?.addEventListener('click', () => window.electronAPI?.maximize());
  document.getElementById('btn-close')?.addEventListener('click', () => window.electronAPI?.close());

  // ---------------------------------------------------------------
  // Live tab controls
  // ---------------------------------------------------------------
  document.getElementById('btn-start').addEventListener('click', () => {
    send({ type: 'start', auto_mode: true });
  });
  document.getElementById('btn-stop').addEventListener('click', () => {
    send({ type: 'stop' });
  });
  document.getElementById('btn-refresh-devices').addEventListener('click', () => {
    send({ type: 'get_devices' });
  });
  document.getElementById('auto-mode').addEventListener('change', (e) => {
    send({ type: 'config', key: 'auto_mode', value: e.target.checked });
  });

  // ---------------------------------------------------------------
  // Settings sliders
  // ---------------------------------------------------------------
  const sliderMap = [
    ['sl-amount', 'sv-amount', 'amount', 0.01],
    ['sl-speed', 'sv-speed', 'speed', 0.01],
    ['sl-mix', 'sv-mix', 'mix', 0.01],
    ['sl-gate', 'sv-gate', 'gate', 0.01],
    ['sl-comp', 'sv-comp', 'compression', 0.01],
    ['sl-bright', 'sv-bright', 'brightness', 0.01],
    ['sl-deess', 'sv-deess', 'deesser', 0.01],
    ['sl-reverb', 'sv-reverb', 'reverb', 0.01],
    ['sl-gain', 'sv-gain', 'gain', 0.01],
  ];

  sliderMap.forEach(([sliderId, valId, key, scale]) => {
    const slider = document.getElementById(sliderId);
    const valLabel = document.getElementById(valId);
    if (!slider) return;
    slider.addEventListener('input', () => {
      const v = (parseFloat(slider.value) * scale).toFixed(2);
      valLabel.textContent = v;
      send({ type: 'config', key, value: parseFloat(v) });
    });
  });

  // Root / Scale
  document.getElementById('param-root')?.addEventListener('change', (e) => {
    send({ type: 'config', key: 'root', value: e.target.value });
  });
  document.getElementById('param-scale')?.addEventListener('change', (e) => {
    send({ type: 'config', key: 'scale', value: e.target.value });
  });
  document.getElementById('btn-detect-key')?.addEventListener('click', () => {
    send({ type: 'detect_key' });
  });

  // Bypass
  document.getElementById('bypass')?.addEventListener('change', (e) => {
    send({ type: 'config', key: 'bypass', value: e.target.checked });
  });

  // Presets
  document.getElementById('btn-apply-preset')?.addEventListener('click', () => {
    send({ type: 'apply_preset', name: document.getElementById('preset-select').value });
  });

  // ---------------------------------------------------------------
  // Test tab
  // ---------------------------------------------------------------
  document.getElementById('btn-record')?.addEventListener('click', () => {
    send({ type: 'record_test' });
  });
  document.getElementById('btn-play-original')?.addEventListener('click', () => {
    send({ type: 'play_test', kind: 'original' });
  });
  document.getElementById('btn-play-processed')?.addEventListener('click', () => {
    send({ type: 'play_test', kind: 'processed' });
  });
  document.getElementById('btn-play-ab')?.addEventListener('click', () => {
    send({ type: 'play_ab' });
  });

  // ---------------------------------------------------------------
  // Route tab
  // ---------------------------------------------------------------
  document.getElementById('btn-find-virtual')?.addEventListener('click', () => {
    send({ type: 'find_virtual' });
  });
  document.getElementById('btn-test-tone')?.addEventListener('click', () => {
    send({ type: 'test_tone' });
  });
  document.getElementById('btn-refresh-devices2')?.addEventListener('click', () => {
    send({ type: 'get_devices' });
  });

  // ---------------------------------------------------------------
  // Canvas rendering
  // ---------------------------------------------------------------
  const gaugeCanvas = document.getElementById('gauge-canvas');
  const gaugeCtx = gaugeCanvas.getContext('2d');
  const meterCanvas = document.getElementById('meter-canvas');
  const meterCtx = meterCanvas.getContext('2d');
  const specCanvas = document.getElementById('spectrum-canvas');
  const specCtx = specCanvas.getContext('2d');

  function resizeSpecCanvas() {
    const rect = specCanvas.parentElement.getBoundingClientRect();
    specCanvas.width = rect.width - 36;
    specCanvas.height = 56;
  }
  window.addEventListener('resize', resizeSpecCanvas);
  setTimeout(resizeSpecCanvas, 100);

  function drawGauge() {
    const ctx = gaugeCtx;
    const w = gaugeCanvas.width, h = gaugeCanvas.height;
    ctx.clearRect(0, 0, w, h);

    const cx = w / 2, cy = h - 10;
    const r = Math.min(w, h * 2) / 2 - 22;

    // 外圈光晕
    ctx.beginPath();
    ctx.arc(cx, cy, r + 4, Math.PI, 0, false);
    ctx.strokeStyle = 'rgba(200, 180, 190, 0.15)';
    ctx.lineWidth = 12;
    ctx.lineCap = 'round';
    ctx.stroke();

    // 背景轨道（立体感）
    ctx.beginPath();
    ctx.arc(cx, cy, r, Math.PI, 0, false);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
    ctx.lineWidth = 10;
    ctx.lineCap = 'round';
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(cx, cy, r, Math.PI, 0, false);
    ctx.strokeStyle = 'rgba(200, 180, 190, 0.25)';
    ctx.lineWidth = 8;
    ctx.lineCap = 'round';
    ctx.stroke();

    // 状态区域（渐变色带）
    const zones = [
      { start: Math.PI, end: Math.PI + Math.PI * 0.25, color: '#e06070' },
      { start: Math.PI + Math.PI * 0.25, end: Math.PI + Math.PI * 0.4, color: '#d4a843' },
      { start: Math.PI + Math.PI * 0.4, end: Math.PI + Math.PI * 0.6, color: '#5a9e6a' },
      { start: Math.PI + Math.PI * 0.6, end: Math.PI + Math.PI * 0.75, color: '#d4a843' },
      { start: Math.PI + Math.PI * 0.75, end: Math.PI * 2, color: '#e06070' },
    ];
    zones.forEach(z => {
      // 光晕
      ctx.beginPath();
      ctx.arc(cx, cy, r, z.start, z.end, false);
      ctx.strokeStyle = z.color;
      ctx.lineWidth = 10;
      ctx.lineCap = 'round';
      ctx.globalAlpha = 0.15;
      ctx.stroke();

      // 主色带
      ctx.beginPath();
      ctx.arc(cx, cy, r, z.start, z.end, false);
      ctx.strokeStyle = z.color;
      ctx.lineWidth = 6;
      ctx.lineCap = 'round';
      ctx.globalAlpha = 0.5;
      ctx.stroke();
    });
    ctx.globalAlpha = 1;

    // 刻度
    ctx.strokeStyle = 'rgba(200, 180, 190, 0.4)';
    ctx.lineWidth = 1;
    for (let i = -50; i <= 50; i += 10) {
      const a = Math.PI + ((i + 100) / 200) * Math.PI;
      const r1 = r - 12;
      const r2 = i % 25 === 0 ? r - 4 : r - 7;
      ctx.beginPath();
      ctx.moveTo(cx + r1 * Math.cos(a), cy + r1 * Math.sin(a));
      ctx.lineTo(cx + r2 * Math.cos(a), cy + r2 * Math.sin(a));
      ctx.stroke();
    }

    // 平滑音分
    smoothCents.value = (smoothCents.value || 0) + ((smoothCents.target || 0) - (smoothCents.value || 0)) * 0.2;
    const cents = Math.max(-100, Math.min(100, smoothCents.value));
    const angle = Math.PI + ((cents + 100) / 200) * Math.PI;

    // 指针阴影
    const nx = cx + (r - 16) * Math.cos(angle);
    const ny = cy + (r - 16) * Math.sin(angle);
    ctx.beginPath();
    ctx.moveTo(cx + 2, cy + 2);
    ctx.lineTo(nx + 2, ny + 2);
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.1)';
    ctx.lineWidth = 4;
    ctx.lineCap = 'round';
    ctx.stroke();

    // 指针（渐变）
    const grad = ctx.createLinearGradient(cx, cy, nx, ny);
    grad.addColorStop(0, '#e8578f');
    grad.addColorStop(1, '#d04070');
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(nx, ny);
    ctx.strokeStyle = grad;
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.stroke();

    // 中心点（立体）
    ctx.beginPath();
    ctx.arc(cx, cy, 7, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(232, 87, 143, 0.3)';
    ctx.fill();

    ctx.beginPath();
    ctx.arc(cx, cy, 5, 0, Math.PI * 2);
    const centerGrad = ctx.createRadialGradient(cx - 1, cy - 1, 0, cx, cy, 5);
    centerGrad.addColorStop(0, '#f08ab0');
    centerGrad.addColorStop(1, '#e8578f');
    ctx.fillStyle = centerGrad;
    ctx.fill();

    ctx.beginPath();
    ctx.arc(cx - 1, cy - 1, 2, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
    ctx.fill();

    // 更新文字
    document.getElementById('gauge-note').textContent = currentNote;
    document.getElementById('gauge-freq').textContent = currentFreq > 0 ? `${currentFreq.toFixed(0)} Hz` : '-- Hz';
    const sign = cents >= 0 ? '+' : '';
    document.getElementById('gauge-cents').textContent = `${sign}${cents.toFixed(0)} ct`;
  }

  function drawMeter() {
    const ctx = meterCtx;
    const w = meterCanvas.width, h = meterCanvas.height;
    ctx.clearRect(0, 0, w, h);

    smoothLevel.value = (smoothLevel.value || 0) + ((smoothLevel.target || 0) - (smoothLevel.value || 0)) * 0.3;
    const level = Math.max(0, Math.min(1, smoothLevel.value));

    // 外框阴影
    ctx.fillStyle = 'rgba(200, 180, 190, 0.15)';
    ctx.beginPath();
    ctx.roundRect(3, 3, w - 4, h - 4, 8);
    ctx.fill();

    // 背景轨道（立体）
    ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
    ctx.beginPath();
    ctx.roundRect(2, 2, w - 4, h - 4, 7);
    ctx.fill();

    ctx.fillStyle = 'rgba(200, 180, 190, 0.2)';
    ctx.beginPath();
    ctx.roundRect(3, 3, w - 6, h - 6, 6);
    ctx.fill();

    // 填充
    const fillH = (h - 10) * level;
    if (fillH > 2) {
      const grad = ctx.createLinearGradient(0, h - 5, 0, h - 5 - fillH);
      grad.addColorStop(0, '#5a9e6a');
      grad.addColorStop(0.5, '#d4a843');
      grad.addColorStop(1, '#e8578f');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.roundRect(5, h - 5 - fillH, w - 10, fillH, 4);
      ctx.fill();

      // 高光
      const highlightGrad = ctx.createLinearGradient(0, h - 5, 0, h - 5 - fillH);
      highlightGrad.addColorStop(0, 'rgba(255, 255, 255, 0.3)');
      highlightGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = highlightGrad;
      ctx.beginPath();
      ctx.roundRect(5, h - 5 - fillH, (w - 10) / 2, fillH, 4);
      ctx.fill();
    }
  }

  function drawSpectrum() {
    const ctx = specCtx;
    const w = specCanvas.width, h = specCanvas.height;
    ctx.clearRect(0, 0, w, h);

    const n = spectrumData.length;
    const barW = Math.max(3, (w - 6) / n - 2);
    const gap = 2;

    for (let i = 0; i < n; i++) {
      const val = Math.max(0, Math.min(1, spectrumData[i]));
      const barH = Math.max(2, val * (h - 6));
      const x = 3 + i * (barW + gap);
      const y = h - 3 - barH;

      // 颜色
      let color;
      if (val < 0.35) color = '#5a9e6a';
      else if (val < 0.65) color = '#d4a843';
      else color = '#e8578f';

      // 阴影
      ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
      ctx.beginPath();
      ctx.roundRect(x + 1, y + 1, barW, barH, 3);
      ctx.fill();

      // 主体
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.5 + val * 0.5;
      ctx.beginPath();
      ctx.roundRect(x, y, barW, barH, 3);
      ctx.fill();

      // 高光
      ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
      ctx.globalAlpha = 0.3;
      ctx.beginPath();
      ctx.roundRect(x, y, barW / 2, barH, 3);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  // Animation loop
  function animate() {
    drawGauge();
    drawMeter();
    drawSpectrum();
    requestAnimationFrame(animate);
  }

  // ---------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------
  async function init() {
    // 设置激活 UI
    setupActivationUI();

    // 检查激活状态
    await checkActivation();

    // 连接 WebSocket
    if (window.electronAPI) {
      wsPort = await window.electronAPI.getWsPort();
    }
    connectWS();
    animate();
  }

  init();
})();
