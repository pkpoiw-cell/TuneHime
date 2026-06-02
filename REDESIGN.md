# AI Live Tuner 技术重构方案

## Python 的问题

| 问题 | 影响 |
|------|------|
| **无法做虚拟声卡** | 用户必须手动装 VB-CABLE，体验差 |
| **GIL 限制** | 线程并发受限，实时音频有风险 |
| **打包体积大** | PyInstaller 打出来 200MB+，启动慢 |
| **延迟** | 比 C++ 高一个量级（43ms vs 5ms） |
| **没有 VST3 能力** | 不能作为插件加载到 OBS/DAW |

## 最佳方案：C++ + JUCE

**JUCE** 是音频软件行业的标准框架，Auto-Tune、Spotify、Discord 都用它。

### 为什么选 JUCE

| 能力 | 说明 |
|------|------|
| **VST3 插件** | 直接在 OBS/直播伴侣/DAW 里加载，不需要虚拟声卡 |
| **独立应用** | 也能打包成独立 .exe |
| **超低延迟** | ASIO/WASAPI 原生支持，延迟 < 10ms |
| **跨平台** | Windows/Mac/Linux 一套代码 |
| **专业音频** | 内置 DSP 库、音高检测、效果器 |
| **体积小** | 打包后 < 20MB |

### 架构设计

```
方案 A: VST3 插件（推荐）
┌─────────────────────────────┐
│ OBS / 直播伴侣 / DAW       │
│  ┌─────────────────────┐   │
│  │ AI Live Tuner VST3  │   │
│  │  ┌───────────────┐  │   │
│  │  │ Pitch Correct  │  │   │
│  │  │ Noise Gate     │  │   │
│  │  │ Compressor     │  │   │
│  │  │ EQ / Brightness│  │   │
│  │  │ Reverb         │  │   │
│  │  └───────────────┘  │   │
│  └─────────────────────┘   │
└─────────────────────────────┘
用户操作: OBS 里加一个滤镜就行

方案 B: 独立应用 + 虚拟音频驱动
┌──────────┐    ┌──────────────┐    ┌──────────┐
│ 麦克风   │───>│ AI Live Tuner│───>│ 虚拟麦克风│───> OBS
└──────────┘    └──────────────┘    └──────────┘
用 JUCE 的 AudioIODevice 同时捕获输入和虚拟输出
```

### 代码结构

```
ai-live-tuner/
├── CMakeLists.txt
├── Source/
│   ├── PluginProcessor.cpp    # 音频处理核心
│   ├── PluginProcessor.h
│   ├── PluginEditor.cpp       # UI 界面
│   ├── PluginEditor.h
│   ├── DSP/
│   │   ├── PitchDetector.h    # 音高检测 (YIN/Rubber Band)
│   │   ├── PitchShifter.h     # 音高修正 (Rubber Band / SoundTouch)
│   │   ├── VoiceChain.h       # 噪声门+压缩+EQ+混响
│   │   └── KeyDetector.h      # 调号识别
│   └── UI/
│       ├── MainComponent.h    # 主界面
│       ├── PitchGauge.h       # 音高仪表
│       ├── SpectrumAnalyzer.h # 频谱
│       └── LookAndFeel.h      # 主题样式
├── Assets/
│   └── fonts, icons
└── Builds/
    ├── VisualStudio2022/      # Windows
    └── Xcode/                 # Mac
```

### 核心依赖

| 库 | 用途 | 许可证 |
|----|------|--------|
| JUCE | UI + 音频框架 | GPL / 商业 |
| Rubber Band | 高质量音高修正 | GPL / 商业 |
| FFTW | FFT 计算 | GPL |
| 或 kissfft | FFT 计算（更轻量） | BSD |

### UI 设计（JUCE 原生绘制）

JUCE 可以用代码绘制任意 UI，效果等同于 HTML/CSS：

```cpp
// 示例：绘制音高仪表盘
void PitchGauge::paint(Graphics& g) {
    auto bounds = getLocalBounds().toFloat();
    auto centre = bounds.getCentre();
    auto radius = bounds.getWidth() / 2 - 20;

    // 绘制弧形背景
    Path arc;
    arc.addCentredArc(centre.x, centre.y, radius, radius,
                       0, -MathConstants<float>::pi, 0, true);
    g.setColour(Colour(0xffd6e4));
    g.strokePath(arc, PathStrokeType(8));

    // 绘制指针
    float angle = -MathConstants<float>::pi + (cents + 100) / 200.0f * MathConstants<float>::pi;
    float nx = centre.x + radius * std::cos(angle);
    float ny = centre.y + radius * std::sin(angle);
    g.setColour(Colour(0xff6b9d));
    g.drawLine(centre.x, centre.y, nx, ny, 3);
}
```

### 工作量估算

| 模块 | 时间 | 难度 |
|------|------|------|
| JUCE 项目搭建 | 1 天 | 低 |
| 音高检测 (YIN) | 2 天 | 中 |
| 音高修正 (用 Rubber Band) | 1 天 | 低 |
| 效果器链 (Gate/Comp/EQ/Reverb) | 3 天 | 中 |
| UI 界面 | 3 天 | 中 |
| VST3 打包 | 1 天 | 低 |
| 测试 + 调参 | 3 天 | 中 |
| **合计** | **约 2 周** | |

## 备选方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **C++ + JUCE** | 专业标准，VST3，超低延迟 | 学习曲线陡 | ★★★★★ |
| **C# + NAudio** | 开发快，Windows 原生 | 无 VST3 支持 | ★★★ |
| **Rust + Tauri** | 现代，性能好 | 音频生态不成熟 | ★★ |
| **继续用 Python** | 已有代码 | 无法做 VST3 | ★ |

## 我的建议

**如果你要认真做这个产品，换成 C++ + JUCE 是唯一正确的选择。**

原因：
1. VST3 插件 = 用户在 OBS 里加一个滤镜就行，不需要装任何东西
2. 延迟从 43ms 降到 <5ms，唱歌无感
3. 打包体积从 200MB 降到 <20MB
4. 行业标准，Auto-Tune 用的就是这套

Python 写的版本可以作为原型验证，真正卖钱的产品必须用 C++。
