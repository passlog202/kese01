/** 数字/文本格式化工具 */
export function fmtPrice(n) {
  return `¥${Number(n).toFixed(2)}`
}

export function fmtNumber(n) {
  return (Number(n) || 0).toLocaleString('zh-CN')
}

export function fmtTime(iso) {
  return iso ? iso.replace('T', ' ').slice(0, 19) : ''
}

/** 历史记录 result_json 解析 */
export function parseResult(raw) {
  try {
    return typeof raw === 'string' ? JSON.parse(raw) : raw
  } catch {
    return { items: [] }
  }
}

/** 历史记录 query_json 解析 */
export function parseQuery(raw) {
  try {
    return typeof raw === 'string' ? JSON.parse(raw) : raw
  } catch {
    return {}
  }
}
