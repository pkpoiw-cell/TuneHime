/**
 * AI Live Tuner 激活码验证模块（示例文件）
 *
 * 使用说明：
 * 1. 复制此文件为 activation.js
 * 2. 将 SECRET_KEY 替换为你自己的密钥
 * 3. 确保 activation.js 与激活码生成工具使用相同的密钥
 *
 * ⚠️ 不要将真实的 activation.js 提交到公开仓库！
 */

const crypto = require('crypto');

// ═══════════════════════════════════════════════════════════════
// 密钥配置（必须与生成工具保持一致）
// ⚠️ 请替换为你自己的密钥！
// ═══════════════════════════════════════════════════════════════
const SECRET_KEY = 'YOUR-SECRET-KEY-HERE';  // ← 替换为你的密钥
const HMAC_ALGORITHM = 'sha256';

// 许可证类型映射
const LICENSE_CODE_MAP = {
  'T': 'trial',
  'M': 'monthly',
  'Y': 'yearly',
  'L': 'lifetime',
};

/**
 * 验证激活码
 *
 * @param {string} code - 激活码
 * @returns {object} { valid: boolean, type: string, error: string }
 */
function validateActivationCode(code) {
  // 1. 格式检查
  if (!code || typeof code !== 'string') {
    return { valid: false, type: null, error: '激活码不能为空' };
  }

  // 移除空格，转大写
  const normalized = code.replace(/\s/g, '').toUpperCase();

  // 检查格式：PPPP-XXXX-XXXX-XXXX
  const formatRegex = /^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/;
  if (!formatRegex.test(normalized)) {
    return { valid: false, type: null, error: '激活码格式错误' };
  }

  // 2. 提取各部分
  const parts = normalized.split('-').join('');
  const prefix = parts.substring(0, 4);
  const codeBody = parts.substring(4);

  // 3. 提取类型码和校验位
  const typeCode = prefix[0];
  const storedChecksum = prefix.substring(1, 3);
  const licenseType = LICENSE_CODE_MAP[typeCode];

  if (!licenseType) {
    return { valid: false, type: null, error: '无效的激活码类型' };
  }

  // 4. 重新计算校验位
  const computedChecksum = crypto.createHash('md5')
    .update(codeBody)
    .digest('hex')
    .substring(0, 2)
    .toUpperCase();

  // 5. 对比校验位
  if (storedChecksum !== computedChecksum) {
    return { valid: false, type: null, error: '激活码校验失败' };
  }

  // 6. 验证通过
  return {
    valid: true,
    type: licenseType,
    error: null,
  };
}

/**
 * 获取许可证类型信息
 */
function getLicenseInfo(type) {
  const info = {
    trial:    { days: 7,    label: '7天试用' },
    monthly:  { days: 30,   label: '月卡' },
    yearly:   { days: 365,  label: '年卡' },
    lifetime: { days: 9999, label: '终身' },
  };
  return info[type] || null;
}

module.exports = { validateActivationCode, getLicenseInfo };
