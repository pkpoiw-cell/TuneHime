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
  let appState = { config: {}, presets: ['自然', '流行', '电音'], user_presets: [], running: false };
  const busyButtons = new Set();

  function setStatus(text, online) {
    document.getElementById('engine-status').textContent = text;
    document.getElementById('status-pill')?.classList.toggle('offline', !online);
  }

  function setMessage(text, kind = 'info') {
    const el = document.getElementById('auto-status');
    if (!el) return;
    el.className = `auto-status ${kind}`;
    el.innerHTML = `<span class="float">♪</span> ${escapeHtml(text)}`;
  }

  function setButtonBusy(button, busy, text) {
    if (!button) return;
    if (busy) {
      button.dataset.label = button.textContent;
      button.classList.add('is-busy');
      button.disabled = true;
      if (text) button.textContent = text;
      busyButtons.add(button);
    } else {
      button.classList.remove('is-busy');
      button.disabled = false;
      if (button.dataset.label) button.textContent = button.dataset.label;
      busyButtons.delete(button);
    }
  }

  function clearBusyButtons() {
    busyButtons.forEach((button) => setButtonBusy(button, false));
  }

  function syncRunButtons(running) {
    appState.running = Boolean(running);
    const startBtn = document.getElementById('btn-start');
    const stopBtn = document.getElementById('btn-stop');
    if (startBtn) {
      startBtn.classList.toggle('is-active', appState.running);
      startBtn.disabled = appState.running || startBtn.classList.contains('is-busy');
      startBtn.innerHTML = appState.running ? '<span>♪</span>修音运行中' : '<span>♪</span>开始直播修音';
    }
    if (stopBtn) {
      stopBtn.disabled = !appState.running || stopBtn.classList.contains('is-busy');
    }
  }

  function connectWS() {
    if (ws && ws.readyState === WebSocket.OPEN) return;
    ws = new WebSocket(`ws://127.0.0.1:${wsPort}`);
    ws.onopen = () => {
      console.log('WS connected');
      setStatus('专业引擎 · 在线', true);
      setMessage('已连接后端，选择设备后即可开始');
      send({ type: 'get_devices' });
    };
    ws.onclose = () => {
      setStatus('后端已断开', false);
      setMessage('后端连接已断开，正在重连', 'error');
      clearBusyButtons();
      syncRunButtons(false);
      setTimeout(connectWS, 2000);
    };
    ws.onerror = () => {
      setStatus('连接异常', false);
      setMessage('连接异常，请确认后端已启动', 'error');
    };
    ws.onmessage = (e) => {
      try { handleMessage(JSON.parse(e.data)); } catch {}
    };
  }

  function send(msg) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
      return true;
    }
    setMessage('后端未连接，稍后再试', 'error');
    return false;
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
      case 'state':
        applyState(msg);
        break;
      case 'engine_status':
        clearBusyButtons();
        syncRunButtons(msg.running);
        setStatus(msg.running ? '直播修音中' : '专业引擎 · 在线', true);
        setMessage(msg.text || (msg.running ? '实时修音运行中' : '已停止'));
        break;
      case 'error':
        clearBusyButtons();
        syncRunButtons(false);
        setStatus('修音异常', false);
        setMessage(msg.text || '音频引擎异常', 'error');
        break;
      case 'test_status':
        clearBusyButtons();
        document.getElementById('test-status').textContent = msg.text;
        break;
      case 'route_status':
        clearBusyButtons();
        document.getElementById('route-status').textContent = msg.text;
        break;
      case 'auto_status':
        clearBusyButtons();
        setMessage(msg.text);
        break;
      case 'key_detected':
        document.getElementById('param-root').value = msg.root;
        document.getElementById('param-scale').value = msg.scale === 'major' ? '大调' : msg.scale === 'minor' ? '小调' : '半音阶';
        setStatus(`已识别: ${msg.root} ${msg.scale === 'major' ? '大调' : '小调'}`, true);
        break;
    }
  }

  function applyState(msg) {
    appState = {
      config: msg.config || appState.config || {},
      presets: msg.presets || appState.presets || [],
      user_presets: msg.user_presets || [],
      running: Boolean(msg.running),
    };

    const presetSelect = document.getElementById('preset-select');
    if (presetSelect) {
      const selected = appState.config.preset || presetSelect.value || '流行';
      presetSelect.innerHTML = appState.presets.map((name) => {
        const custom = appState.user_presets.includes(name) ? ' · 自定义' : '';
        return `<option value="${escapeHtml(name)}">${escapeHtml(name + custom)}</option>`;
      }).join('');
      presetSelect.value = selected;
    }

    setControlValue('param-root', appState.config.root);
    setControlValue('param-scale', appState.config.scale);
    setControlValue('input-device', appState.config.input_device);
    setControlValue('output-device', appState.config.output_device);
    setControlChecked('auto-mode', appState.config.auto_mode);
    setControlChecked('bypass', appState.config.bypass);
    setSliderValue('sl-amount', 'sv-amount', appState.config.amount, 100);
    setSliderValue('sl-speed', 'sv-speed', appState.config.speed, 100);
    setSliderValue('sl-mix', 'sv-mix', appState.config.mix, 100);
    setSliderValue('sl-gate', 'sv-gate', appState.config.gate, 100);
    setSliderValue('sl-comp', 'sv-comp', appState.config.compression, 100);
    setSliderValue('sl-bright', 'sv-bright', appState.config.brightness, 100);
    setSliderValue('sl-deess', 'sv-deess', appState.config.deesser, 100);
    setSliderValue('sl-reverb', 'sv-reverb', appState.config.reverb, 100);
    setSliderValue('sl-gain', 'sv-gain', appState.config.gain, 100);
    syncRunButtons(appState.running);
  }

  function setControlValue(id, value) {
    const el = document.getElementById(id);
    if (el && value !== undefined) el.value = value;
  }

  function setControlChecked(id, value) {
    const el = document.getElementById(id);
    if (el && value !== undefined) el.checked = Boolean(value);
  }

  function setSliderValue(sliderId, valueId, value, multiplier) {
    const slider = document.getElementById(sliderId);
    const label = document.getElementById(valueId);
    if (!slider || value === undefined) return;
    const number = Number(value);
    slider.value = Math.round(number * multiplier);
    if (label) label.textContent = number.toFixed(2);
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
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
    if (msg.spectrum) {
      spectrumData = new Float32Array(msg.spectrum);
      markDirty();
    }
    if (msg.auto_status) {
      setMessage(msg.auto_status);
    }
    // 数据更新时标记脏
    if (msg.cents !== undefined || msg.level !== undefined) {
      markDirty();
    }
  }

  // ---------------------------------------------------------------
  // Device list
  // ---------------------------------------------------------------
  function populateDevices(inputs, outputs) {
    const inputSel = document.getElementById('input-device');
    const outputSel = document.getElementById('output-device');
    inputSel.innerHTML = inputs.map(n => `<option value="${escapeHtml(n)}">${escapeHtml(n)}</option>`).join('');
    outputSel.innerHTML = outputs.map(n => `<option value="${escapeHtml(n)}">${escapeHtml(n)}</option>`).join('');
    if (appState.config.input_device) inputSel.value = appState.config.input_device;
    if (appState.config.output_device) outputSel.value = appState.config.output_device;
  }

  // ---------------------------------------------------------------
  // Tabs
  // ---------------------------------------------------------------
  const tabTitles = {
    'live': { title: '实时修音', subtitle: '直播人声调音台' },
    'settings': { title: '修音设置', subtitle: '调音参数与人声处理' },
    'test': { title: '效果测试', subtitle: '录制与对比' },
    'route': { title: '输出设置', subtitle: '虚拟声卡配置' },
    'preferences': { title: '软件设置', subtitle: '音姬 TuneHime 偏好设置' },
  };

  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(`panel-${tab.dataset.tab}`).classList.add('active');

      // 更新页面标题
      const tabId = tab.dataset.tab;
      const titleInfo = tabTitles[tabId];
      if (titleInfo) {
        document.querySelector('.page-title h1').textContent = titleInfo.title;
        document.querySelector('.header-subtitle').textContent = titleInfo.subtitle;
      }
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
    const button = document.getElementById('btn-start');
    setStatus('直播修音中', true);
    setMessage('正在启动音频引擎...');
    setButtonBusy(button, true, '启动中...');
    if (!send({ type: 'start', auto_mode: document.getElementById('auto-mode')?.checked !== false })) {
      setButtonBusy(button, false);
    }
  });
  document.getElementById('btn-stop').addEventListener('click', () => {
    const button = document.getElementById('btn-stop');
    setButtonBusy(button, true, '停止中...');
    if (!send({ type: 'stop' })) setButtonBusy(button, false);
  });
  document.getElementById('btn-refresh-devices').addEventListener('click', () => {
    const button = document.getElementById('btn-refresh-devices');
    setButtonBusy(button, true, '刷新中');
    if (!send({ type: 'get_devices' })) setButtonBusy(button, false);
    else setTimeout(() => setButtonBusy(button, false), 700);
  });
  document.getElementById('input-device')?.addEventListener('change', (e) => {
    send({ type: 'config', key: 'input_device', value: e.target.value });
  });
  document.getElementById('output-device')?.addEventListener('change', (e) => {
    send({ type: 'config', key: 'output_device', value: e.target.value });
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
    const button = document.getElementById('btn-detect-key');
    setButtonBusy(button, true, '识别中');
    setMessage('请对着麦克风唱 5 秒稳定旋律');
    if (!send({ type: 'detect_key' })) setButtonBusy(button, false);
  });

  // Bypass
  document.getElementById('bypass')?.addEventListener('change', (e) => {
    send({ type: 'config', key: 'bypass', value: e.target.checked });
  });

  // Presets
  document.getElementById('btn-apply-preset')?.addEventListener('click', () => {
    const button = document.getElementById('btn-apply-preset');
    setButtonBusy(button, true, '应用中');
    if (!send({ type: 'apply_preset', name: document.getElementById('preset-select').value })) {
      setButtonBusy(button, false);
    }
  });
  document.querySelectorAll('.preset-tile').forEach((button) => {
    button.addEventListener('click', () => {
      const name = button.dataset.preset;
      document.getElementById('preset-select').value = name;
      setButtonBusy(button, true, '应用中');
      if (!send({ type: 'apply_preset', name })) setButtonBusy(button, false);
    });
  });
  document.getElementById('btn-save-preset')?.addEventListener('click', () => {
    const current = document.getElementById('preset-select').value || '流行';
    const name = window.prompt('保存为自定义预设', appState.user_presets.includes(current) ? current : `${current} 自定义`);
    if (name) {
      const button = document.getElementById('btn-save-preset');
      setButtonBusy(button, true, '保存中');
      if (!send({ type: 'save_preset', name })) setButtonBusy(button, false);
    }
  });
  document.getElementById('btn-del-preset')?.addEventListener('click', () => {
    const name = document.getElementById('preset-select').value;
    if (!appState.user_presets.includes(name)) {
      document.getElementById('auto-status').innerHTML = '<span class="float">♪</span> 内置预设不能删除';
      return;
    }
    if (window.confirm(`删除自定义预设“${name}”？`)) {
      send({ type: 'delete_preset', name });
    }
  });

  // ---------------------------------------------------------------
  // Test tab
  // ---------------------------------------------------------------
  document.getElementById('btn-record')?.addEventListener('click', () => {
    const button = document.getElementById('btn-record');
    document.getElementById('test-status').textContent = '正在录制 5 秒，请正常唱歌...';
    setButtonBusy(button, true, '录制中...');
    if (!send({ type: 'record_test' })) setButtonBusy(button, false);
  });
  document.getElementById('btn-play-original')?.addEventListener('click', () => {
    const button = document.getElementById('btn-play-original');
    setButtonBusy(button, true, '播放中');
    if (!send({ type: 'play_test', kind: 'original' })) setButtonBusy(button, false);
  });
  document.getElementById('btn-play-processed')?.addEventListener('click', () => {
    const button = document.getElementById('btn-play-processed');
    setButtonBusy(button, true, '播放中');
    if (!send({ type: 'play_test', kind: 'processed' })) setButtonBusy(button, false);
  });
  document.getElementById('btn-play-ab')?.addEventListener('click', () => {
    const button = document.getElementById('btn-play-ab');
    setButtonBusy(button, true, '播放中');
    if (!send({ type: 'play_ab' })) setButtonBusy(button, false);
  });

  // ---------------------------------------------------------------
  // Route tab
  // ---------------------------------------------------------------
  document.getElementById('btn-find-virtual')?.addEventListener('click', () => {
    const button = document.getElementById('btn-find-virtual');
    setButtonBusy(button, true, '查找中');
    if (!send({ type: 'find_virtual' })) setButtonBusy(button, false);
  });
  document.getElementById('btn-test-tone')?.addEventListener('click', () => {
    const button = document.getElementById('btn-test-tone');
    setButtonBusy(button, true, '发送中');
    if (!send({ type: 'test_tone' })) setButtonBusy(button, false);
  });
  document.getElementById('btn-refresh-devices2')?.addEventListener('click', () => {
    const button = document.getElementById('btn-refresh-devices2');
    setButtonBusy(button, true, '刷新中');
    if (!send({ type: 'get_devices' })) setButtonBusy(button, false);
    else setTimeout(() => setButtonBusy(button, false), 700);
  });

  // ---------------------------------------------------------------
  // Preferences tab
  // ---------------------------------------------------------------
  function updatePreferencesUI() {
    if (!activationStatus) return;

    const licenseStatus = document.getElementById('pref-license-status');
    const licenseRemaining = document.getElementById('pref-license-remaining');

    if (activationStatus.status === 'activated') {
      licenseStatus.textContent = '已激活';
      licenseStatus.style.color = '#5a9e6a';
      licenseRemaining.textContent = '永久';
    } else if (activationStatus.status === 'expired') {
      licenseStatus.textContent = '已过期';
      licenseStatus.style.color = '#e06070';
      licenseRemaining.textContent = '需要激活';
    } else {
      licenseStatus.textContent = '试用中';
      licenseStatus.style.color = '#d4a843';
      licenseRemaining.textContent = `${activationStatus.remainingDays} 天`;
    }
  }

  // 加载偏好设置
  async function loadPreferences() {
    if (!window.electronAPI?.getPreferences) return;

    try {
      const prefs = await window.electronAPI.getPreferences();

      // 通用设置
      document.getElementById('pref-autostart').checked = prefs.autoLaunch;
      document.getElementById('pref-minimize-to-tray').checked = prefs.minimizeToTray;
      document.getElementById('pref-start-minimized').checked = prefs.startMinimized;
      document.getElementById('pref-check-update').checked = prefs.checkUpdate;

      // 音频设置
      document.getElementById('pref-sample-rate').value = prefs.sampleRate;
      document.getElementById('pref-buffer-size').value = prefs.bufferSize;
      document.getElementById('pref-low-latency').checked = prefs.lowLatency;

      // 界面设置
      document.getElementById('pref-theme').value = prefs.theme;
      document.getElementById('pref-language').value = prefs.language;
      document.getElementById('pref-show-fps').checked = prefs.showFps;

      // 高级设置
      document.getElementById('pref-log-level').value = prefs.logLevel;
    } catch (err) {
      console.error('Failed to load preferences:', err);
    }
  }

  // 保存偏好设置的通用函数
  async function savePref(key, value) {
    if (window.electronAPI?.savePreference) {
      await window.electronAPI.savePreference(key, value);
    }
  }

  // 通用设置事件监听
  document.getElementById('pref-autostart')?.addEventListener('change', async (e) => {
    if (window.electronAPI?.setAutoLaunch) {
      await window.electronAPI.setAutoLaunch(e.target.checked);
    }
  });

  document.getElementById('pref-minimize-to-tray')?.addEventListener('change', (e) => {
    savePref('minimizeToTray', e.target.checked);
  });

  document.getElementById('pref-start-minimized')?.addEventListener('change', (e) => {
    savePref('startMinimized', e.target.checked);
  });

  document.getElementById('pref-check-update')?.addEventListener('change', (e) => {
    savePref('checkUpdate', e.target.checked);
  });

  // 音频设置事件监听
  document.getElementById('pref-sample-rate')?.addEventListener('change', (e) => {
    savePref('sampleRate', parseInt(e.target.value));
  });

  document.getElementById('pref-buffer-size')?.addEventListener('change', (e) => {
    savePref('bufferSize', parseInt(e.target.value));
  });

  document.getElementById('pref-low-latency')?.addEventListener('change', (e) => {
    savePref('lowLatency', e.target.checked);
  });

  // 界面设置事件监听
  document.getElementById('pref-theme')?.addEventListener('change', (e) => {
    savePref('theme', e.target.value);
    applyTheme(e.target.value);
  });

  document.getElementById('pref-language')?.addEventListener('change', (e) => {
    savePref('language', e.target.value);
  });

  document.getElementById('pref-show-fps')?.addEventListener('change', (e) => {
    savePref('showFps', e.target.checked);
  });

  // 高级设置事件监听
  document.getElementById('pref-log-level')?.addEventListener('change', (e) => {
    savePref('logLevel', e.target.value);
  });

  // 主题应用函数
  function applyTheme(theme) {
    if (theme === 'auto') {
      // 跟随系统
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    } else {
      document.documentElement.setAttribute('data-theme', theme);
    }
  }

  // 激活码按钮
  document.getElementById('btn-activate')?.addEventListener('click', () => {
    document.getElementById('activation-overlay').style.display = 'flex';
  });

  // 购买按钮
  document.getElementById('btn-purchase')?.addEventListener('click', () => {
    if (window.electronAPI?.openExternal) {
      window.electronAPI.openExternal('https://tunehime.com/purchase');
    }
  });

  // 打开日志目录
  document.getElementById('btn-open-log')?.addEventListener('click', () => {
    if (window.electronAPI?.openLogDir) {
      window.electronAPI.openLogDir();
    }
  });

  // 恢复默认设置
  document.getElementById('btn-reset-settings')?.addEventListener('click', async () => {
    if (window.confirm('确定要恢复所有设置为默认值吗？')) {
      if (window.electronAPI?.resetAllSettings) {
        await window.electronAPI.resetAllSettings();
        // 重新加载设置
        await loadPreferences();
        alert('设置已恢复为默认值');
      }
    }
  });

  // 检查更新
  document.getElementById('btn-check-update')?.addEventListener('click', () => {
    if (window.electronAPI?.checkUpdate) {
      window.electronAPI.checkUpdate();
    }
  });

  // 官方网站
  document.getElementById('btn-website')?.addEventListener('click', () => {
    if (window.electronAPI?.openExternal) {
      window.electronAPI.openExternal('https://tunehime.com');
    }
  });

  // GitHub
  document.getElementById('btn-github')?.addEventListener('click', () => {
    if (window.electronAPI?.openExternal) {
      window.electronAPI.openExternal('https://github.com/pkpoiw-cell/TuneHime');
    }
  });

  // ---------------------------------------------------------------
  // Canvas rendering (Optimized)
  // ---------------------------------------------------------------
  const gaugeCanvas = document.getElementById('gauge-canvas');
  const gaugeCtx = gaugeCanvas.getContext('2d');
  const meterCanvas = document.getElementById('meter-canvas');
  const meterCtx = meterCanvas.getContext('2d');
  const specCanvas = document.getElementById('spectrum-canvas');
  const specCtx = specCanvas.getContext('2d');

  // 缓存 DOM 元素引用
  const gaugeNoteEl = document.getElementById('gauge-note');
  const gaugeFreqEl = document.getElementById('gauge-freq');
  const gaugeCentsEl = document.getElementById('gauge-cents');

  // 脏标记 - 只在数据变化时重绘
  let isDirty = true;
  let lastCents = 0;
  let lastLevel = 0;
  let lastNote = '--';
  let lastFreq = 0;

  // 限流动画 - 空闲时降低帧率
  let animationFrame = 0;
  const TARGET_FPS = 30;
  const FRAME_INTERVAL = 1000 / TARGET_FPS;
  let lastFrameTime = 0;

  // 预渲染的静态背景缓存
  let gaugeBgCanvas = null;
  let meterBgCanvas = null;

  function resizeSpecCanvas() {
    const rect = specCanvas.parentElement.getBoundingClientRect();
    specCanvas.width = Math.max(180, rect.width - 56);
    specCanvas.height = 56;
    isDirty = true;
  }
  window.addEventListener('resize', resizeSpecCanvas);
  setTimeout(resizeSpecCanvas, 100);

  // 预渲染仪表盘背景（只绘制一次）
  function createGaugeBackground() {
    const w = gaugeCanvas.width, h = gaugeCanvas.height;
    const offscreen = document.createElement('canvas');
    offscreen.width = w;
    offscreen.height = h;
    const ctx = offscreen.getContext('2d');

    const cx = w / 2, cy = h - 10;
    const r = Math.min(w, h * 2) / 2 - 22;

    // 外圈光晕
    ctx.beginPath();
    ctx.arc(cx, cy, r + 4, Math.PI, 0, false);
    ctx.strokeStyle = 'rgba(200, 180, 190, 0.15)';
    ctx.lineWidth = 12;
    ctx.lineCap = 'round';
    ctx.stroke();

    // 背景轨道
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

    // 状态区域
    const zones = [
      { start: Math.PI, end: Math.PI + Math.PI * 0.25, color: '#e06070' },
      { start: Math.PI + Math.PI * 0.25, end: Math.PI + Math.PI * 0.4, color: '#d4a843' },
      { start: Math.PI + Math.PI * 0.4, end: Math.PI + Math.PI * 0.6, color: '#5a9e6a' },
      { start: Math.PI + Math.PI * 0.6, end: Math.PI + Math.PI * 0.75, color: '#d4a843' },
      { start: Math.PI + Math.PI * 0.75, end: Math.PI * 2, color: '#e06070' },
    ];
    zones.forEach(z => {
      ctx.beginPath();
      ctx.arc(cx, cy, r, z.start, z.end, false);
      ctx.strokeStyle = z.color;
      ctx.lineWidth = 10;
      ctx.lineCap = 'round';
      ctx.globalAlpha = 0.15;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(cx, cy, r, z.start, z.end, false);
      ctx.lineWidth = 6;
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

    // 中心点
    ctx.beginPath();
    ctx.arc(cx, cy, 7, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(232, 87, 143, 0.3)';
    ctx.fill();

    return { canvas: offscreen, cx, cy, r };
  }

  // 预渲染电平表背景
  function createMeterBackground() {
    const w = meterCanvas.width, h = meterCanvas.height;
    const offscreen = document.createElement('canvas');
    offscreen.width = w;
    offscreen.height = h;
    const ctx = offscreen.getContext('2d');

    ctx.fillStyle = 'rgba(200, 180, 190, 0.15)';
    ctx.beginPath();
    ctx.roundRect(3, 3, w - 4, h - 4, 8);
    ctx.fill();

    ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
    ctx.beginPath();
    ctx.roundRect(2, 2, w - 4, h - 4, 7);
    ctx.fill();

    ctx.fillStyle = 'rgba(200, 180, 190, 0.2)';
    ctx.beginPath();
    ctx.roundRect(3, 3, w - 6, h - 6, 6);
    ctx.fill();

    return offscreen;
  }

  // 初始化背景缓存
  function initBackgrounds() {
    gaugeBgCanvas = createGaugeBackground();
    meterBgCanvas = createMeterBackground();
  }
  setTimeout(initBackgrounds, 200);

  function drawGauge() {
    const ctx = gaugeCtx;
    const w = gaugeCanvas.width, h = gaugeCanvas.height;
    ctx.clearRect(0, 0, w, h);

    // 绘制预渲染的背景
    if (gaugeBgCanvas) {
      ctx.drawImage(gaugeBgCanvas.canvas, 0, 0);
    }

    const cx = gaugeBgCanvas?.cx || w / 2;
    const cy = gaugeBgCanvas?.cy || h - 10;
    const r = gaugeBgCanvas?.r || Math.min(w, h * 2) / 2 - 22;

    // 平滑音分
    smoothCents.value = (smoothCents.value || 0) + ((smoothCents.target || 0) - (smoothCents.value || 0)) * 0.15;
    const cents = Math.max(-100, Math.min(100, smoothCents.value));
    const angle = Math.PI + ((cents + 100) / 200) * Math.PI;

    // 指针
    const nx = cx + (r - 16) * Math.cos(angle);
    const ny = cy + (r - 16) * Math.sin(angle);

    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(nx, ny);
    ctx.strokeStyle = '#e8578f';
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.stroke();

    // 中心高光
    ctx.beginPath();
    ctx.arc(cx, cy, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#e8578f';
    ctx.fill();

    ctx.beginPath();
    ctx.arc(cx - 1, cy - 1, 2, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
    ctx.fill();

    // 更新文字（仅在变化时）
    const newNote = currentNote;
    const newFreq = currentFreq > 0 ? `${currentFreq.toFixed(0)} Hz` : '-- Hz';
    const sign = cents >= 0 ? '+' : '';
    const newCents = `${sign}${cents.toFixed(0)} ct`;

    if (newNote !== lastNote) {
      gaugeNoteEl.textContent = newNote;
      lastNote = newNote;
    }
    if (newFreq !== lastFreq) {
      gaugeFreqEl.textContent = newFreq;
      lastFreq = newFreq;
    }
    if (newCents !== lastCents) {
      gaugeCentsEl.textContent = newCents;
      lastCents = newCents;
    }
  }

  function drawMeter() {
    const ctx = meterCtx;
    const w = meterCanvas.width, h = meterCanvas.height;
    ctx.clearRect(0, 0, w, h);

    // 绘制预渲染的背景
    if (meterBgCanvas) {
      ctx.drawImage(meterBgCanvas, 0, 0);
    }

    smoothLevel.value = (smoothLevel.value || 0) + ((smoothLevel.target || 0) - (smoothLevel.value || 0)) * 0.2;
    const level = Math.max(0, Math.min(1, smoothLevel.value));

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

      let color;
      if (val < 0.35) color = '#5a9e6a';
      else if (val < 0.65) color = '#d4a843';
      else color = '#e8578f';

      ctx.fillStyle = color;
      ctx.globalAlpha = 0.5 + val * 0.5;
      ctx.beginPath();
      ctx.roundRect(x, y, barW, barH, 3);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  // 优化的动画循环 - 限流 + 脏标记
  function animate(timestamp) {
    animationFrame = requestAnimationFrame(animate);

    // 限流到目标帧率
    if (timestamp - lastFrameTime < FRAME_INTERVAL) return;
    lastFrameTime = timestamp;

    // 检查是否有数据更新
    const centsChanged = Math.abs((smoothCents.target || 0) - (smoothCents.value || 0)) > 0.5;
    const levelChanged = Math.abs((smoothLevel.target || 0) - (smoothLevel.value || 0)) > 0.01;

    if (isDirty || centsChanged || levelChanged) {
      drawGauge();
      drawMeter();
      drawSpectrum();
      isDirty = false;
    }
  }

  // 标记需要重绘
  function markDirty() {
    isDirty = true;
  }

  // ---------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------
  async function init() {
    // 设置激活 UI
    setupActivationUI();

    // 检查激活状态
    await checkActivation();

    // 更新设置面板的授权信息
    updatePreferencesUI();

    // 加载偏好设置
    await loadPreferences();

    // 连接 WebSocket
    if (window.electronAPI) {
      wsPort = await window.electronAPI.getWsPort();
    }
    connectWS();
    // 启动动画循环
    requestAnimationFrame(animate);
  }

  init();
})();
