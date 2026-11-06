export interface TextChange { kind: 'equal' | 'removed' | 'added'; text: string }

// Word/whitespace LCS retains exact copy. Large edits use a bounded middle fallback.
export function diffText(before: string, after: string): TextChange[] {
  if (before === after) return before ? [{ kind: 'equal', text: before }] : [];
  const a = before.match(/\s+|\S+/g) ?? [];
  const b = after.match(/\s+|\S+/g) ?? [];
  const result: TextChange[] = [];
  function append(kind: TextChange['kind'], text: string) {
    if (!text) return;
    const previous = result.at(-1);
    if (previous?.kind === kind) previous.text += text;
    else result.push({ kind, text });
  }
  if ((a.length + 1) * (b.length + 1) > 250_000) {
    let start = 0; let endA = a.length; let endB = b.length;
    while (start < endA && start < endB && a[start] === b[start]) start++;
    while (endA > start && endB > start && a[endA - 1] === b[endB - 1]) { endA--; endB--; }
    append('equal', a.slice(0, start).join('')); append('removed', a.slice(start, endA).join('')); append('added', b.slice(start, endB).join('')); append('equal', a.slice(endA).join(''));
    return result;
  }
  const width = b.length + 1;
  const matrix = new Uint32Array((a.length + 1) * width);
  for (let i = a.length - 1; i >= 0; i--) for (let j = b.length - 1; j >= 0; j--) matrix[i * width + j] = a[i] === b[j] ? matrix[(i + 1) * width + j + 1] + 1 : Math.max(matrix[(i + 1) * width + j], matrix[i * width + j + 1]);
  let i = 0; let j = 0;
  while (i < a.length || j < b.length) {
    if (i < a.length && j < b.length && a[i] === b[j]) { append('equal', a[i]); i++; j++; }
    else if (i < a.length && (j === b.length || matrix[(i + 1) * width + j] >= matrix[i * width + j + 1])) { append('removed', a[i]); i++; }
    else { append('added', b[j]); j++; }
  }
  return result;
}
